# 🐾 PET CONNECT: Animal Rescue & Companion Matching Platform

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Framework-Flask%20%7C%20Scikit--Learn-green.svg)](https://flask.palletsprojects.com/)
[![Species Supported](https://img.shields.io/badge/Species-Dogs%20%7C%20Cats%20%7C%20Rabbits%20%7C%20Birds%20%7C%20Pocket%20Pets%20%7C%20Reptiles-orange.svg)]()
[![ML Model](https://img.shields.io/badge/Stay%20Classifier-Gradient%20Boosting-brightgreen.svg)]()
[![Matching Engine](https://img.shields.io/badge/Matcher-Multi--Dimensional%20Manageability%20%2B%207D%20Cosine-purple.svg)]()

**PET CONNECT** is an authentic, compassionate, and full-stack animal rescue and sanctuary platform. Designed to modernize shelter care coordination, optimize lifelong companion adoption matching, and proactively manage stay durations across diverse rescue species, **PET CONNECT** bridges prospective adopters with rescue companions based on what adopters can realistically manage every day.

---

## 🌟 Core Innovation: Personal Manageability & Lifestyle Matching

The central specialty of **PET CONNECT** is **matching adopters with companions that fit their daily capacity** across 5 realistic dimensions:

1. **⚡ Manageable Energy & Exercise**: Matches daily exercise availability (30m to 2h+) against the companion's energy level and exercise needs.
2. **✂️ Maintenance & Grooming Capacity**: Balances weekly grooming/upkeep availability against coat complexity and specialized medical attention.
3. **🏡 Living Space & Yard**: Evaluates indoor square footage and outdoor yard access (0: Apartment / No Yard to 3: Acreage). Indoor species (cats, rabbits, birds, pocket pets, reptiles) achieve 98–100% compatibility in apartment homes.
4. **💰 Monthly Care Budget**: Balances upfront adoption fees and ongoing nutrition/veterinary costs against adopter budget limits.
5. **👶 Family & Child Safety**: Enforces safety thresholds factoring youngest household child age and companion sociability.

### Matching Architecture
The matching engine (`ml/matcher.py`) blends:
- **60% Weighted Manageability Composite**: Quantifies daily lifestyle fit and flags potential surrender/neglect risks before adoption.
- **40% 7-Dimensional Vector Cosine Similarity**: Captures multi-attribute temperament and environmental compatibility.
- **Humane Explanations & Care Checklists**: Produces plain-English descriptions explaining why each companion is an ideal fit along with species-tailored care checklists.

---

## 🌐 Dual-Portal Architecture

The platform provides two dedicated, purpose-built interfaces:

```
                                  +---------------------------------------+
                                  |        PET CONNECT SANCTUARY          |
                                  |            (app.py Controller)        |
                                  +-------------------+-------------------+
                                                      |
                         +----------------------------+----------------------------+
                         |                                                         |
                         v                                                         v
        +----------------------------------+                      +----------------------------------+
        |   1. CUSTOMER ADOPTION PORTAL    |                      |  2. SHELTER OPERATIONS CONSOLE   |
        |        (URL: / or /customer)     |                      |       (URL: /dev or /admin)      |
        +----------------------------------+                      +----------------------------------+
        | • PET CONNECT Sanctuary Design   |                      | • Shelter Care Coordinator Hub   |
        | • Upfront Adopter Email Capture  |                      | • 📋 Animal Directory & Intake   |
        | • 6 Species (Dogs, Cats, Rabbits,|                      | • 🧭 Lifestyle & Manageability   |
        |   Birds, Pocket Pets, Reptiles)  |                      | • 🧡 Long-Stay Foster Queue (&ge;30d)|
        | • Interactive Manageability Tool |                      | • 🛡️ Specialized Placement Triage|
        | • 1-Click Lifestyle Presets      |                      | • 📊 Real Shelter Operations KPIs|
        | • Instant Confirmation Emails    |                      | • ✉️ Adoption Inquiries & Emails |
        +----------------------------------+                      +----------------------------------+
```

### 🐾 1. Customer Adoption Portal (`/customer` or `/`)
- **Upfront Adopter Email Registration**: Greets visitors with an upfront email check-in modal and persistent top bar (`POST /api/register-email`), saving adopter sessions in SQLite and pre-filling adoption inquiry forms automatically.
- **Automated Adoption Confirmation Emails**: When a customer submits an adoption request (`POST /api/adoption-request`), **PET CONNECT** generates and dispatches a rich HTML & plain-text confirmation email containing their reference number, match breakdown, personalized species care checklist, and next-step meet-and-greet instructions. Customers can view, download, or resend their confirmation email directly from the web receipt.
- **Interactive Manageability Widget**: Sliders for Energy, Maintenance, Space, Budget, and Youngest Child.
- **1-Click Lifestyle Presets**:
  - 🧘 *Low Maintenance & Chill* (Calm, low-brushing indoor companions)
  - 🏃 *Active Adventure Partner* (Athletic, high-energy companions)
  - 🏢 *Apartment Friendly* (Indoor companions with zero yard requirement)
  - 👨‍👩‍👧 *Family with Kids* (Gentle, patient, child-safe companions)
  - 💵 *Budget-Friendly Pet* (Minimal monthly care and setup costs)
- **Rich Companion Cards**:
  - High-res photography & handcrafted SVG species illustrations.
  - Prominent Compatibility Score Badge (e.g. `98% Match`).
  - Personalized match reason callout.
  - Sub-stat mini-meters (`⚡ Energy`, `✂️ Maintenance`, `🏡 Space`, `💰 Budget`).
  - Heart bookmarking with saved favorites drawer.
  - Realistic adoption inquiry application modal with instant confirmation email receipt.

### 📋 2. Shelter Operations Console (`/dev`)
- **Executive Operations KPIs**: Total census, average length of stay, foster alerts, specialized triage count.
- **Operational Tabs**:
  1. **📋 Animal Directory & Intake**: Microchip RFID scanning, care sheets, behavioral metrics, new animal intake.
  2. **🧭 Lifestyle & Manageability Matcher**: Staff-facing matching tool to advise walk-in adopters.
  3. **🧡 Long-Stay Foster Queue**: Flags animals in care $\ge 30\text{ days}$ for foster outreach and sponsorship.
  4. **🛡️ Specialized Animal Triage**: Automated routing for Working Dogs (Search & Rescue), Working Barn Cats, and Exotic Sanctuary habitats.
  5. **📊 Shelter Census & Analytics**: Species distribution, stay risk distributions, and medical triage breakdown.

---

## 🤖 Machine Learning & Data Pipeline

### Real-World Shelter Datasets
Integrated from open municipal animal shelter repositories:
- **Austin Animal Center (AAC)**: Real intake and outcome data spanning thousands of rescue animals.
- **Sonoma County Animal Services**: Multi-species demographics and intake reasons.
- **Multi-Species Master Dataset (`data/real_shelter_multispecies_master.csv`)**: 1,998 real-world records covering Dogs, Cats, Rabbits, Birds, Pocket Pets, and Reptiles.
- Comprehensive dataset research documented in [`data/RECOMMENDED_DATASETS.md`](data/RECOMMENDED_DATASETS.md).
- Automated live ingestion script: [`data/fetch_real_datasets.py`](data/fetch_real_datasets.py).

### Length of Stay (LOS) Classifier (`ml/los_classifier.py`)
- **Algorithm**: Gradient Boosting Classifier (`HistGradientBoostingClassifier` / `GradientBoostingClassifier`).
- **Target**: Stay risk classification (Low Stay Risk $< 30$ days vs. Prolonged Stay Risk $\ge 30$ days).
- **Features**: Age, species, breed, intake season, special medical needs, behavior scores, size, and coat color.
- **Metrics**: 85.0% accuracy on real shelter multi-species data, cross-validated and exported to `models/`.

---

## 📁 Repository Structure

```
Anagha_vn/
├── app.py                     # Main Flask web application & REST API controller
├── config.py                  # Global application configuration & database paths
├── requirements.txt           # Python dependencies
├── start.sh                   # Unix launch script with automatic venv setup
├── start.bat                  # Windows launch script
├── README.md                  # System documentation & architecture guide
│
├── data/                      # Data storage & ingestion pipelines
│   ├── RECOMMENDED_DATASETS.md # Survey of real-world animal shelter datasets
│   ├── fetch_real_datasets.py  # Live API fetcher for Austin & Sonoma County shelter data
│   ├── generator.py           # Multi-species synthetic dataset generator
│   ├── real_shelter_multispecies_master.csv # Master multi-species dataset (1,998 records)
│   ├── austin_real_shelter_dataset.csv     # Austin Animal Center data subset
│   ├── sonoma_real_shelter_dataset.csv     # Sonoma County data subset
│   ├── shelter_animals.csv    # Canonical shelter catalog
│   └── shelter.db             # Local SQLite database (runtime generated, gitignored)
│
├── ml/                        # Machine learning & algorithmic matching modules
│   ├── matcher.py             # Multi-dimensional manageability & vector cosine matcher
│   ├── los_classifier.py      # Length of stay predictive model & training pipeline
│   └── outlier_router.py      # Specialized placement triage (SAR K9, Barn Cat, Exotic)
│
├── models/                    # Pre-trained ML artifacts & metadata
│   ├── los_gb_model.pkl       # Trained Gradient Boosting model
│   ├── los_svm_model.pkl      # Baseline SVM model
│   ├── scaler.pkl             # Feature scaler
│   ├── encoders.pkl           # Categorical label encoders
│   └── model_metrics.json     # Evaluation metrics & performance benchmarks
│
├── static/                    # Frontend static assets
│   ├── css/
│   │   ├── customer.css       # Customer adoption portal styles & animations
│   │   └── style.css          # Shelter operations console styles
│   ├── js/
│   │   ├── customer.js        # Adoption portal logic, sliders, presets, cards
│   │   └── main.js            # Operations console tabs, charts, RFID scanner
│   └── images/
│       └── pets/              # High-resolution companion photos across species
│
└── templates/                 # Jinja2 HTML templates
    ├── index.html             # Platform gateway & portal selector
    ├── customer.html          # Public Adoption Portal
    └── dev.html               # Shelter Operations & Triage Hub
```

---

## ⚡ Quick Start Guide

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone & Navigate
```bash
git clone https://github.com/jeromegego-cell/Anagha_vn.git
cd Anagha_vn
```

### 2. Launch with Helper Script
**Linux / macOS:**
```bash
chmod +x start.sh
./start.sh
```

**Windows:**
```bat
start.bat
```

*Or manually:*
```bash
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### 3. Open in Browser
- **🐾 Public Adoption Portal**: [http://localhost:5000/customer](http://localhost:5000/customer)
- **📋 Shelter Operations Console**: [http://localhost:5000/dev](http://localhost:5000/dev)

---

## 📡 REST API Reference

| Endpoint | Method | Description | Key Parameters |
| --- | --- | --- | --- |
| `/api/register-email` | `GET` / `POST` | Register customer email beforehand & retrieve adopter session | `email`, `name`, `phone` |
| `/api/adoption-request` | `POST` | Submit adoption request & dispatch confirmation email | `pet_id`, `applicant_name`, `applicant_email`, `applicant_phone`, `user_profile` |
| `/api/adoption-request/<ref>/email` | `GET` | View or download confirmation email (`html`, `eml`, `json`) | `format` |
| `/api/adoption-request/<ref>/resend` | `POST` | Resend confirmation email to customer | `email` (optional override) |
| `/api/adoption-requests` | `GET` | List submitted adoption inquiries & email status for staff | None |
| `/api/match` | `POST` | Calculate lifestyle & manageability match scores | `energy_capacity`, `maintenance_capacity`, `space_limit`, `yard_size`, `budget_limit`, `youngest_child_age`, `species_filter`, `limit` |
| `/api/animals` | `GET` | Retrieve shelter companion catalog with filters | `species`, `search`, `limit`, `offset` |
| `/api/predict-stay` | `POST` | Predict Length of Stay risk using Gradient Boosting | Animal profile JSON |
| `/api/specialized-triage` | `GET` | Retrieve animals routed to specialized placements | `placement_type` (`WORKING_K9`, `BARN_CAT`, `EXOTIC_SPECIALIST`) |
| `/api/scan-rfid` | `POST` | Simulate microchip scan and load companion record | `tag_id` (optional, picks random if empty) |
| `/api/stats` | `GET` | Shelter operations statistics and census analytics | None |
| `/api/intake` | `POST` | Register a new companion intake into the sanctuary | Companion attributes JSON |

---

## 📄 License
This project is licensed under the MIT License — compassionate non-profit technology for shelter animals everywhere.
