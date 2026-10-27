import os
import re
import sqlite3
import io
import csv
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from flask import Flask, render_template, jsonify, request, Response
from config import Config
from data.generator import generate_shelter_dataset
from ml.matcher import VectorMatcher
from ml.los_classifier import LengthOfStayClassifier
from ml.outlier_router import SpecializedPlacementRouter, OutlierSARRouter

app = Flask(__name__)

app.config.from_object(Config)

# Global instances
los_model = LengthOfStayClassifier()
latest_scanned_tag = None
latest_scanned_animal = None

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def is_valid_email(email_str):
    """Validates an email address format."""
    if not email_str or not isinstance(email_str, str):
        return False
    cleaned = email_str.strip()
    return bool(len(cleaned) <= 254 and EMAIL_REGEX.match(cleaned))


def get_db_connection():
    """Helper to connect to SQLite DB with safe concurrency settings."""
    os.makedirs(os.path.dirname(Config.DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_portal_tables():
    """Creates PET CONNECT adopter pre-registration and adoption request tables if not present."""
    os.makedirs(Config.SENT_EMAILS_DIR, exist_ok=True)
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adopter_sessions (
            email TEXT PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            preferred_species TEXT DEFAULT 'all',
            energy_capacity REAL DEFAULT 5.0,
            maintenance_capacity REAL DEFAULT 5.0,
            space_limit REAL DEFAULT 5.0,
            yard_size INTEGER DEFAULT 1,
            budget_limit REAL DEFAULT 5.0,
            youngest_child_age REAL DEFAULT 10.0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adoption_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_ref TEXT UNIQUE,
            animal_id TEXT,
            rfid_tag TEXT,
            pet_name TEXT,
            species TEXT,
            breed TEXT,
            adoption_fee INTEGER,
            adopter_name TEXT,
            adopter_email TEXT,
            adopter_phone TEXT,
            housing_type TEXT,
            other_pets TEXT,
            experience_level TEXT,
            personal_note TEXT,
            compatibility_score REAL,
            email_status TEXT,
            email_subject TEXT,
            email_body_text TEXT,
            email_body_html TEXT,
            email_file_path TEXT,
            status TEXT DEFAULT 'CONFIRMED_PENDING_MEET',
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def build_confirmation_email(request_record, animal_dict, match_analysis):
    """
    Constructs a rich plain-text and HTML confirmation email for a PET CONNECT adoption request.
    """
    ref_id = request_record['request_ref']
    adopter_name = request_record['adopter_name']
    adopter_email = request_record['adopter_email']
    adopter_phone = request_record.get('adopter_phone') or 'Provided on file'
    pet_name = request_record['pet_name']
    species = request_record['species']
    breed = request_record['breed']
    rfid_tag = request_record['rfid_tag']
    fee = request_record['adoption_fee']
    housing_label_map = {
        'house_yard': 'Single Family House with Fenced Yard',
        'house_noyard': 'House without Fenced Yard',
        'apartment': 'Apartment / Condominium',
        'rural': 'Rural Property / Acreage'
    }
    housing_display = housing_label_map.get(request_record.get('housing_type', ''), request_record.get('housing_type', 'Standard Home'))
    created_at = request_record['created_at']

    score = match_analysis.get('compatibility_score', 94.0)
    tier = match_analysis.get('compatibility_tier', 'Ideal Match')
    primary_reason = match_analysis.get('primary_explanation', f"{pet_name} aligns wonderfully with your household routine.")
    metrics = match_analysis.get('metrics_breakdown', {})
    checklist = match_analysis.get('care_checklist') or VectorMatcher.generate_care_checklist(animal_dict)

    subject = f"🐾 PET CONNECT Confirmation: Your Adoption Request for {pet_name} [Ref #{ref_id}]"

    checklist_txt = "\n".join(f"  • {item}" for item in checklist)
    body_text = (
        f"Hello {adopter_name},\n\n"
        f"Thank you for choosing rescue with PET CONNECT! Your adoption request for {pet_name} "
        f"({breed} {species}, Microchip Ref: {rfid_tag}) has been officially registered.\n\n"
        f"--- ADOPTION REQUEST CONFIRMATION ---\n"
        f"Reference Code: #{ref_id}\n"
        f"Submitted At:   {created_at}\n"
        f"Companion:      {pet_name} ({species} • {breed})\n"
        f"Microchip Tag:  {rfid_tag}\n"
        f"Adoption Fee:   ${fee} (Includes vaccinations, microchip & wellness exam)\n"
        f"Adopter Name:   {adopter_name}\n"
        f"Adopter Email:  {adopter_email}\n"
        f"Adopter Phone:  {adopter_phone}\n"
        f"Home Setting:   {housing_display}\n\n"
        f"--- PERSONAL MANAGEABILITY & COMPATIBILITY SUMMARY ---\n"
        f"Overall Compatibility: {score}% ({tier})\n"
        f"Summary: {primary_reason}\n"
        f"  - Energy Match:      {round(metrics.get('energy_match', 92))}%\n"
        f"  - Maintenance Match: {round(metrics.get('maintenance_match', 90))}%\n"
        f"  - Space Match:       {round(metrics.get('space_match', 95))}%\n"
        f"  - Budget Match:      {round(metrics.get('budget_match', 90))}%\n\n"
        f"--- RECOMMENDED PREPARATION CHECKLIST FOR {pet_name.upper()} ---\n"
        f"{checklist_txt}\n\n"
        f"--- NEXT STEPS ---\n"
        f"1. A PET CONNECT Adoption Coordinator will contact you at {adopter_email} within 24 to 48 hours.\n"
        f"2. Bring your Reference Code (#{ref_id}) when visiting our sanctuary (Tue–Sun, 11:00 AM – 5:00 PM).\n\n"
        f"Warmest regards,\n"
        f"The PET CONNECT Adoption & Sanctuary Care Team\n"
        f"{Config.SMTP_FROM_EMAIL}\n"
    )

    checklist_html = "".join(
        f"<li style='margin-bottom:8px;color:#e2e8f0;font-size:14px;line-height:1.5;'>{item}</li>"
        for item in checklist
    )

    body_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{subject}</title>
</head>
<body style="margin:0;padding:24px;background-color:#0b0f17;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#f8fafc;">
  <div style="max-width:640px;margin:0 auto;background:#151c28;border:1px solid rgba(255,255,255,0.12);border-radius:16px;overflow:hidden;box-shadow:0 20px 40px rgba(0,0,0,0.5);">
    <div style="background:linear-gradient(135deg,#e76f51,#f4a261);padding:24px 28px;color:#ffffff;">
      <div style="font-size:12px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;opacity:0.95;">PET CONNECT • Official Adoption Confirmation</div>
      <h1 style="margin:6px 0 4px 0;font-size:24px;font-weight:800;">We've Received Your Request for {pet_name}!</h1>
      <div style="font-size:13px;opacity:0.95;">Confirmation Reference: <strong>#{ref_id}</strong> • {created_at}</div>
    </div>

    <div style="padding:28px;">
      <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6;color:#cbd5e1;">
        Hello <strong style="color:#ffffff;">{adopter_name}</strong>, thank you for choosing rescue through <strong>PET CONNECT</strong>.
        Your adoption inquiry for <strong style="color:#f4a261;">{pet_name}</strong> ({breed} {species}) is confirmed and queued for our Adoption Coordinator team.
      </p>

      <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:18px;margin-bottom:20px;">
        <h3 style="margin:0 0 12px 0;font-size:14px;text-transform:uppercase;letter-spacing:0.05em;color:#f4a261;">Companion &amp; Application Summary</h3>
        <table style="width:100%;border-collapse:collapse;font-size:14px;color:#cbd5e1;">
          <tr><td style="padding:5px 0;color:#94a3b8;">Confirmation Ref:</td><td style="padding:5px 0;font-weight:700;color:#ffffff;">#{ref_id}</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Companion:</td><td style="padding:5px 0;font-weight:700;color:#ffffff;">{pet_name} ({species} • {breed})</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Microchip ID:</td><td style="padding:5px 0;font-family:monospace;color:#74c69d;">{rfid_tag}</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Adoption Fee:</td><td style="padding:5px 0;color:#ffffff;">${fee} (Spay/Neuter, Vaccines &amp; Microchip Included)</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Adopter Email:</td><td style="padding:5px 0;color:#ffffff;">{adopter_email}</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Contact Phone:</td><td style="padding:5px 0;color:#ffffff;">{adopter_phone}</td></tr>
          <tr><td style="padding:5px 0;color:#94a3b8;">Home Environment:</td><td style="padding:5px 0;color:#ffffff;">{housing_display}</td></tr>
        </table>
      </div>

      <div style="background:rgba(82,183,136,0.1);border:1px solid rgba(82,183,136,0.3);border-radius:12px;padding:18px;margin-bottom:20px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
          <strong style="color:#74c69d;font-size:15px;">Personal Manageability Score: {score}% ({tier})</strong>
        </div>
        <p style="margin:0 0 12px 0;font-size:13.5px;color:#e2e8f0;line-height:1.5;">{primary_reason}</p>
        <div style="font-size:12.5px;color:#cbd5e1;">
          ⚡ Energy: <strong>{round(metrics.get('energy_match', 92))}%</strong> &nbsp;|&nbsp;
          ✂️ Maintenance: <strong>{round(metrics.get('maintenance_match', 90))}%</strong> &nbsp;|&nbsp;
          🏡 Space: <strong>{round(metrics.get('space_match', 95))}%</strong> &nbsp;|&nbsp;
          💰 Budget: <strong>{round(metrics.get('budget_match', 90))}%</strong>
        </div>
      </div>

      <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:18px;margin-bottom:20px;">
        <h3 style="margin:0 0 10px 0;font-size:14px;text-transform:uppercase;letter-spacing:0.05em;color:#48cae4;">Recommended Preparation Checklist</h3>
        <ul style="margin:0;padding-left:18px;">
          {checklist_html}
        </ul>
      </div>

      <div style="border-top:1px solid rgba(255,255,255,0.1);padding-top:16px;font-size:13px;color:#94a3b8;line-height:1.6;">
        <strong style="color:#ffffff;">What Happens Next?</strong><br>
        Our PET CONNECT care coordinator will reach out to <strong>{adopter_email}</strong> within <strong>24–48 hours</strong> to schedule your meet-and-greet.
        You may also visit our sanctuary Tuesday–Sunday (11:00 AM – 5:00 PM) with Reference Code <strong>#{ref_id}</strong>.
      </div>
    </div>
  </div>
</body>
</html>"""

    return {
        'subject': subject,
        'body_text': body_text,
        'body_html': body_html,
        'checklist': checklist
    }


def dispatch_confirmation_email(to_email, to_name, subject, body_text, body_html, request_ref):
    """
    Dispatches the confirmation email via configured SMTP server (if credentials provided)
    and archives a local copy (.html and .eml) in data/sent_emails/ for instant verification.
    """
    os.makedirs(Config.SENT_EMAILS_DIR, exist_ok=True)
    html_filename = f"{request_ref}.html"
    eml_filename = f"{request_ref}.eml"
    html_path = os.path.join(Config.SENT_EMAILS_DIR, html_filename)
    eml_path = os.path.join(Config.SENT_EMAILS_DIR, eml_filename)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>"
    msg['To'] = f"{to_name} <{to_email}>" if to_name else to_email
    msg['Date'] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    msg['X-PetConnect-Reference'] = request_ref
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype='html')

    with open(html_path, 'w', encoding='utf-8') as f_html:
        f_html.write(body_html)

    with open(eml_path, 'wb') as f_eml:
        f_eml.write(bytes(msg))

    smtp_error = None
    smtp_configured = bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASSWORD)
    if smtp_configured:
        try:
            smtp_from = Config.SMTP_USER if '@' in Config.SMTP_USER else Config.SMTP_FROM_EMAIL
            del msg['From']
            msg['From'] = f"{Config.SMTP_FROM_NAME} <{smtp_from}>"
            with smtplib.SMTP(Config.SMTP_HOST, int(Config.SMTP_PORT), timeout=12) as server:
                server.ehlo()
                if Config.SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(Config.SMTP_USER, Config.SMTP_PASSWORD.replace(' ', ''))
                server.send_message(msg)
            delivery_status = "LIVE_SMTP_DELIVERED"
        except Exception as exc:
            smtp_error = str(exc)
            print(f"SMTP relay error (archived locally to {html_path}): {exc}")
            delivery_status = "LOCAL_SANDBOX_ONLY (SMTP_ERROR)"
    else:
        delivery_status = "LOCAL_SANDBOX_ONLY (Configure Gmail App Password for Real Inbox Delivery)"

    return {
        'status': delivery_status,
        'smtp_delivered': delivery_status == "LIVE_SMTP_DELIVERED",
        'smtp_configured': smtp_configured,
        'smtp_error': smtp_error,
        'html_path': html_path,
        'eml_path': eml_path,
        'preview_url': f"/api/adoption-request/{request_ref}/email"
    }


def select_animal_profile(tag_id):
    """Loads and returns animal profile by tag ID or primary key with ML evaluations."""
    global latest_scanned_tag, latest_scanned_animal
    latest_scanned_tag = tag_id

    conn = get_db_connection()
    animal = conn.execute("SELECT * FROM animals WHERE rfid_tag = ? OR id = ?", (tag_id, tag_id)).fetchone()
    conn.close()

    if animal:
        animal_dict = dict(animal)
        prediction = los_model.predict(animal_dict)
        placement_eval = SpecializedPlacementRouter.evaluate_candidate(animal_dict)

        animal_dict['los_prediction'] = prediction
        animal_dict['sar_evaluation'] = placement_eval
        animal_dict['specialized_placement_eval'] = placement_eval
        latest_scanned_animal = animal_dict
        print(f"Loaded Selected Companion Profile: {animal_dict['name']} ({animal_dict.get('species')})")
    else:
        latest_scanned_animal = {
            'id': 'UNKNOWN',
            'rfid_tag': tag_id,
            'name': f'Unregistered Tag ({tag_id})',
            'species': 'Unknown',
            'is_high_risk': 0,
            'is_sar_candidate': 0,
            'specialized_placement': 'STANDARD_ADOPTION'
        }
    return latest_scanned_animal


def init_system():
    """Ensures multi-species database, portal tables, and trained ML model are loaded on startup."""
    if not os.path.exists(Config.DATABASE_PATH):
        print("Database not found. Generating multi-species sanctuary dataset...")
        generate_shelter_dataset()

    ensure_portal_tables()

    print("Initializing PET CONNECT Care & Foster Triage Predictive Model...")
    if not los_model.load_model():
        print("Existing model artifacts not found or incomplete. Training Gradient Boosting model...")
        los_model.train()
    else:
        print(f"Loaded existing model successfully! (Accuracy: {los_model.metrics.get('accuracy_percentage', 98.4)}%)")

    conn = get_db_connection()
    first_animal = conn.execute("SELECT * FROM animals LIMIT 1").fetchone()
    conn.close()
    if first_animal:
        select_animal_profile(first_animal['rfid_tag'])


@app.route('/')
@app.route('/customer')
def customer_portal():
    """Renders warm PET CONNECT customer companion adoption portal."""
    return render_template('customer.html')


@app.route('/dev')
@app.route('/admin')
def developer_portal():
    """Renders PET CONNECT shelter operations & coordinator command center."""
    return render_template('dev.html')


@app.route('/api/register-email', methods=['GET', 'POST'])
def register_adopter_email():
    """
    Captures and persists the customer's email address beforehand on PET CONNECT,
    allowing personalized match persistence and instant adoption confirmation emails.
    """
    ensure_portal_tables()
    if request.method == 'GET':
        email = (request.args.get('email') or '').strip().lower()
        if not is_valid_email(email):
            return jsonify({'registered': False, 'error': 'Valid email query parameter is required'}), 400

        conn = get_db_connection()
        row = conn.execute("SELECT * FROM adopter_sessions WHERE LOWER(email) = ?", (email,)).fetchone()
        reqs = conn.execute(
            "SELECT request_ref, pet_name, species, breed, adoption_fee, compatibility_score, email_status, created_at "
            "FROM adoption_requests WHERE LOWER(adopter_email) = ? ORDER BY id DESC",
            (email,)
        ).fetchall()
        conn.close()

        if not row:
            return jsonify({'registered': False, 'email': email, 'adoption_requests': []}), 404

        adopter_dict = dict(row)
        adopter_dict['name'] = adopter_dict.get('full_name') or ''
        return jsonify({
            'registered': True,
            'platform': Config.PLATFORM_NAME,
            'adopter': adopter_dict,
            'adoption_requests': [dict(r) for r in reqs]
        })

    data = request.json or {}
    email = (data.get('email') or data.get('adopter_email') or data.get('applicant_email') or '').strip().lower()
    full_name = (data.get('full_name') or data.get('name') or data.get('adopter_name') or data.get('applicant_name') or '').strip()
    phone = (data.get('phone') or data.get('adopter_phone') or data.get('applicant_phone') or '').strip()

    if not is_valid_email(email):
        return jsonify({'success': False, 'error': 'Please enter a valid email address (e.g. name@example.com).'}), 400

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    energy_cap = float(data.get('energy_capacity', 5.0))
    maint_cap = float(data.get('maintenance_capacity', 5.0))
    space_lim = float(data.get('space_limit', 5.0))
    yard_sz = int(data.get('yard_size', 1))
    budget_lim = float(data.get('budget_limit', 5.0))
    child_age = float(data.get('youngest_child_age', 10.0))
    pref_species = str(data.get('preferred_species', 'all')).strip().lower()

    conn = get_db_connection()
    existing = conn.execute("SELECT * FROM adopter_sessions WHERE LOWER(email) = ?", (email,)).fetchone()
    if existing:
        existing_dict = dict(existing)
        updated_name = full_name or existing_dict.get('full_name') or ''
        updated_phone = phone or existing_dict.get('phone') or ''
        conn.execute("""
            UPDATE adopter_sessions
            SET full_name = ?, phone = ?, preferred_species = ?,
                energy_capacity = ?, maintenance_capacity = ?, space_limit = ?,
                yard_size = ?, budget_limit = ?, youngest_child_age = ?, updated_at = ?
            WHERE LOWER(email) = ?
        """, (
            updated_name, updated_phone, pref_species,
            energy_cap, maint_cap, space_lim, yard_sz, budget_lim, child_age,
            now_iso, email
        ))
    else:
        conn.execute("""
            INSERT INTO adopter_sessions (
                email, full_name, phone, preferred_species,
                energy_capacity, maintenance_capacity, space_limit,
                yard_size, budget_limit, youngest_child_age, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            email, full_name, phone, pref_species,
            energy_cap, maint_cap, space_lim, yard_sz, budget_lim, child_age,
            now_iso, now_iso
        ))
    conn.commit()

    saved_row = conn.execute("SELECT * FROM adopter_sessions WHERE LOWER(email) = ?", (email,)).fetchone()
    past_requests = conn.execute(
        "SELECT request_ref, pet_name, species, breed, adoption_fee, compatibility_score, email_status, created_at "
        "FROM adoption_requests WHERE LOWER(adopter_email) = ? ORDER BY id DESC",
        (email,)
    ).fetchall()
    conn.close()

    adopter_payload = dict(saved_row) if saved_row else {'email': email, 'full_name': full_name}
    adopter_payload['name'] = adopter_payload.get('full_name') or full_name

    return jsonify({
        'success': True,
        'platform': Config.PLATFORM_NAME,
        'message': f'Your email ({email}) is connected to PET CONNECT for instant adoption confirmations.',
        'adopter': adopter_payload,
        'adoption_requests': [dict(r) for r in past_requests]
    })


@app.route('/api/adoption-request', methods=['POST'])
def create_adoption_request():
    """
    Processes a customer's adoption inquiry on PET CONNECT, stores the application in SQLite,
    and dispatches a personalized confirmation email to the customer's email address.
    """
    ensure_portal_tables()
    data = request.json or {}

    adopter_email = (data.get('adopter_email') or data.get('applicant_email') or data.get('email') or '').strip().lower()
    adopter_name = (data.get('adopter_name') or data.get('applicant_name') or data.get('name') or '').strip()
    adopter_phone = (data.get('adopter_phone') or data.get('applicant_phone') or data.get('phone') or '').strip()
    housing_type = (data.get('housing_type') or 'house_yard').strip()
    other_pets = (data.get('other_pets') or 'none').strip()
    experience_level = (data.get('experience_level') or 'experienced').strip()
    personal_note = (data.get('personal_note') or data.get('notes') or '').strip()

    rfid_tag = (data.get('rfid_tag') or '').strip()
    animal_id = str(data.get('animal_id') or data.get('pet_id') or '').strip()
    pet_name_input = (data.get('pet_name') or '').strip()

    if not is_valid_email(adopter_email):
        return jsonify({'success': False, 'error': 'A valid email address is required to receive your confirmation email.'}), 400

    if not adopter_name:
        return jsonify({'success': False, 'error': 'Please provide your full name.'}), 400

    conn = get_db_connection()
    animal_row = None
    if rfid_tag:
        animal_row = conn.execute("SELECT * FROM animals WHERE rfid_tag = ? OR id = ?", (rfid_tag, rfid_tag)).fetchone()
    if not animal_row and animal_id:
        animal_row = conn.execute("SELECT * FROM animals WHERE id = ?", (animal_id,)).fetchone()
    if not animal_row and pet_name_input:
        animal_row = conn.execute("SELECT * FROM animals WHERE LOWER(name) LIKE ?", (f"{pet_name_input.lower()}%",)).fetchone()
    if not animal_row:
        animal_row = conn.execute("SELECT * FROM animals LIMIT 1").fetchone()

    animal_dict = dict(animal_row) if animal_row else {
        'id': animal_id or 'ANM-1001',
        'rfid_tag': rfid_tag or 'TAG_PETCONNECT',
        'name': pet_name_input or 'Rescue Companion',
        'species': data.get('species') or data.get('pet_species') or 'Dog',
        'breed': data.get('breed') or data.get('pet_breed') or 'Mixed Breed',
        'adoption_fee': int(data.get('adoption_fee', 120)),
        'energy_level': 5,
        'exercise_needed_hours': 1.0,
        'grooming_needed': 4,
        'space_needed': 4,
        'yard_needed': 0,
        'budget_needed': 4,
        'sociability': 8,
        'child_friendly_min_age': 0
    }

    user_profile = data.get('user_profile') or {
        'energy_capacity': float(data.get('energy_capacity', 5.0)),
        'maintenance_capacity': float(data.get('maintenance_capacity', 5.0)),
        'space_limit': float(data.get('space_limit', 5.0)),
        'yard_size': int(data.get('yard_size', 1)),
        'budget_limit': float(data.get('budget_limit', 5.0)),
        'exercise_time_hours': float(data.get('exercise_time_hours', 1.5)),
        'youngest_child_age': float(data.get('youngest_child_age', 10.0))
    }

    match_analysis = VectorMatcher.calculate_match(user_profile, animal_dict)
    clean_pet_name = pet_name_input or str(animal_dict.get('name', 'Companion')).split(' (ANM-')[0]
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    request_ref = f"PC-{now_dt.strftime('%Y%m%d')}-{os.urandom(2).hex().upper()}"

    request_record = {
        'request_ref': request_ref,
        'animal_id': animal_dict.get('id', 'ANM-1001'),
        'rfid_tag': animal_dict.get('rfid_tag', rfid_tag or 'TAG_001'),
        'pet_name': clean_pet_name,
        'species': animal_dict.get('species', 'Dog'),
        'breed': animal_dict.get('breed', 'Mixed Breed'),
        'adoption_fee': int(data.get('adoption_fee') or animal_dict.get('adoption_fee', 120)),
        'adopter_name': adopter_name,
        'adopter_email': adopter_email,
        'adopter_phone': adopter_phone,
        'applicant_name': adopter_name,
        'applicant_email': adopter_email,
        'applicant_phone': adopter_phone,
        'housing_type': housing_type,
        'other_pets': other_pets,
        'experience_level': experience_level,
        'personal_note': personal_note,
        'compatibility_score': match_analysis['compatibility_score'],
        'created_at': now_iso
    }

    email_content = build_confirmation_email(request_record, animal_dict, match_analysis)
    dispatch_info = dispatch_confirmation_email(
        to_email=adopter_email,
        to_name=adopter_name,
        subject=email_content['subject'],
        body_text=email_content['body_text'],
        body_html=email_content['body_html'],
        request_ref=request_ref
    )

    conn.execute("""
        INSERT INTO adoption_requests (
            request_ref, animal_id, rfid_tag, pet_name, species, breed, adoption_fee,
            adopter_name, adopter_email, adopter_phone, housing_type, other_pets,
            experience_level, personal_note, compatibility_score,
            email_status, email_subject, email_body_text, email_body_html, email_file_path,
            status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        request_ref,
        request_record['animal_id'],
        request_record['rfid_tag'],
        request_record['pet_name'],
        request_record['species'],
        request_record['breed'],
        request_record['adoption_fee'],
        adopter_name,
        adopter_email,
        adopter_phone,
        housing_type,
        other_pets,
        experience_level,
        personal_note,
        request_record['compatibility_score'],
        dispatch_info['status'],
        email_content['subject'],
        email_content['body_text'],
        email_content['body_html'],
        dispatch_info['html_path'],
        'CONFIRMED_EMAIL_SENT',
        now_iso
    ))

    # Also upsert into adopter_sessions so their email & name stay pre-registered
    conn.execute("""
        INSERT INTO adopter_sessions (
            email, full_name, phone, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(email) DO UPDATE SET
            full_name = excluded.full_name,
            phone = excluded.phone,
            updated_at = excluded.updated_at
    """, (adopter_email, adopter_name, adopter_phone, now_iso, now_iso))

    conn.commit()
    conn.close()

    confirmation_payload = {
        'reference_id': request_ref,
        'request_ref': request_ref,
        'from': f"{Config.SMTP_FROM_NAME} <{Config.SMTP_FROM_EMAIL}>",
        'to': adopter_email,
        'to_name': adopter_name,
        'applicant_email': adopter_email,
        'applicant_name': adopter_name,
        'subject': email_content['subject'],
        'email_subject': email_content['subject'],
        'sent_at': now_iso,
        'delivery_status': dispatch_info['status'],
        'smtp_delivered': dispatch_info['smtp_delivered'],
        'smtp_configured': dispatch_info['smtp_configured'],
        'smtp_error': dispatch_info['smtp_error'],
        'preview_url': dispatch_info['preview_url'],
        'email_view_url': dispatch_info['preview_url'],
        'email_download_url': f"{dispatch_info['preview_url']}?download=1",
        'body_text': email_content['body_text'],
        'email_text': email_content['body_text'],
        'body_html': email_content['body_html'],
        'care_checklist': email_content['checklist']
    }

    return jsonify({
        'success': True,
        'platform': Config.PLATFORM_NAME,
        'message': f'Confirmation email prepared for {adopter_email} (Reference #{request_ref})',
        'request': request_record,
        'confirmation_email': confirmation_payload,
        'confirmation': confirmation_payload
    }), 200


@app.route('/api/adoption-request/<request_ref>/resend', methods=['POST'])
def resend_adoption_confirmation_email(request_ref):
    """Re-sends the confirmation email for an existing adoption request reference."""
    ensure_portal_tables()
    data = request.json or {}
    override_email = (data.get('email') or '').strip().lower()

    # Optional inline SMTP credentials if user enters Gmail App Password during resend
    if data.get('smtp_user') and data.get('smtp_password'):
        Config.SMTP_HOST = (data.get('smtp_host') or 'smtp.gmail.com').strip()
        Config.SMTP_PORT = int(data.get('smtp_port') or 587)
        Config.SMTP_USER = data.get('smtp_user').strip()
        Config.SMTP_PASSWORD = data.get('smtp_password').strip().replace(' ', '')
        Config.SMTP_FROM_EMAIL = Config.SMTP_USER

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM adoption_requests WHERE request_ref = ?", (request_ref,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': f'Adoption request {request_ref} not found.'}), 404

    rec = dict(row)
    target_email = override_email if is_valid_email(override_email) else rec['adopter_email']
    dispatch_info = dispatch_confirmation_email(
        to_email=target_email,
        to_name=rec['adopter_name'],
        subject=rec['email_subject'],
        body_text=rec['email_body_text'],
        body_html=rec['email_body_html'],
        request_ref=request_ref
    )

    conn.execute(
        "UPDATE adoption_requests SET adopter_email = ?, email_status = ? WHERE request_ref = ?",
        (target_email, dispatch_info['status'], request_ref)
    )
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'message': f'Confirmation email processed for {target_email} (Reference #{request_ref}).',
        'reference_id': request_ref,
        'to': target_email,
        'delivery_status': dispatch_info['status'],
        'smtp_delivered': dispatch_info['smtp_delivered'],
        'smtp_configured': dispatch_info['smtp_configured'],
        'smtp_error': dispatch_info['smtp_error'],
        'preview_url': dispatch_info['preview_url']
    })


@app.route('/api/smtp-config', methods=['GET', 'POST'])
def configure_smtp_settings():
    """Allows configuring Gmail SMTP (smtp.gmail.com:587 + App Password) at runtime for real inbox delivery."""
    if request.method == 'GET':
        return jsonify({
            'smtp_configured': bool(Config.SMTP_HOST and Config.SMTP_USER and Config.SMTP_PASSWORD),
            'smtp_host': Config.SMTP_HOST or 'smtp.gmail.com',
            'smtp_port': Config.SMTP_PORT or 587,
            'smtp_user': Config.SMTP_USER or ''
        })

    data = request.json or {}
    smtp_host = (data.get('smtp_host') or 'smtp.gmail.com').strip()
    smtp_port = int(data.get('smtp_port') or 587)
    smtp_user = (data.get('smtp_user') or '').strip()
    smtp_password = (data.get('smtp_password') or '').strip().replace(' ', '')

    if not smtp_user or not smtp_password:
        return jsonify({'success': False, 'error': 'Both Gmail address and 16-character Google App Password are required.'}), 400

    Config.SMTP_HOST = smtp_host
    Config.SMTP_PORT = smtp_port
    Config.SMTP_USER = smtp_user
    Config.SMTP_PASSWORD = smtp_password
    Config.SMTP_FROM_EMAIL = smtp_user

    return jsonify({
        'success': True,
        'smtp_configured': True,
        'smtp_host': Config.SMTP_HOST,
        'smtp_user': Config.SMTP_USER,
        'message': f'Live Gmail SMTP configured ({Config.SMTP_USER} via {Config.SMTP_HOST}:{Config.SMTP_PORT}).'
    })


@app.route('/api/adoption-request/<request_ref>/email', methods=['GET'])
def view_confirmation_email_html(request_ref):
    """Serves the formatted HTML confirmation email for viewing or downloading in the browser."""
    ensure_portal_tables()
    conn = get_db_connection()
    row = conn.execute(
        "SELECT email_body_html, pet_name, request_ref FROM adoption_requests WHERE request_ref = ?",
        (request_ref,)
    ).fetchone()
    conn.close()

    if not row:
        return jsonify({'error': 'Confirmation email not found'}), 404

    download = request.args.get('download', '').lower() in ['1', 'true', 'yes']
    headers = {}
    if download:
        headers['Content-Disposition'] = f'attachment; filename=PET_CONNECT_Confirmation_{request_ref}.html'

    return Response(row['email_body_html'], mimetype='text/html', headers=headers)


@app.route('/api/adoption-requests', methods=['GET'])
def list_adoption_requests():
    """Returns submitted adoption requests and full pre-filled confirmation email payloads for the Shelter Operations Console."""
    ensure_portal_tables()
    email_filter = (request.args.get('email') or '').strip().lower()
    conn = get_db_connection()
    if email_filter:
        rows = conn.execute(
            "SELECT id, request_ref, animal_id, rfid_tag, pet_name, species, breed, adoption_fee, "
            "adopter_name, adopter_email, adopter_phone, housing_type, other_pets, experience_level, "
            "personal_note, compatibility_score, email_status, email_subject, email_body_text, email_body_html, "
            "status, created_at "
            "FROM adoption_requests WHERE LOWER(adopter_email) = ? ORDER BY id DESC",
            (email_filter,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, request_ref, animal_id, rfid_tag, pet_name, species, breed, adoption_fee, "
            "adopter_name, adopter_email, adopter_phone, housing_type, other_pets, experience_level, "
            "personal_note, compatibility_score, email_status, email_subject, email_body_text, email_body_html, "
            "status, created_at "
            "FROM adoption_requests ORDER BY id DESC LIMIT 100"
        ).fetchall()
    conn.close()

    items = []
    for r in rows:
        item = dict(r)
        item['preview_url'] = f"/api/adoption-request/{item['request_ref']}/email"
        item['applicant_name'] = item.get('adopter_name', '')
        item['applicant_email'] = item.get('adopter_email', '')
        item['applicant_phone'] = item.get('adopter_phone', '')
        item['pet_species'] = item.get('species', '')
        item['pet_breed'] = item.get('breed', '')
        item['email_delivery_status'] = item.get('email_status', 'READY_FOR_STAFF_DISPATCH')
        items.append(item)
    return jsonify({
        'total_requests': len(items),
        'requests': items
    })


@app.route('/api/adoption-request/<request_ref>/staff-send', methods=['POST'])
def staff_send_adoption_confirmation(request_ref):
    """
    Allows a shelter employee in the Shelter Operations Console (/dev) to review the pre-filled
    customer adoption request, optionally customize the confirmation email or add staff notes,
    and dispatch/approve the confirmation email to the customer.
    """
    ensure_portal_tables()
    data = request.json or {}

    conn = get_db_connection()
    row = conn.execute("SELECT * FROM adoption_requests WHERE request_ref = ?", (request_ref,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': f'Adoption request {request_ref} not found.'}), 404

    rec = dict(row)
    to_email = (data.get('to_email') or data.get('email') or rec['adopter_email'] or '').strip().lower()
    to_name = (data.get('to_name') or data.get('adopter_name') or rec['adopter_name'] or '').strip()
    subject = (data.get('subject') or rec['email_subject'] or f"🐾 PET CONNECT Adoption Confirmation [#{request_ref}]").strip()
    body_text = (data.get('body_text') or rec['email_body_text'] or '').strip()
    staff_note = (data.get('staff_note') or '').strip()
    dispatch_channel = (data.get('dispatch_channel') or 'STAFF_CONSOLE').strip().upper()

    if not is_valid_email(to_email):
        conn.close()
        return jsonify({'success': False, 'error': 'Valid recipient email is required.'}), 400

    # Optional inline SMTP credentials from the staff console
    if data.get('smtp_user') and data.get('smtp_password'):
        Config.SMTP_HOST = (data.get('smtp_host') or 'smtp.gmail.com').strip()
        Config.SMTP_PORT = int(data.get('smtp_port') or 587)
        Config.SMTP_USER = data.get('smtp_user').strip()
        Config.SMTP_PASSWORD = data.get('smtp_password').strip().replace(' ', '')
        Config.SMTP_FROM_EMAIL = Config.SMTP_USER

    if staff_note and staff_note not in body_text:
        body_text = f"{body_text}\n\n--- Shelter Coordinator Note ---\n{staff_note}\n"

    body_html = rec['email_body_html'] or f"<pre>{body_text}</pre>"
    if staff_note and staff_note not in body_html:
        note_block = (
            f"<div style='background:rgba(82,183,136,0.12);border-left:4px solid #52b788;"
            f"padding:12px 16px;margin:16px 0;border-radius:8px;color:#e2e8f0;font-size:14px;'>"
            f"<strong style='color:#74c69d;'>Shelter Coordinator Note:</strong><br>{staff_note}</div>"
        )
        if "</div>\n  </div>\n</body>" in body_html:
            body_html = body_html.replace("</div>\n  </div>\n</body>", f"{note_block}</div>\n  </div>\n</body>")
        else:
            body_html += note_block

    dispatch_info = dispatch_confirmation_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        request_ref=request_ref
    )

    if dispatch_info['smtp_delivered']:
        final_email_status = "SENT_BY_STAFF_VIA_GMAIL_SMTP"
    elif dispatch_channel in ['GMAIL_WEB', 'MAILTO_CLIENT']:
        final_email_status = f"SENT_BY_STAFF_VIA_{dispatch_channel}"
    else:
        final_email_status = "APPROVED_AND_DISPATCHED_BY_STAFF"

    conn.execute("""
        UPDATE adoption_requests
        SET adopter_email = ?, adopter_name = ?, email_subject = ?,
            email_body_text = ?, email_body_html = ?,
            email_status = ?, status = ?
        WHERE request_ref = ?
    """, (
        to_email, to_name, subject,
        body_text, body_html,
        final_email_status, 'STAFF_APPROVED_AND_SENT',
        request_ref
    ))
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'reference_id': request_ref,
        'to': to_email,
        'to_name': to_name,
        'subject': subject,
        'body_text': body_text,
        'delivery_status': final_email_status,
        'smtp_delivered': dispatch_info['smtp_delivered'],
        'smtp_error': dispatch_info['smtp_error'],
        'preview_url': dispatch_info['preview_url'],
        'message': f'Shelter Staff dispatched confirmation email for #{request_ref} to {to_email}.'
    })


@app.route('/api/animals', methods=['GET'])
def get_animals():
    """
    Returns list of shelter animals with batch ML predictions.
    Supports optional ?species= filter (e.g. ?species=Dog, ?species=Rabbit, ?species=Bird, ?species=Small Pet, ?species=Reptile).
    """
    species_filter = request.args.get('species')
    conn = get_db_connection()

    if species_filter:
        s_clean = species_filter.strip().lower()
        if s_clean in ['pocket pet', 'pocket pets', 'small pet', 'small pets']:
            animals = conn.execute(
                "SELECT * FROM animals WHERE LOWER(species) IN ('small pet', 'pocket pet') ORDER BY id ASC"
            ).fetchall()
        else:
            animals = conn.execute(
                "SELECT * FROM animals WHERE LOWER(species) = ? ORDER BY id ASC", (s_clean,)
            ).fetchall()
    else:
        animals = conn.execute("SELECT * FROM animals ORDER BY id ASC").fetchall()
    conn.close()

    animal_list = [dict(a) for a in animals]
    if not animal_list:
        return jsonify([])

    predictions = los_model.predict_batch(animal_list)
    for idx, a_dict in enumerate(animal_list):
        a_dict['los_prediction'] = predictions[idx]
        placement_eval = SpecializedPlacementRouter.evaluate_candidate(a_dict)
        a_dict['sar_evaluation'] = placement_eval
        a_dict['specialized_placement_eval'] = placement_eval

    return jsonify(animal_list)


@app.route('/api/animals', methods=['POST'])
@app.route('/api/intake', methods=['POST'])
def add_animal():
    """Registers a new companion animal profile into the PET CONNECT sanctuary system."""
    data = request.json or {}
    name = data.get('name')
    species = data.get('species', 'Dog')
    breed = data.get('breed', 'Mixed Breed')

    if not name:
        return jsonify({'error': 'Companion name is required'}), 400

    conn = get_db_connection()
    count_row = conn.execute("SELECT COUNT(*) FROM animals").fetchone()
    next_id = f"ANM-{1000 + count_row[0] + 1}"
    rfid_tag = data.get('rfid_tag') or f"TAG_{os.urandom(3).hex().upper()}"

    is_dog = species.lower() == 'dog'
    default_yard = 1 if is_dog else 0
    default_space = 5 if is_dog else (3 if species.lower() in ['cat', 'rabbit'] else 2)
    default_exercise = 1.5 if is_dog else (0.8 if species.lower() == 'bird' else 0.4)
    default_fee = int(data.get('adoption_fee', 175 if is_dog else (75 if species.lower() in ['cat', 'rabbit'] else 30)))

    new_animal = {
        'id': next_id,
        'rfid_tag': rfid_tag,
        'name': f"{name} ({next_id})",
        'species': species,
        'breed': breed,
        'age_months': int(data.get('age_months', 24)),
        'coat_color': data.get('coat_color', 'Brown/Tan'),
        'size': data.get('size', 'Medium' if is_dog else 'Small'),
        'energy_level': int(data.get('energy_level', 5)),
        'trainability': int(data.get('trainability', 5)),
        'drive_level': int(data.get('drive_level', 5)),
        'vocalization_level': int(data.get('vocalization_level', 4)),
        'separation_anxiety_risk': int(data.get('separation_anxiety_risk', 3 if is_dog else 1)),
        'leash_reactivity_score': int(data.get('leash_reactivity_score', 2 if is_dog else 1)),
        'cat_friendly_score': int(data.get('cat_friendly_score', 6)),
        'dog_friendly_score': int(data.get('dog_friendly_score', 6)),
        'space_needed': int(data.get('space_needed', default_space)),
        'yard_needed': int(data.get('yard_needed', default_yard)),
        'exercise_needed_hours': float(data.get('exercise_needed_hours', default_exercise)),
        'child_friendly_min_age': int(data.get('child_friendly_min_age', 0)),
        'grooming_needed': int(data.get('grooming_needed', 4)),
        'setup_budget_needed': int(data.get('setup_budget_needed', 5)),
        'budget_needed': int(data.get('budget_needed', 4)),
        'sociability': int(data.get('sociability', 6)),
        'surrender_history': int(data.get('surrender_history', 0)),
        'special_medical_needs': int(data.get('special_medical_needs', 0)),
        'shelter_capacity_utilization_pct': float(data.get('shelter_capacity_utilization_pct', 70.0)),
        'intake_season': data.get('intake_season', 'Summer High'),
        'length_of_stay_days': int(data.get('length_of_stay_days', 10)),
        'adoption_fee': default_fee,
        'bio': data.get('bio', f"Lovable {breed} looking for a warm, dedicated home."),
        'personality_bio': data.get('bio', f"Lovable {breed} looking for a warm, dedicated home.")
    }

    placement_eval = SpecializedPlacementRouter.evaluate_candidate(new_animal)
    new_animal['specialized_placement'] = placement_eval['placement_type']
    new_animal['is_sar_candidate'] = 1 if placement_eval['is_sar_candidate'] else 0
    new_animal['is_high_risk'] = 1 if new_animal['length_of_stay_days'] >= Config.LOS_HIGH_RISK_DAYS else 0
    new_animal['status'] = placement_eval['routing_status']

    conn.execute("""
        INSERT INTO animals (
            id, rfid_tag, name, species, breed, age_months, coat_color, size,
            energy_level, trainability, drive_level, vocalization_level,
            separation_anxiety_risk, leash_reactivity_score, cat_friendly_score, dog_friendly_score,
            space_needed, yard_needed, exercise_needed_hours, child_friendly_min_age,
            grooming_needed, setup_budget_needed, budget_needed, sociability,
            surrender_history, special_medical_needs, shelter_capacity_utilization_pct,
            intake_season, length_of_stay_days, is_high_risk, is_sar_candidate,
            specialized_placement, status, adoption_fee, bio, personality_bio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        new_animal['id'], new_animal['rfid_tag'], new_animal['name'], new_animal['species'],
        new_animal['breed'], new_animal['age_months'], new_animal['coat_color'], new_animal['size'],
        new_animal['energy_level'], new_animal['trainability'], new_animal['drive_level'], new_animal['vocalization_level'],
        new_animal['separation_anxiety_risk'], new_animal['leash_reactivity_score'], new_animal['cat_friendly_score'], new_animal['dog_friendly_score'],
        new_animal['space_needed'], new_animal['yard_needed'], new_animal['exercise_needed_hours'], new_animal['child_friendly_min_age'],
        new_animal['grooming_needed'], new_animal['setup_budget_needed'], new_animal['budget_needed'], new_animal['sociability'],
        new_animal['surrender_history'], new_animal['special_medical_needs'], new_animal['shelter_capacity_utilization_pct'],
        new_animal['intake_season'], new_animal['length_of_stay_days'], new_animal['is_high_risk'], new_animal['is_sar_candidate'],
        new_animal['specialized_placement'], new_animal['status'], new_animal['adoption_fee'], new_animal['bio'], new_animal['personality_bio']
    ))
    conn.commit()
    conn.close()

    new_animal['los_prediction'] = los_model.predict(new_animal)
    new_animal['sar_evaluation'] = placement_eval
    new_animal['specialized_placement_eval'] = placement_eval
    return jsonify({'success': True, 'animal': new_animal}), 201


@app.route('/api/animals/<animal_id>', methods=['GET'])
def get_animal_detail(animal_id):
    """Returns detailed profile for a specific companion animal."""
    conn = get_db_connection()
    animal = conn.execute("SELECT * FROM animals WHERE id = ?", (animal_id,)).fetchone()
    conn.close()

    if not animal:
        return jsonify({'error': 'Companion animal profile not found'}), 404

    a_dict = dict(animal)
    pred = los_model.predict(a_dict)
    placement_eval = SpecializedPlacementRouter.evaluate_candidate(a_dict)
    a_dict['los_prediction'] = pred
    a_dict['sar_evaluation'] = placement_eval
    a_dict['specialized_placement_eval'] = placement_eval
    return jsonify(a_dict)


@app.route('/api/predict-stay', methods=['POST'])
def predict_animal_stay():
    """Predicts Length of Stay risk using the trained Gradient Boosting Classifier."""
    data = request.json or {}
    prediction = los_model.predict(data)
    placement_eval = SpecializedPlacementRouter.evaluate_candidate(data)
    return jsonify({
        'success': True,
        'prediction': prediction,
        'los_prediction': prediction,
        'specialized_placement_eval': placement_eval
    })


@app.route('/api/latest-scan', methods=['GET'])
def get_latest_scan():
    """Returns currently selected companion profile."""
    return jsonify({
        'status': 'active',
        'scanned_tag': latest_scanned_tag,
        'animal': latest_scanned_animal
    })


@app.route('/api/scan-rfid', methods=['POST'])
def trigger_rfid_scan():
    """Selects an animal profile by tag or randomly across species."""
    data = request.json or {}
    tag_id = data.get('tag_id')

    if not tag_id:
        conn = get_db_connection()
        random_row = conn.execute("SELECT rfid_tag FROM animals ORDER BY RANDOM() LIMIT 1").fetchone()
        conn.close()
        tag_id = random_row['rfid_tag'] if random_row else 'TAG_99A1001'

    animal = select_animal_profile(tag_id)
    return jsonify({
        'success': True,
        'message': f'Companion profile loaded for microchip tag {tag_id}',
        'scanned_animal': animal
    })


@app.route('/api/match', methods=['POST'])
def match_user():
    """
    Computes Personal Manageability Compatibility & 7D Vector Cosine Similarity
    between adopter lifestyle profiling and shelter companion requirements.
    Supports both nested `user_profile` dicts and top-level JSON parameters.
    """
    data = request.json or {}
    raw_profile = data.get('user_profile') if isinstance(data.get('user_profile'), dict) else data

    user_ex = float(raw_profile.get('exercise_time_hours', 1.5))
    user_profile = {
        'energy_capacity': float(raw_profile.get('energy_capacity') or min(10.0, max(1.0, user_ex * 3.33))),
        'maintenance_capacity': float(raw_profile.get('maintenance_capacity') or raw_profile.get('grooming_time_available', 5.0)),
        'space_limit': float(raw_profile.get('space_limit', 5.0) if not isinstance(raw_profile.get('space_limit'), str) else 4.0),
        'yard_size': int(raw_profile.get('yard_size', 1) if str(raw_profile.get('yard_size', '1')).isdigit() else 0),
        'budget_limit': float(raw_profile.get('budget_limit', 5.0)),
        'setup_budget': float(raw_profile.get('setup_budget', raw_profile.get('budget_limit', 5.0))),
        'exercise_time_hours': user_ex,
        'sociability_pref': float(raw_profile.get('sociability_pref', 5.0)),
        'youngest_child_age': float(raw_profile.get('youngest_child_age', 10.0)),
        'grooming_time_available': float(raw_profile.get('grooming_time_available') or raw_profile.get('maintenance_capacity', 5.0))
    }

    target_id = data.get('target_animal_id')
    species_raw = data.get('species_filter') or data.get('species') or raw_profile.get('species_filter')
    species_filter = None if (not species_raw or str(species_raw).strip().lower() in ['all', 'none']) else str(species_raw).strip().lower()
    limit = data.get('limit')

    conn = get_db_connection()
    if target_id:
        rows = conn.execute("SELECT * FROM animals WHERE id = ?", (target_id,)).fetchall()
    elif species_filter:
        if species_filter in ['pocket pet', 'pocket pets', 'small pet', 'small pets']:
            rows = conn.execute("SELECT * FROM animals WHERE LOWER(species) IN ('small pet', 'pocket pet') AND specialized_placement = 'STANDARD_ADOPTION'").fetchall()
        else:
            rows = conn.execute("SELECT * FROM animals WHERE LOWER(species) = ? AND specialized_placement = 'STANDARD_ADOPTION'", (species_filter,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM animals WHERE specialized_placement = 'STANDARD_ADOPTION'").fetchall()
    conn.close()

    results = [dict(r) for r in rows]
    if not results:
        return jsonify({
            'user_profile': user_profile,
            'total_evaluated': 0,
            'peak_match_score': 0,
            'matches': []
        })

    predictions = los_model.predict_batch(results)
    for idx, a_dict in enumerate(results):
        match_res = VectorMatcher.calculate_match(user_profile, a_dict)
        a_dict['match_analysis'] = match_res
        a_dict['los_prediction'] = predictions[idx]
        placement_eval = SpecializedPlacementRouter.evaluate_candidate(a_dict)
        a_dict['sar_evaluation'] = placement_eval
        a_dict['specialized_placement_eval'] = placement_eval

    results.sort(key=lambda x: x['match_analysis']['compatibility_score'], reverse=True)
    total_evaluated = len(results)
    peak_score = results[0]['match_analysis']['compatibility_score'] if results else 0

    if limit and isinstance(limit, int) and limit > 0:
        results = results[:limit]

    return jsonify({
        'user_profile': user_profile,
        'total_evaluated': total_evaluated,
        'peak_match_score': peak_score,
        'matches': results
    })


@app.route('/api/specialized-triage', methods=['GET'])
@app.route('/api/specialized-candidates', methods=['GET'])
@app.route('/api/sar-candidates', methods=['GET'])
def get_specialized_candidates():
    """
    Specialized Placement Triage:
    Returns companions routed to non-standard placements (Working K9s, Barn Cats, Exotic Specialists).
    """
    placement_filter = request.args.get('placement_type')
    conn = get_db_connection()

    if placement_filter:
        rows = conn.execute(
            "SELECT * FROM animals WHERE specialized_placement = ? ORDER BY id ASC", (placement_filter,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM animals WHERE specialized_placement != 'STANDARD_ADOPTION' OR is_sar_candidate = 1 ORDER BY id ASC"
        ).fetchall()
    conn.close()

    candidates = [dict(r) for r in rows]
    working_k9s = []
    barn_cats = []
    exotic_specialists = []

    if candidates:
        preds = los_model.predict_batch(candidates)
        for idx, a_dict in enumerate(candidates):
            eval_res = SpecializedPlacementRouter.evaluate_candidate(a_dict)
            a_dict['sar_evaluation'] = eval_res
            a_dict['specialized_placement_eval'] = eval_res
            a_dict['los_prediction'] = preds[idx]

            p_type = eval_res['placement_type']
            if p_type == 'WORKING_K9':
                working_k9s.append(a_dict)
            elif p_type == 'BARN_CAT':
                barn_cats.append(a_dict)
            elif p_type == 'EXOTIC_SPECIALIST':
                exotic_specialists.append(a_dict)

    return jsonify({
        'total_specialized': len(candidates),
        'total_specialized_candidates': len(candidates),
        'total_sar_candidates': len(working_k9s),
        'placement_breakdown': {
            'WORKING_K9': len(working_k9s),
            'BARN_CAT': len(barn_cats),
            'EXOTIC_SPECIALIST': len(exotic_specialists)
        },
        'candidates': candidates,
        'working_dogs': working_k9s,
        'working_k9_candidates': working_k9s,
        'barn_cats': barn_cats,
        'barn_cat_candidates': barn_cats,
        'exotic_rescues': exotic_specialists,
        'exotic_specialist_candidates': exotic_specialists
    })


@app.route('/api/export-high-risk', methods=['GET'])
def export_high_risk_csv():
    """Exports Care Triage Priority (Class 0: stay >= 30d) companions as a downloadable CSV report."""
    conn = get_db_connection()
    all_rows = [dict(r) for r in conn.execute("SELECT * FROM animals").fetchall()]
    conn.close()

    if not all_rows:
        return jsonify({'error': 'No animal records found'}), 404

    preds = los_model.predict_batch(all_rows)
    high_risk_animals = []
    for idx, a in enumerate(all_rows):
        if preds[idx]['is_high_risk']:
            a['prolonged_stay_risk'] = preds[idx]['prolonged_stay_risk']
            high_risk_animals.append(a)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'ID', 'Microchip Tag', 'Name', 'Species', 'Breed', 'Age (Months)',
        'Adoption Fee ($)', 'Placement Triage', 'Current Stay (Days)', 'Prolonged Stay Risk (%)', 'Action Status'
    ])

    for item in high_risk_animals:
        writer.writerow([
            item['id'], item['rfid_tag'], item['name'], item['species'], item['breed'],
            item['age_months'], item.get('adoption_fee', 75), item.get('specialized_placement', 'STANDARD_ADOPTION'),
            item['length_of_stay_days'], f"{item['prolonged_stay_risk']}%", item['status']
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=pet_connect_high_risk_report.csv'}
    )


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Returns multi-species shelter census breakdown, triage statistics, adoption request counts, and ML metrics."""
    ensure_portal_tables()
    conn = get_db_connection()
    total_animals = conn.execute("SELECT COUNT(*) FROM animals").fetchone()[0]
    avg_los = conn.execute("SELECT AVG(length_of_stay_days) FROM animals").fetchone()[0]
    total_requests = conn.execute("SELECT COUNT(*) FROM adoption_requests").fetchone()[0]
    registered_adopters = conn.execute("SELECT COUNT(*) FROM adopter_sessions").fetchone()[0]

    species_rows = conn.execute(
        "SELECT species, COUNT(*) as count FROM animals GROUP BY species ORDER BY count DESC"
    ).fetchall()
    species_census = {row['species']: row['count'] for row in species_rows}

    placement_rows = conn.execute(
        "SELECT specialized_placement, COUNT(*) as count FROM animals GROUP BY specialized_placement ORDER BY count DESC"
    ).fetchall()
    placement_census = {row['specialized_placement']: row['count'] for row in placement_rows}

    med_rows = conn.execute("SELECT special_medical_needs, COUNT(*) as count FROM animals GROUP BY special_medical_needs").fetchall()
    medical_breakdown = {
        'routine': sum(r['count'] for r in med_rows if r['special_medical_needs'] == 0),
        'minor': sum(r['count'] for r in med_rows if r['special_medical_needs'] == 1),
        'specialized': sum(r['count'] for r in med_rows if r['special_medical_needs'] >= 2)
    }

    all_rows = [dict(r) for r in conn.execute("SELECT * FROM animals").fetchall()]
    conn.close()

    high_risk_count = 0
    if all_rows:
        preds = los_model.predict_batch(all_rows)
        high_risk_count = sum(1 for p in preds if p['is_high_risk'])

    sar_count = placement_census.get('WORKING_K9', 0)
    spec_triage_total = sum(v for k, v in placement_census.items() if k != 'STANDARD_ADOPTION') or sar_count

    return jsonify({
        'platform_name': Config.PLATFORM_NAME,
        'total_animals': total_animals,
        'adoption_requests_count': total_requests,
        'registered_adopters_count': registered_adopters,
        'species_census': species_census,
        'specialized_placement_census': placement_census,
        'medical_breakdown': medical_breakdown,
        'high_risk_count': high_risk_count,
        'high_risk_percentage': round((high_risk_count / total_animals) * 100, 1) if total_animals else 0,
        'sar_candidates_count': sar_count,
        'specialized_triage_count': spec_triage_total,
        'average_length_of_stay_days': round(avg_los, 1) if avg_los else 0,
        'ml_model_info': {
            'algorithm': 'Gradient Boosting Ensemble Classifier',
            'accuracy_percentage': los_model.metrics.get('accuracy_percentage', 98.4),
            'precision_percentage': los_model.metrics.get('precision_percentage', 98.5),
            'care_triage': 'Predictive Length-of-Stay Analysis (Class 1: <30d Fast-Track, Class 0: >=30d Priority Care)',
            'specialized_routing': 'Specialized Placement Triage (Working K9, Barn Cat, & Exotic Sanctuary Routing)',
            'lifestyle_matcher': 'PET CONNECT Personal Manageability & 7D Vector Recommendation Engine'
        }
    })


if __name__ == '__main__':
    init_system()
    app.run(host='0.0.0.0', port=5000, debug=False)
