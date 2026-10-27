import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    PLATFORM_NAME = "PET CONNECT"
    PLATFORM_TAGLINE = "Companion Adoption & Personal Manageability Sanctuary"
    SECRET_KEY = os.environ.get('SECRET_KEY', 'pet-connect-secret-key-2026')
    DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'shelter.db')
    CSV_DATA_PATH = os.path.join(BASE_DIR, 'data', 'shelter_animals.csv')
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    SENT_EMAILS_DIR = os.path.join(BASE_DIR, 'data', 'sent_emails')

    # Email / Confirmation Dispatch Configuration
    SMTP_HOST = os.environ.get('PET_CONNECT_SMTP_HOST', '')
    SMTP_PORT = int(os.environ.get('PET_CONNECT_SMTP_PORT', 587))
    SMTP_USER = os.environ.get('PET_CONNECT_SMTP_USER', '')
    SMTP_PASSWORD = os.environ.get('PET_CONNECT_SMTP_PASSWORD', '')
    SMTP_USE_TLS = os.environ.get('PET_CONNECT_SMTP_TLS', 'true').lower() == 'true'
    SMTP_FROM_EMAIL = os.environ.get('PET_CONNECT_FROM_EMAIL', 'adoptions@petconnect.org')
    SMTP_FROM_NAME = os.environ.get('PET_CONNECT_FROM_NAME', 'PET CONNECT Adoption Team')

    # Specialized Placement Triage Criteria
    # Humane shelter routing for animals needing non-standard home environments
    SPECIALIZED_PLACEMENT_CRITERIA = {
        'WORKING_K9': {
            'species': 'Dog',
            'min_energy': 8,
            'min_trainability': 8,
            'min_drive': 8,
            'roles': ['Search & Rescue', 'Disaster Assistance', 'Working K9 Detection']
        },
        'BARN_CAT': {
            'species': 'Cat',
            'min_drive': 7,
            'max_sociability': 4,
            'roles': ['Working Barn Cat', 'Rural Sanctuary', 'Humane Rodent Deterrence']
        },
        'EXOTIC_SPECIALIST': {
            'species': ['Reptile', 'Bird'],
            'min_setup_budget': 6,
            'roles': ['Exotic Foster Care', 'Avian / Herpetological Sanctuary Placement']
        }
    }

    # Backward-compatible SAR Thresholds for existing references
    SAR_THRESHOLDS = {
        'energy_level': 8,       # Minimum energy level out of 10
        'trainability': 8,       # Minimum trainability rating out of 10
        'drive_level': 8         # Minimum working/prey/ball drive rating out of 10
    }

    # Care & Foster Triage (Length of Stay Predictive Risk Threshold)
    LOS_HIGH_RISK_DAYS = 30    # Stay >= 30 days triggers proactive foster care & featured profile outreach

    # Multi-Species Sanctuary Configuration
    SUPPORTED_SPECIES = ['Dog', 'Cat', 'Rabbit', 'Bird', 'Small Pet', 'Reptile']


PLATFORM_NAME = Config.PLATFORM_NAME

