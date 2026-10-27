/* ==========================================================================
   PET CONNECT Animal Rescue & Sanctuary — Customer Portal Logic
   Upfront Email Registration, Manageability Matching & Confirmation Emails
   ========================================================================== */

let customerAnimals = [];
let favoriteIds = new Set();
let activeFilter = 'all';
let searchQuery = '';
let manageabilityDebounceTimer = null;

// Pre-registered customer identity (asked beforehand)
let preRegisteredEmail = '';
let preRegisteredName = '';
let preRegisteredPhone = '';
let pendingPetModalArgs = null;
let currentSelectedPet = null;
let lastConfirmationRef = null;

document.addEventListener('DOMContentLoaded', () => {
    loadFavoritesFromStorage();
    loadAdopterIdentityFromStorage();
    updateManageabilityDisplayLabels();
    fetchCustomerAnimals();
});

// Load saved favorites from browser storage
function loadFavoritesFromStorage() {
    try {
        const saved = localStorage.getItem('pet_connect_favorites');
        if (saved) {
            favoriteIds = new Set(JSON.parse(saved));
            updateSavedCountBadge();
        }
    } catch (e) {
        console.warn('Could not load favorites from localStorage', e);
    }
}

function saveFavoritesToStorage() {
    try {
        localStorage.setItem('pet_connect_favorites', JSON.stringify(Array.from(favoriteIds)));
        updateSavedCountBadge();
    } catch (e) {
        console.warn('Could not save favorites to localStorage', e);
    }
}

function updateSavedCountBadge() {
    const badge = document.getElementById('saved-count');
    if (badge) badge.innerText = favoriteIds.size;
}

// ==========================================================================
// Upfront Customer Email Registration ("Ask for their email beforehand")
// ==========================================================================
function loadAdopterIdentityFromStorage() {
    try {
        preRegisteredEmail = (localStorage.getItem('pet_connect_adopter_email') || '').trim();
        preRegisteredName = (localStorage.getItem('pet_connect_adopter_name') || '').trim();
        preRegisteredPhone = (localStorage.getItem('pet_connect_adopter_phone') || '').trim();
    } catch (e) {
        console.warn('Could not read adopter email from localStorage', e);
    }

    syncAdopterEmailUI();

    // Ask for the customer's email beforehand when they visit the web portal
    if (!preRegisteredEmail) {
        setTimeout(() => {
            openEmailOnboardingModal();
        }, 300);
    }
}

function saveAdopterIdentityToStorage(email, name, phone) {
    preRegisteredEmail = (email || '').trim().toLowerCase();
    if (name !== undefined && name !== null && String(name).trim() !== '') {
        preRegisteredName = String(name).trim();
    }
    if (phone !== undefined && phone !== null && String(phone).trim() !== '') {
        preRegisteredPhone = String(phone).trim();
    }

    try {
        localStorage.setItem('pet_connect_adopter_email', preRegisteredEmail);
        if (preRegisteredName) localStorage.setItem('pet_connect_adopter_name', preRegisteredName);
        if (preRegisteredPhone) localStorage.setItem('pet_connect_adopter_phone', preRegisteredPhone);
    } catch (e) {
        console.warn('Could not persist adopter identity to localStorage', e);
    }

    syncAdopterEmailUI();
}

function syncAdopterEmailUI() {
    const headerBtn = document.getElementById('header-email-status-btn');
    const headerLabel = document.getElementById('header-email-label');
    const inlineEmailInput = document.getElementById('inline-adopter-email');
    const inlineNameInput = document.getElementById('inline-adopter-name');
    const inlineBtnText = document.getElementById('inline-email-btn-text');
    const inlineSubtext = document.getElementById('upfront-email-subtext');
    const banner = document.getElementById('upfront-email-banner');

    const modalEmailInput = document.getElementById('pre-adopter-email');
    const modalNameInput = document.getElementById('pre-adopter-name');
    const modalPhoneInput = document.getElementById('pre-adopter-phone');

    const adoptFormEmail = document.getElementById('adopter-email');
    const adoptFormName = document.getElementById('adopter-name');
    const adoptFormPhone = document.getElementById('adopter-phone');

    if (preRegisteredEmail) {
        if (headerBtn) headerBtn.classList.add('connected');
        if (headerLabel) headerLabel.innerText = `Connected: ${preRegisteredEmail}`;
        if (inlineEmailInput) inlineEmailInput.value = preRegisteredEmail;
        if (inlineNameInput && preRegisteredName) inlineNameInput.value = preRegisteredName;
        if (inlineBtnText) inlineBtnText.innerText = 'Update Email';
        if (inlineSubtext) {
            inlineSubtext.innerHTML = `<strong style="color: #74c69d;">✓ Connected as ${preRegisteredName ? preRegisteredName + ' (' + preRegisteredEmail + ')' : preRegisteredEmail}.</strong> Your adoption requests will automatically send confirmation emails to this address.`;
        }
        if (banner) banner.classList.add('connected');
    } else {
        if (headerBtn) headerBtn.classList.remove('connected');
        if (headerLabel) headerLabel.innerText = 'Set Email for Instant Confirmation';
        if (inlineBtnText) inlineBtnText.innerText = 'Connect Email';
        if (banner) banner.classList.remove('connected');
    }

    if (modalEmailInput && preRegisteredEmail) modalEmailInput.value = preRegisteredEmail;
    if (modalNameInput && preRegisteredName) modalNameInput.value = preRegisteredName;
    if (modalPhoneInput && preRegisteredPhone) modalPhoneInput.value = preRegisteredPhone;

    if (adoptFormEmail && preRegisteredEmail) adoptFormEmail.value = preRegisteredEmail;
    if (adoptFormName && preRegisteredName && !adoptFormName.value) adoptFormName.value = preRegisteredName;
    if (adoptFormPhone && preRegisteredPhone && !adoptFormPhone.value) adoptFormPhone.value = preRegisteredPhone;
}

function openEmailOnboardingModal() {
    const modal = document.getElementById('email-onboarding-modal');
    if (!modal) return;
    syncAdopterEmailUI();
    const errEl = document.getElementById('pre-email-error-msg');
    if (errEl) errEl.style.display = 'none';
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';

    setTimeout(() => {
        const emailField = document.getElementById('pre-adopter-email');
        if (emailField) emailField.focus();
    }, 100);
}

function closeEmailOnboardingModal() {
    const modal = document.getElementById('email-onboarding-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function handleEmailModalBackdropClick(e) {
    if (e.target.id === 'email-onboarding-modal') {
        closeEmailOnboardingModal();
    }
}

async function registerEmailWithBackend(email, name, phone) {
    const payload = {
        email: email,
        full_name: name || '',
        phone: phone || '',
        preferred_species: activeFilter,
        ...getManageabilityUserProfile()
    };

    const res = await fetch('/api/register-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
        throw new Error(data.error || 'Could not register email address.');
    }
    saveAdopterIdentityToStorage(email, name, phone);
    return data;
}

async function submitPreRegistrationEmail(e) {
    e.preventDefault();
    const emailEl = document.getElementById('pre-adopter-email');
    const nameEl = document.getElementById('pre-adopter-name');
    const phoneEl = document.getElementById('pre-adopter-phone');
    const errEl = document.getElementById('pre-email-error-msg');
    const submitBtn = document.getElementById('pre-email-submit-btn');

    const email = (emailEl ? emailEl.value : '').trim();
    const name = (nameEl ? nameEl.value : '').trim();
    const phone = (phoneEl ? phoneEl.value : '').trim();

    if (errEl) errEl.style.display = 'none';
    if (submitBtn) submitBtn.disabled = true;

    try {
        await registerEmailWithBackend(email, name, phone);
        closeEmailOnboardingModal();

        // If customer clicked "Meet Me & Apply to Adopt" before setting email, open that pet modal now!
        if (pendingPetModalArgs) {
            const args = pendingPetModalArgs;
            pendingPetModalArgs = null;
            openAdoptionModal(...args);
        }
    } catch (err) {
        if (errEl) {
            errEl.innerText = err.message || 'Please enter a valid email address.';
            errEl.style.display = 'block';
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function handleInlineEmailRegistration(e) {
    e.preventDefault();
    const emailEl = document.getElementById('inline-adopter-email');
    const nameEl = document.getElementById('inline-adopter-name');
    const btnText = document.getElementById('inline-email-btn-text');

    const email = (emailEl ? emailEl.value : '').trim();
    const name = (nameEl ? nameEl.value : '').trim();
    if (!email) return;

    const origText = btnText ? btnText.innerText : 'Connect Email';
    if (btnText) btnText.innerText = 'Saving...';

    try {
        await registerEmailWithBackend(email, name, preRegisteredPhone);
        if (btnText) btnText.innerText = 'Connected ✓';
        setTimeout(() => syncAdopterEmailUI(), 1200);
    } catch (err) {
        alert(err.message || 'Please enter a valid email address.');
        if (btnText) btnText.innerText = origText;
    }
}

// ==========================================================================
// Species Configuration & Handcrafted SVG Visuals
// ==========================================================================
const SPECIES_CONFIG = {
    dog: {
        emoji: '🐕',
        label: 'Dog',
        badgeBg: 'rgba(231, 111, 81, 0.2)',
        badgeColor: '#f4a261',
        defaultFee: 150
    },
    cat: {
        emoji: '🐈',
        label: 'Cat',
        badgeBg: 'rgba(160, 108, 213, 0.2)',
        badgeColor: '#c77dff',
        defaultFee: 75
    },
    rabbit: {
        emoji: '🐇',
        label: 'Rabbit',
        badgeBg: 'rgba(82, 183, 136, 0.2)',
        badgeColor: '#74c69d',
        defaultFee: 45
    },
    bird: {
        emoji: '🦜',
        label: 'Bird',
        badgeBg: 'rgba(0, 180, 216, 0.2)',
        badgeColor: '#48cae4',
        defaultFee: 35
    },
    'pocket pet': {
        emoji: '🐹',
        label: 'Pocket Pet',
        badgeBg: 'rgba(244, 162, 97, 0.2)',
        badgeColor: '#f4a261',
        defaultFee: 25
    },
    'small pet': {
        emoji: '🐹',
        label: 'Pocket Pet',
        badgeBg: 'rgba(244, 162, 97, 0.2)',
        badgeColor: '#f4a261',
        defaultFee: 25
    },
    reptile: {
        emoji: '🦎',
        label: 'Reptile',
        badgeBg: 'rgba(112, 162, 136, 0.2)',
        badgeColor: '#90be6d',
        defaultFee: 45
    }
};

function getSpeciesConfig(speciesName) {
    const key = (speciesName || 'dog').toLowerCase().trim();
    return SPECIES_CONFIG[key] || SPECIES_CONFIG['dog'];
}

function getSpeciesSVGIllustration(species, name) {
    const s = (species || '').toLowerCase().trim();

    if (s.includes('rabbit')) {
        return `
            <div class="pet-illustrated-media" style="background: linear-gradient(135deg, #1b2e25, #2d4a3e);">
                <div class="avatar-svg-container">
                    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <ellipse cx="38" cy="28" rx="8" ry="24" fill="#e9edc9" transform="rotate(-8 38 28)"/>
                        <ellipse cx="38" cy="28" rx="4.5" ry="17" fill="#f4a261" opacity="0.6" transform="rotate(-8 38 28)"/>
                        <ellipse cx="62" cy="28" rx="8" ry="24" fill="#e9edc9" transform="rotate(8 62 28)"/>
                        <ellipse cx="62" cy="28" rx="4.5" ry="17" fill="#f4a261" opacity="0.6" transform="rotate(8 62 28)"/>
                        <circle cx="50" cy="58" r="26" fill="#fefae0"/>
                        <ellipse cx="40" cy="65" rx="10" ry="7" fill="#faedcd"/>
                        <ellipse cx="60" cy="65" rx="10" ry="7" fill="#faedcd"/>
                        <ellipse cx="41" cy="54" rx="3.5" ry="4.5" fill="#2b2d42"/>
                        <circle cx="42" cy="52.5" r="1.2" fill="#fff"/>
                        <ellipse cx="59" cy="54" rx="3.5" ry="4.5" fill="#2b2d42"/>
                        <circle cx="60" cy="52.5" r="1.2" fill="#fff"/>
                        <polygon points="50,62 46,59 54,59" fill="#e76f51"/>
                        <path d="M50 62 Q50 67 45 68 M50 62 Q50 67 55 68" stroke="#7f4f24" stroke-width="1.8" stroke-linecap="round" fill="none"/>
                        <line x1="28" y1="62" x2="16" y2="60" stroke="#d4a373" stroke-width="1.4" stroke-linecap="round"/>
                        <line x1="28" y1="66" x2="15" y2="67" stroke="#d4a373" stroke-width="1.4" stroke-linecap="round"/>
                        <line x1="72" y1="62" x2="84" y2="60" stroke="#d4a373" stroke-width="1.4" stroke-linecap="round"/>
                        <line x1="72" y1="66" x2="85" y2="67" stroke="#d4a373" stroke-width="1.4" stroke-linecap="round"/>
                    </svg>
                </div>
                <span class="avatar-species-subtitle">Rescue Rabbit Companion</span>
            </div>
        `;
    }

    if (s.includes('bird')) {
        return `
            <div class="pet-illustrated-media" style="background: linear-gradient(135deg, #102a43, #243b53);">
                <div class="avatar-svg-container">
                    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M48 20 C42 12 36 10 32 12 C36 16 42 22 46 26 Z" fill="#ffd166"/>
                        <path d="M54 22 C52 10 46 6 40 8 C46 14 50 20 53 26 Z" fill="#f4a261"/>
                        <circle cx="50" cy="48" r="26" fill="#e0e1dd"/>
                        <circle cx="36" cy="52" r="8" fill="#f07167" opacity="0.85"/>
                        <circle cx="43" cy="44" r="4.5" fill="#1b263b"/>
                        <circle cx="44.5" cy="42.5" r="1.5" fill="#fff"/>
                        <polygon points="26,48 16,53 28,58" fill="#a37081"/>
                        <path d="M26 48 Q20 51 16 53 Q22 55 28 58 Z" fill="#b08968"/>
                        <ellipse cx="68" cy="62" rx="14" ry="20" fill="#778da9" transform="rotate(-15 68 62)"/>
                        <ellipse cx="72" cy="65" rx="9" ry="14" fill="#ffd166" opacity="0.75" transform="rotate(-15 72 65)"/>
                    </svg>
                </div>
                <span class="avatar-species-subtitle">Rescue Aviary Companion</span>
            </div>
        `;
    }

    if (s.includes('pocket') || s.includes('small')) {
        return `
            <div class="pet-illustrated-media" style="background: linear-gradient(135deg, #3d2618, #58311a);">
                <div class="avatar-svg-container">
                    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <circle cx="32" cy="38" r="10" fill="#ddb892"/>
                        <circle cx="32" cy="38" r="6" fill="#e76f51" opacity="0.6"/>
                        <circle cx="68" cy="38" r="10" fill="#ddb892"/>
                        <circle cx="68" cy="38" r="6" fill="#e76f51" opacity="0.6"/>
                        <ellipse cx="50" cy="60" rx="30" ry="26" fill="#ede0d4"/>
                        <ellipse cx="38" cy="56" rx="16" ry="18" fill="#b08968"/>
                        <circle cx="37" cy="52" r="3.5" fill="#2b2d42"/>
                        <circle cx="38" cy="51" r="1.2" fill="#fff"/>
                        <circle cx="63" cy="52" r="3.5" fill="#2b2d42"/>
                        <circle cx="64" cy="51" r="1.2" fill="#fff"/>
                        <ellipse cx="50" cy="63" rx="7" ry="5" fill="#faedcd"/>
                        <polygon points="50,62 47,60 53,60" fill="#e76f51"/>
                        <path d="M50 63 Q50 66 47 67 M50 63 Q50 66 53 67" stroke="#7f4f24" stroke-width="1.6" stroke-linecap="round" fill="none"/>
                        <line x1="26" y1="62" x2="14" y2="61" stroke="#b08968" stroke-width="1.3" stroke-linecap="round"/>
                        <line x1="26" y1="65" x2="12" y2="67" stroke="#b08968" stroke-width="1.3" stroke-linecap="round"/>
                        <line x1="74" y1="62" x2="86" y2="61" stroke="#b08968" stroke-width="1.3" stroke-linecap="round"/>
                        <line x1="74" y1="65" x2="88" y2="67" stroke="#b08968" stroke-width="1.3" stroke-linecap="round"/>
                    </svg>
                </div>
                <span class="avatar-species-subtitle">Pocket Pet Companion</span>
            </div>
        `;
    }

    if (s.includes('reptile')) {
        return `
            <div class="pet-illustrated-media" style="background: linear-gradient(135deg, #1e3a2f, #2d5a47);">
                <div class="avatar-svg-container">
                    <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M28 50 C28 35 42 32 60 38 C72 42 78 52 74 62 C70 72 45 74 34 68 C29 64 28 57 28 50 Z" fill="#90be6d"/>
                        <circle cx="62" cy="35" r="2.5" fill="#f4a261"/>
                        <circle cx="68" cy="39" r="2.5" fill="#f4a261"/>
                        <circle cx="74" cy="45" r="2.5" fill="#f4a261"/>
                        <circle cx="76" cy="52" r="2.5" fill="#f4a261"/>
                        <circle cx="73" cy="60" r="2.5" fill="#f4a261"/>
                        <circle cx="48" cy="46" r="6.5" fill="#ffd166"/>
                        <ellipse cx="48" cy="46" rx="2" ry="5" fill="#2b2d42"/>
                        <circle cx="49" cy="44" r="1" fill="#fff"/>
                        <path d="M30 56 Q40 62 52 59" stroke="#4d7c0f" stroke-width="2.2" stroke-linecap="round" fill="none"/>
                        <circle cx="32" cy="51" r="1.4" fill="#365314"/>
                    </svg>
                </div>
                <span class="avatar-species-subtitle">Reptile Sanctuary Resident</span>
            </div>
        `;
    }

    return `
        <div class="pet-illustrated-media" style="background: linear-gradient(135deg, #2b2d42, #1b263b);">
            <div class="avatar-svg-container">
                <i class="ph-fill ph-paw-print" style="font-size: 4rem; color: var(--accent-amber);"></i>
            </div>
            <span class="avatar-species-subtitle">${name || 'PET CONNECT Companion'}</span>
        </div>
    `;
}

function getPetPhoto(pet) {
    const breed = (pet.breed || '').toLowerCase();
    const species = (pet.species || '').toLowerCase();

    if (species === 'dog') {
        if (breed.includes('golden') || breed.includes('retriever')) return '/static/images/pets/golden_retriever.jpg';
        if (breed.includes('shepherd') || breed.includes('malinois')) return '/static/images/pets/german_shepherd.jpg';
        if (breed.includes('husky')) return '/static/images/pets/husky.jpg';
        return '/static/images/pets/golden_retriever.jpg';
    }

    if (species === 'cat') {
        if (breed.includes('siamese')) return '/static/images/pets/siamese_cat.jpg';
        if (breed.includes('tabby') || breed.includes('shorthair') || breed.includes('maine')) return '/static/images/pets/tabby_cat.jpg';
        return '/static/images/pets/tabby_cat.jpg';
    }

    if (species === 'rabbit') return '/static/images/pets/rabbit.jpg';
    if (species === 'bird') return '/static/images/pets/bird.jpg';
    if (species.includes('pocket') || species.includes('small')) return '/static/images/pets/small_pet.jpg';
    if (species === 'reptile') return '/static/images/pets/reptile.jpg';

    return null;
}

// Manageability Controls: Update Slider Value Text Pills
function updateManageabilityDisplayLabels() {
    const elEnergy = document.getElementById('slider-cust-energy');
    const elMaint = document.getElementById('slider-cust-maintenance');
    const elYard = document.getElementById('slider-cust-yard');
    const elBudget = document.getElementById('slider-cust-budget');
    const elChild = document.getElementById('slider-cust-child');

    if (elEnergy) {
        const val = parseInt(elEnergy.value) || 5;
        const disp = document.getElementById('display-cust-energy');
        if (disp) {
            if (val <= 3) disp.innerText = 'Calm / Couch (~30m/day)';
            else if (val <= 6) disp.innerText = 'Moderate Walks (~1h/day)';
            else if (val <= 8) disp.innerText = 'Active Partner (~1.5h/day)';
            else disp.innerText = 'Athlete / High Drive (2h+/day)';
        }
    }

    if (elMaint) {
        const val = parseInt(elMaint.value) || 5;
        const disp = document.getElementById('display-cust-maintenance');
        if (disp) {
            if (val <= 3) disp.innerText = 'Low / Quick Brush';
            else if (val <= 6) disp.innerText = 'Moderate Grooming';
            else if (val <= 8) disp.innerText = 'Attentive Regular Care';
            else disp.innerText = 'High Maintenance / Daily';
        }
    }

    if (elYard) {
        const val = parseInt(elYard.value) || 0;
        const disp = document.getElementById('display-cust-yard');
        if (disp) {
            if (val === 0) disp.innerText = 'Apartment (No Yard)';
            else if (val === 1) disp.innerText = 'Townhouse / Small Yard';
            else if (val === 2) disp.innerText = 'House / Medium Yard';
            else disp.innerText = 'Spacious Yard / Acreage';
        }
    }

    if (elBudget) {
        const val = parseInt(elBudget.value) || 5;
        const disp = document.getElementById('display-cust-budget');
        if (disp) {
            if (val <= 3) disp.innerText = 'Budget Friendly (<$35/mo)';
            else if (val <= 6) disp.innerText = 'Moderate (~$65/mo)';
            else if (val <= 8) disp.innerText = 'Generous Care (~$95/mo)';
            else disp.innerText = 'Flexible / Premium ($120+/mo)';
        }
    }

    if (elChild) {
        const val = parseInt(elChild.value);
        const disp = document.getElementById('display-cust-child');
        if (disp) {
            if (val <= 4) disp.innerText = 'Toddler (Under 5y)';
            else if (val <= 10) disp.innerText = `Kids (${val} Years Old)`;
            else disp.innerText = `Teens / Adults (${val}y+)`;
        }
    }
}

function applyManageabilityPreset(presetType, btnEl) {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    const sEnergy = document.getElementById('slider-cust-energy');
    const sMaint = document.getElementById('slider-cust-maintenance');
    const sYard = document.getElementById('slider-cust-yard');
    const sBudget = document.getElementById('slider-cust-budget');
    const sChild = document.getElementById('slider-cust-child');

    if (presetType === 'chill') {
        if (sEnergy) sEnergy.value = 2;
        if (sMaint) sMaint.value = 2;
        if (sYard) sYard.value = 0;
        if (sBudget) sBudget.value = 3;
        if (sChild) sChild.value = 12;
    } else if (presetType === 'active') {
        if (sEnergy) sEnergy.value = 9;
        if (sMaint) sMaint.value = 6;
        if (sYard) sYard.value = 3;
        if (sBudget) sBudget.value = 7;
        if (sChild) sChild.value = 10;
    } else if (presetType === 'apartment') {
        if (sEnergy) sEnergy.value = 4;
        if (sMaint) sMaint.value = 4;
        if (sYard) sYard.value = 0;
        if (sBudget) sBudget.value = 5;
        if (sChild) sChild.value = 10;
    } else if (presetType === 'family') {
        if (sEnergy) sEnergy.value = 5;
        if (sMaint) sMaint.value = 4;
        if (sYard) sYard.value = 2;
        if (sBudget) sBudget.value = 6;
        if (sChild) sChild.value = 3;
    } else if (presetType === 'budget') {
        if (sEnergy) sEnergy.value = 4;
        if (sMaint) sMaint.value = 3;
        if (sYard) sYard.value = 1;
        if (sBudget) sBudget.value = 2;
        if (sChild) sChild.value = 10;
    }

    updateManageabilityDisplayLabels();
    fetchCustomerAnimals();
}

function resetManageabilityControls() {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));

    const sEnergy = document.getElementById('slider-cust-energy');
    const sMaint = document.getElementById('slider-cust-maintenance');
    const sYard = document.getElementById('slider-cust-yard');
    const sBudget = document.getElementById('slider-cust-budget');
    const sChild = document.getElementById('slider-cust-child');

    if (sEnergy) sEnergy.value = 5;
    if (sMaint) sMaint.value = 5;
    if (sYard) sYard.value = 1;
    if (sBudget) sBudget.value = 5;
    if (sChild) sChild.value = 10;

    updateManageabilityDisplayLabels();
    fetchCustomerAnimals();
}

function handleManageabilityChange() {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    updateManageabilityDisplayLabels();

    if (manageabilityDebounceTimer) clearTimeout(manageabilityDebounceTimer);
    manageabilityDebounceTimer = setTimeout(() => {
        fetchCustomerAnimals();
    }, 120);
}

function getManageabilityUserProfile() {
    const elEnergy = document.getElementById('slider-cust-energy');
    const elMaint = document.getElementById('slider-cust-maintenance');
    const elYard = document.getElementById('slider-cust-yard');
    const elBudget = document.getElementById('slider-cust-budget');
    const elChild = document.getElementById('slider-cust-child');

    const energyCap = elEnergy ? parseInt(elEnergy.value) : 5;
    const maintCap = elMaint ? parseInt(elMaint.value) : 5;
    const yardVal = elYard ? parseInt(elYard.value) : 1;
    const budgetVal = elBudget ? parseInt(elBudget.value) : 5;
    const childAge = elChild ? parseInt(elChild.value) : 10;

    const exHours = parseFloat((energyCap * 0.28).toFixed(1));
    const spaceVal = yardVal === 0 ? 3 : (yardVal === 1 ? 5 : (yardVal === 2 ? 7 : 9));

    return {
        energy_capacity: energyCap,
        exercise_time_hours: exHours,
        maintenance_capacity: maintCap,
        grooming_time_available: maintCap,
        space_limit: spaceVal,
        yard_size: yardVal,
        budget_limit: budgetVal,
        setup_budget: budgetVal,
        youngest_child_age: childAge,
        sociability_pref: childAge <= 7 ? 8 : 6
    };
}

async function fetchCustomerAnimals() {
    try {
        const userProfile = getManageabilityUserProfile();
        const speciesParam = (activeFilter === 'all' || activeFilter === 'favorites') ? 'all' : activeFilter;

        const res = await fetch('/api/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_profile: userProfile,
                species_filter: speciesParam,
                limit: 120
            })
        });
        const data = await res.json();
        customerAnimals = data.matches || [];

        const peakEl = document.getElementById('stat-peak-match');
        if (peakEl) {
            peakEl.innerText = `${data.peak_match_score || 98}%`;
        }

        const evalEl = document.getElementById('stat-evaluated-count');
        if (evalEl) {
            evalEl.innerText = (data.total_evaluated || customerAnimals.length).toLocaleString();
        }

        const statTotal = document.getElementById('stat-total-companions');
        if (statTotal && data.total_evaluated > 0) {
            statTotal.innerText = `${data.total_evaluated.toLocaleString()}+`;
        }

        renderCustomerPets();
    } catch (err) {
        console.error('Error fetching manageability matches:', err);
    }
}

function setFilter(category, btnEl) {
    activeFilter = category.toLowerCase().trim();
    document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    if (activeFilter === 'favorites') {
        renderCustomerPets();
    } else {
        fetchCustomerAnimals();
    }
}

function handlePetSearch(val) {
    searchQuery = (val || '').toLowerCase().trim();
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) {
        clearBtn.style.display = searchQuery ? 'flex' : 'none';
    }
    renderCustomerPets();
}

function clearPetSearch() {
    const input = document.getElementById('pet-search-input');
    if (input) input.value = '';
    searchQuery = '';
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) clearBtn.style.display = 'none';
    renderCustomerPets();
}

function resetFilters() {
    activeFilter = 'all';
    searchQuery = '';
    const input = document.getElementById('pet-search-input');
    if (input) input.value = '';
    const clearBtn = document.getElementById('clear-search-btn');
    if (clearBtn) clearBtn.style.display = 'none';

    document.querySelectorAll('.filter-chip').forEach(c => {
        if (c.dataset.filter === 'all') c.classList.add('active');
        else c.classList.remove('active');
    });
    fetchCustomerAnimals();
}

function toggleFav(rfidTag, btnEl) {
    if (favoriteIds.has(rfidTag)) {
        favoriteIds.delete(rfidTag);
        btnEl.classList.remove('active');
        btnEl.innerHTML = '<i class="ph ph-heart"></i>';
    } else {
        favoriteIds.add(rfidTag);
        btnEl.classList.add('active');
        btnEl.innerHTML = '<i class="ph-fill ph-heart"></i>';
    }
    saveFavoritesToStorage();

    if (activeFilter === 'favorites') {
        renderCustomerPets();
    }
}

function formatAgeFriendly(months) {
    const m = parseInt(months) || 12;
    if (m < 12) return `${m} mo${m === 1 ? '' : 's'} old`;
    const yrs = Math.floor(m / 12);
    const remMonths = m % 12;
    if (remMonths === 0) return `${yrs} yr${yrs === 1 ? '' : 's'} old`;
    return `${yrs} yr, ${remMonths} mo${remMonths === 1 ? '' : 's'}`;
}

function getEnergyLabel(level) {
    const l = parseInt(level) || 5;
    if (l <= 3) return 'Gentle & Calm';
    if (l <= 6) return 'Moderate Play';
    return 'Playful & Active';
}

function getMeterFillClass(val) {
    const v = parseFloat(val) || 0;
    if (v >= 85) return 'fill-green';
    if (v >= 70) return 'fill-teal';
    if (v >= 50) return 'fill-amber';
    return 'fill-rose';
}

function renderCustomerPets() {
    const grid = document.getElementById('customer-pets-grid');
    const emptyState = document.getElementById('empty-state');
    const countLabel = document.getElementById('results-count-label');
    if (!grid) return;

    const filtered = customerAnimals.filter(pet => {
        const petSpecies = (pet.species || '').toLowerCase().trim();
        const petName = (pet.name || '').toLowerCase();
        const petBreed = (pet.breed || '').toLowerCase();
        const petBio = (pet.bio || '').toLowerCase();

        if (activeFilter === 'favorites' && !favoriteIds.has(pet.rfid_tag)) return false;

        if (searchQuery) {
            const matches = petName.includes(searchQuery) ||
                            petBreed.includes(searchQuery) ||
                            petSpecies.includes(searchQuery) ||
                            petBio.includes(searchQuery);
            if (!matches) return false;
        }

        return true;
    });

    if (countLabel) {
        countLabel.innerText = `Showing ${filtered.length} matched companion${filtered.length === 1 ? '' : 's'}`;
    }

    if (filtered.length === 0) {
        grid.innerHTML = '';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    grid.innerHTML = '';

    filtered.slice(0, 48).forEach((pet, idx) => {
        const isFav = favoriteIds.has(pet.rfid_tag);
        const cfg = getSpeciesConfig(pet.species);
        const card = document.createElement('div');
        card.className = 'customer-pet-card';
        card.style.animationDelay = `${Math.min(idx * 0.03, 0.35)}s`;

        const photoUrl = getPetPhoto(pet);
        const adoptionFee = pet.adoption_fee || cfg.defaultFee;
        const staffBio = pet.bio || `A wonderful and gentle ${pet.species.toLowerCase()} companion awaiting a loving family.`;
        const ageText = formatAgeFriendly(pet.age_months);
        const energyLabel = getEnergyLabel(pet.energy_level);
        const cleanName = pet.name.replace(/\s*\(ANM-[0-9]+\)/, '');

        const analysis = pet.match_analysis || {};
        const score = analysis.compatibility_score || 90;
        const metrics = analysis.metrics_breakdown || {};
        const energyScore = Math.round(metrics.energy_match !== undefined ? metrics.energy_match : 92);
        const maintScore = Math.round(metrics.maintenance_match !== undefined ? metrics.maintenance_match : 90);
        const spaceScore = Math.round(metrics.space_match !== undefined ? metrics.space_match : 95);
        const budgetScore = Math.round(metrics.budget_match !== undefined ? metrics.budget_match : 90);

        const primaryReason = analysis.primary_explanation || `${cleanName} matches your manageable routine and home environment.`;

        let pillClass = 'match-pill-excellent';
        if (score < 60) pillClass = 'match-pill-caution';
        else if (score < 75) pillClass = 'match-pill-moderate';
        else if (score < 90) pillClass = 'match-pill-great';

        let mediaHtml = '';
        if (photoUrl) {
            mediaHtml = `
                <img src="${photoUrl}" alt="${cleanName}" class="pet-img" loading="lazy" onerror="this.onerror=null; this.parentElement.innerHTML='${getSpeciesSVGIllustration(pet.species, cleanName).replace(/"/g, '&quot;')}'" />
            `;
        } else {
            mediaHtml = getSpeciesSVGIllustration(pet.species, cleanName);
        }

        card.innerHTML = `
            <div class="pet-card-media">
                <span class="species-tag-badge">
                    <span>${cfg.emoji}</span> ${cfg.label}
                </span>

                <div class="match-score-pill ${pillClass}" title="Overall Personal Manageability & Lifestyle Compatibility">
                    <i class="ph-fill ph-sparkle"></i> ${score}% Match
                </div>

                <span class="adoption-fee-badge">
                    $${adoptionFee} Fee
                </span>

                <button class="pet-fav-btn ${isFav ? 'active' : ''}" 
                        onclick="toggleFav('${pet.rfid_tag}', this)" 
                        title="${isFav ? 'Remove from Saved' : 'Save to Favorites'}" 
                        aria-label="Bookmark companion">
                    <i class="${isFav ? 'ph-fill' : 'ph'} ph-heart"></i>
                </button>

                ${mediaHtml}
            </div>

            <div class="pet-card-body">
                <div class="pet-header-row">
                    <h3 class="pet-name-title">${cleanName}</h3>
                </div>
                <div class="pet-subtitle">${pet.breed} • ${ageText} • ${pet.size || 'Medium'}</div>

                <div class="pet-match-reason">
                    <i class="ph-fill ph-heart-straight"></i>
                    <span>${primaryReason}</span>
                </div>

                <div class="manageability-meter-grid">
                    <div class="mini-meter-row">
                        <div class="mini-meter-header">
                            <span class="mini-meter-label"><i class="ph-fill ph-lightning"></i> Energy Match</span>
                            <span class="mini-meter-val">${energyScore}%</span>
                        </div>
                        <div class="mini-meter-bar">
                            <div class="mini-meter-fill ${getMeterFillClass(energyScore)}" style="width: ${energyScore}%"></div>
                        </div>
                    </div>

                    <div class="mini-meter-row">
                        <div class="mini-meter-header">
                            <span class="mini-meter-label"><i class="ph-fill ph-scissors"></i> Maintenance Match</span>
                            <span class="mini-meter-val">${maintScore}%</span>
                        </div>
                        <div class="mini-meter-bar">
                            <div class="mini-meter-fill ${getMeterFillClass(maintScore)}" style="width: ${maintScore}%"></div>
                        </div>
                    </div>

                    <div class="mini-meter-row">
                        <div class="mini-meter-header">
                            <span class="mini-meter-label"><i class="ph-fill ph-house-line"></i> Space Match</span>
                            <span class="mini-meter-val">${spaceScore}%</span>
                        </div>
                        <div class="mini-meter-bar">
                            <div class="mini-meter-fill ${getMeterFillClass(spaceScore)}" style="width: ${spaceScore}%"></div>
                        </div>
                    </div>

                    <div class="mini-meter-row">
                        <div class="mini-meter-header">
                            <span class="mini-meter-label"><i class="ph-fill ph-wallet"></i> Budget Match</span>
                            <span class="mini-meter-val">${budgetScore}%</span>
                        </div>
                        <div class="mini-meter-bar">
                            <div class="mini-meter-fill ${getMeterFillClass(budgetScore)}" style="width: ${budgetScore}%"></div>
                        </div>
                    </div>
                </div>

                <div class="pet-staff-quote">
                    <i class="ph-fill ph-quotes quote-mark"></i>
                    <span>${staffBio}</span>
                </div>

                <div class="pet-traits-grid">
                    <span class="trait-pill">
                        <i class="ph-fill ph-lightning"></i> ${energyLabel}
                    </span>
                    <span class="trait-pill">
                        <i class="ph-fill ph-baby"></i> Kids: &ge;${pet.child_friendly_min_age || 0}y
                    </span>
                    ${pet.yard_needed === 0 ? '<span class="trait-pill highlight"><i class="ph-fill ph-house-line"></i> Apt Friendly</span>' : ''}
                </div>

                <button class="btn-adopt-card" onclick="openAdoptionModal('${cleanName.replace(/'/g, "\\'")}', '${pet.rfid_tag}', '${pet.species.replace(/'/g, "\\'")}', '${pet.breed.replace(/'/g, "\\'")}', ${pet.age_months}, ${adoptionFee}, '${(pet.id || '').replace(/'/g, "\\'")}')">
                    <i class="ph-fill ph-paw-print"></i> Meet Me &amp; Apply to Adopt
                </button>
            </div>
        `;
        grid.appendChild(card);
    });
}

// ==========================================================================
// Adoption Modal & Backend Confirmation Email Dispatch
// ==========================================================================
function openAdoptionModal(petName, rfidTag, species, breed, ageMonths, adoptionFee, animalId = '') {
    // Enforce asking for customer email beforehand if not yet provided
    if (!preRegisteredEmail) {
        pendingPetModalArgs = [petName, rfidTag, species, breed, ageMonths, adoptionFee, animalId];
        openEmailOnboardingModal();
        return;
    }

    const modal = document.getElementById('adoption-modal');
    if (!modal) return;

    currentSelectedPet = {
        pet_name: petName,
        rfid_tag: rfidTag,
        species: species,
        breed: breed,
        age_months: ageMonths,
        adoption_fee: adoptionFee,
        animal_id: animalId
    };

    document.getElementById('modal-pet-name').innerText = petName;
    document.getElementById('modal-pet-species').innerText = species;
    document.getElementById('modal-pet-info').innerText = `${breed} • ${formatAgeFriendly(ageMonths)} • Ref: ${rfidTag}`;
    document.getElementById('modal-pet-fee').innerText = `$${adoptionFee}`;

    // Pre-fill adopter email, name, and phone from upfront registration
    syncAdopterEmailUI();

    const errBanner = document.getElementById('adoption-submit-error');
    if (errBanner) errBanner.style.display = 'none';

    const avatarContainer = document.getElementById('modal-pet-avatar');
    const photoUrl = getPetPhoto({ species, breed });
    if (photoUrl) {
        avatarContainer.innerHTML = `<img src="${photoUrl}" alt="${petName}" />`;
    } else {
        const cfg = getSpeciesConfig(species);
        avatarContainer.innerHTML = `<div style="font-size: 2rem; display: flex; align-items: center; justify-content: center; width: 100%; height: 100%;">${cfg.emoji}</div>`;
    }

    document.getElementById('adoption-form-container').style.display = 'block';
    document.getElementById('adoption-confirmation-container').style.display = 'none';

    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeAdoptionModal() {
    const modal = document.getElementById('adoption-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

function handleModalBackdropClick(e) {
    if (e.target.id === 'adoption-modal') {
        closeAdoptionModal();
    }
}

async function submitAdoptionRequest(e) {
    e.preventDefault();
    const name = (document.getElementById('adopter-name').value || '').trim();
    const email = (document.getElementById('adopter-email').value || '').trim();
    const phone = (document.getElementById('adopter-phone').value || '').trim();
    const housing = document.getElementById('adopter-housing').value;
    const otherPets = document.getElementById('adopter-other-pets').value;
    const experience = document.getElementById('adopter-experience').value;
    const note = (document.getElementById('adopter-note').value || '').trim();
    const petName = document.getElementById('modal-pet-name').innerText;

    const errBanner = document.getElementById('adoption-submit-error');
    const submitBtn = document.getElementById('submit-adoption-btn');
    if (errBanner) errBanner.style.display = 'none';
    if (submitBtn) submitBtn.disabled = true;

    const petMeta = currentSelectedPet || {
        pet_name: petName,
        rfid_tag: 'TAG_PETCONNECT',
        species: document.getElementById('modal-pet-species').innerText || 'Dog',
        breed: 'Rescue Companion',
        adoption_fee: 150
    };

    try {
        const res = await fetch('/api/adoption-request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                adopter_name: name,
                adopter_email: email,
                adopter_phone: phone,
                housing_type: housing,
                other_pets: otherPets,
                experience_level: experience,
                personal_note: note,
                pet_name: petMeta.pet_name,
                rfid_tag: petMeta.rfid_tag,
                animal_id: petMeta.animal_id,
                species: petMeta.species,
                breed: petMeta.breed,
                adoption_fee: petMeta.adoption_fee,
                user_profile: getManageabilityUserProfile()
            })
        });

        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'Could not submit adoption request.');
        }

        // Persist updated adopter identity
        saveAdopterIdentityToStorage(email, name, phone);

        const emailInfo = data.confirmation_email || {};
        lastConfirmationRef = emailInfo.reference_id || (data.request && data.request.request_ref) || 'PC-2026';

        document.getElementById('confirm-ref-badge').innerText = `Reference #${lastConfirmationRef}`;
        document.getElementById('confirm-pet-name').innerText = petName;
        document.getElementById('confirm-email-display').innerText = email;

        const fromEl = document.getElementById('confirm-email-from');
        if (fromEl && emailInfo.from) fromEl.innerText = emailInfo.from;

        const subjEl = document.getElementById('confirm-email-subject');
        if (subjEl) subjEl.innerText = emailInfo.subject || `PET CONNECT Confirmation [#${lastConfirmationRef}]`;

        const toEl = document.getElementById('confirm-email-to');
        if (toEl) toEl.innerText = emailInfo.to || email;

        const statusEl = document.getElementById('confirm-delivery-status');
        if (statusEl) {
            if (emailInfo.smtp_delivered) {
                statusEl.innerText = 'Delivered to Inbox ✓';
            } else {
                statusEl.innerText = 'Registered & Queued with Shelter Team ✓';
            }
        }

        const viewLink = document.getElementById('confirm-view-html-link');
        if (viewLink && emailInfo.preview_url) viewLink.href = emailInfo.preview_url;

        const gmailComposeLink = document.getElementById('confirm-gmail-compose-link');
        if (gmailComposeLink) {
            const su = encodeURIComponent(emailInfo.subject || `PET CONNECT Confirmation [#${lastConfirmationRef}]`);
            const bd = encodeURIComponent(emailInfo.body_text || `Your PET CONNECT adoption request #${lastConfirmationRef} for ${petName} has been confirmed.`);
            gmailComposeLink.href = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(email)}&su=${su}&body=${bd}`;
        }

        const dlLink = document.getElementById('confirm-download-html-link');
        if (dlLink && emailInfo.preview_url) dlLink.href = `${emailInfo.preview_url}?download=1`;

        const checklistUl = document.getElementById('confirm-care-checklist');
        if (checklistUl) {
            const items = emailInfo.care_checklist || [];
            checklistUl.innerHTML = items.map(item => `<li>${item}</li>`).join('');
        }

        document.getElementById('adoption-form-container').style.display = 'none';
        document.getElementById('adoption-confirmation-container').style.display = 'block';
    } catch (err) {
        if (errBanner) {
            errBanner.innerText = err.message || 'An error occurred while sending your request.';
            errBanner.style.display = 'block';
        }
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

async function resendConfirmationEmail(useInlineSmtp = false) {
    if (!lastConfirmationRef) return;
    const btn = document.getElementById('btn-resend-email');
    const statusEl = document.getElementById('confirm-delivery-status');
    const feedbackEl = document.getElementById('smtp-inline-feedback');
    if (btn) btn.disabled = true;
    if (feedbackEl) feedbackEl.style.display = 'none';

    const payload = { email: preRegisteredEmail };
    if (useInlineSmtp) {
        const smtpUser = (document.getElementById('inline-smtp-user')?.value || '').trim();
        const smtpPass = (document.getElementById('inline-smtp-pass')?.value || '').trim();
        payload.smtp_user = smtpUser;
        payload.smtp_password = smtpPass;
    }

    try {
        const res = await fetch(`/api/adoption-request/${lastConfirmationRef}/resend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            if (data.smtp_delivered) {
                if (statusEl) statusEl.innerText = `Delivered to ${data.to} via Gmail SMTP ✓`;
                if (feedbackEl) {
                    feedbackEl.style.display = 'block';
                    feedbackEl.style.color = '#74c69d';
                    feedbackEl.innerText = `✓ Successfully delivered via smtp.gmail.com:587 to ${data.to}! Check your Gmail inbox.`;
                }
            } else {
                if (statusEl) statusEl.innerText = `Saved Locally (${data.delivery_status})`;
                if (feedbackEl) {
                    feedbackEl.style.display = 'block';
                    feedbackEl.style.color = '#f4a261';
                    feedbackEl.innerText = data.smtp_error
                        ? `SMTP Error: ${data.smtp_error}`
                        : 'Saved locally. Provide a valid Gmail address & 16-char Google App Password to send over Gmail SMTP.';
                }
            }
        }
    } catch (err) {
        console.error('Error resending confirmation email:', err);
    } finally {
        if (btn) btn.disabled = false;
    }
}
