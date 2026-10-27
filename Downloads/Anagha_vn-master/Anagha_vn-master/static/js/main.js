/* ==========================================================================
   PET CONNECT Animal Rescue & Sanctuary — Staff Operations Hub Logic
   Animal Care Directory, Lifestyle Matcher, Foster Queue, Triage & Census
   ========================================================================== */

let allAnimals = [];
let currentScannedTag = null;
let directorySpeciesFilter = 'all';
let currentTriageFilter = 'all';
let cachedSpecializedData = null;
let allAdoptionRequests = [];
let selectedStaffRequestRef = null;

document.addEventListener('DOMContentLoaded', () => {
    initNavHighlight();
    fetchStats();
    fetchAllAnimals();
    fetchLatestScan();
    fetchAdoptionRequests();
    
    // Periodically sync stats, latest inspected profile, and incoming customer adoption requests
    setInterval(fetchLatestScan, 4000);
    setInterval(fetchAdoptionRequests, 5000);

    // Support ?tab=adoption-requests deep link from customer portal
    const params = new URLSearchParams(window.location.search);
    const requestedTab = params.get('tab');
    if (requestedTab) {
        setTimeout(() => switchTab(requestedTab), 120);
    }

    // Adjust nav highlight on window resize
    window.addEventListener('resize', () => {
        const activeBtn = document.querySelector('.nav-tab-btn.active');
        if (activeBtn) updateNavHighlight(activeBtn);
    });
});

// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `apple-toast toast-${type}`;
    
    const iconClass = type === 'success' ? 'ph-check-circle' : type === 'error' ? 'ph-x-circle' : 'ph-info';
    toast.innerHTML = `<i class="ph-fill ${iconClass}"></i> <span>${message}</span>`;
    
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// Sliding Pill Navigation Highlight Logic
function initNavHighlight() {
    const activeBtn = document.querySelector('.nav-tab-btn.active');
    if (activeBtn) updateNavHighlight(activeBtn);
}

function updateNavHighlight(targetBtn) {
    const highlight = document.getElementById('nav-pill-highlight');
    if (!highlight) return;
    
    const activeBtn = targetBtn || document.querySelector('.nav-tab-btn.active');
    if (!activeBtn) return;

    const container = document.getElementById('main-nav-segmented');
    const containerRect = container.getBoundingClientRect();
    const btnRect = activeBtn.getBoundingClientRect();

    highlight.style.width = `${btnRect.width}px`;
    highlight.style.transform = `translateX(${btnRect.left - containerRect.left - 4}px)`;
}

// Tab Switching Handler
function switchTab(tabId, btnElement) {
    document.querySelectorAll('.nav-tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(pane => pane.classList.remove('active'));
    
    if (btnElement) {
        btnElement.classList.add('active');
        updateNavHighlight(btnElement);
    } else {
        const targetBtn = Array.from(document.querySelectorAll('.nav-tab-btn'))
            .find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabId));
        if (targetBtn) {
            targetBtn.classList.add('active');
            updateNavHighlight(targetBtn);
        }
    }
    
    const targetPane = document.getElementById(`tab-${tabId}`);
    if (targetPane) targetPane.classList.add('active');

    if (tabId === 'lifestyle-matcher') {
        runVectorMatch();
    } else if (tabId === 'adoption-requests') {
        fetchAdoptionRequests();
    } else if (tabId === 'specialized-triage') {
        renderSpecializedTriage();
    } else if (tabId === 'census-analytics') {
        fetchStats();
        fetchAdoptionRequests();
    }
}

// Count-Up Number Easing Animation
function animateValue(elementId, targetVal, isPercentage = false, duration = 1000) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const startVal = 0;
    let startTimestamp = null;

    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const easeOutQuint = 1 - Math.pow(1 - progress, 5);
        const currentVal = Math.floor(easeOutQuint * (targetVal - startVal) + startVal);
        
        el.innerText = isPercentage ? `${currentVal}%` : (elementId === 'kpi-avg-los' ? `${currentVal}d` : currentVal.toLocaleString());
        if (progress < 1) window.requestAnimationFrame(step);
    };

    window.requestAnimationFrame(step);
}

// Fetch Global KPIs and Census Stats
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        animateValue('kpi-total-animals', data.total_animals || 0);
        animateValue('kpi-high-risk', data.high_risk_percentage || 0, true);
        animateValue('kpi-sar-count', data.specialized_triage_count || data.sar_candidates_count || 0);
        animateValue('kpi-avg-los', data.average_length_of_stay_days || 0);

        renderCensusAnalytics(data);
    } catch (err) {
        console.error('Error fetching shelter stats:', err);
    }
}

// Render Tab 5 Census & Care Operations Analytics
function renderCensusAnalytics(stats) {
    const speciesContainer = document.getElementById('census-species-bars');
    const medicalContainer = document.getElementById('census-medical-bars');
    const totalAnimals = stats.total_animals || 1;

    // 1. Species Breakdown Bars
    if (speciesContainer && stats.species_census) {
        const speciesColors = {
            'Dog': { icon: '🐕', colorClass: 'fill-blue' },
            'Cat': { icon: '🐈', colorClass: 'fill-purple' },
            'Rabbit': { icon: '🐇', colorClass: 'fill-green' },
            'Bird': { icon: '🦜', colorClass: 'fill-teal' },
            'Pocket Pet': { icon: '🐹', colorClass: 'fill-orange' },
            'Small Pet': { icon: '🐹', colorClass: 'fill-orange' },
            'Reptile': { icon: '🦎', colorClass: 'fill-pink' }
        };

        speciesContainer.innerHTML = '';
        const sortedSpecies = Object.entries(stats.species_census).sort((a, b) => b[1] - a[1]);

        sortedSpecies.forEach(([species, count]) => {
            const pct = Math.round((count / totalAnimals) * 100);
            const cfg = speciesColors[species] || { icon: '🐾', colorClass: 'fill-blue' };

            const item = document.createElement('div');
            item.className = 'census-bar-item';
            item.innerHTML = `
                <div class="census-bar-header">
                    <span>${cfg.icon} <strong>${species}s</strong></span>
                    <span>${count.toLocaleString()} in care (${pct}%)</span>
                </div>
                <div class="census-bar-track">
                    <div class="census-bar-fill ${cfg.colorClass}" style="width: ${pct}%;"></div>
                </div>
            `;
            speciesContainer.appendChild(item);
        });
    }

    // 2. Medical Care Status Breakdown
    if (medicalContainer && stats.medical_breakdown) {
        const med = stats.medical_breakdown;
        const routinePct = Math.round(((med.routine || 0) / totalAnimals) * 100);
        const minorPct = Math.round(((med.minor || 0) / totalAnimals) * 100);
        const specPct = Math.round(((med.specialized || 0) / totalAnimals) * 100);

        medicalContainer.innerHTML = `
            <div class="census-bar-item">
                <div class="census-bar-header">
                    <span><i class="ph ph-heartbeat" style="color: var(--apple-green);"></i> Routine Preventive Care</span>
                    <span>${(med.routine || 0).toLocaleString()} animals (${routinePct}%)</span>
                </div>
                <div class="census-bar-track">
                    <div class="census-bar-fill fill-green" style="width: ${routinePct}%;"></div>
                </div>
            </div>

            <div class="census-bar-item">
                <div class="census-bar-header">
                    <span><i class="ph ph-first-aid" style="color: var(--apple-orange);"></i> Minor Medical Management</span>
                    <span>${(med.minor || 0).toLocaleString()} animals (${minorPct}%)</span>
                </div>
                <div class="census-bar-track">
                    <div class="census-bar-fill fill-orange" style="width: ${minorPct}%;"></div>
                </div>
            </div>

            <div class="census-bar-item">
                <div class="census-bar-header">
                    <span><i class="ph ph-bandaids" style="color: var(--apple-pink);"></i> Specialized Veterinary Care</span>
                    <span>${(med.specialized || 0).toLocaleString()} animals (${specPct}%)</span>
                </div>
                <div class="census-bar-track">
                    <div class="census-bar-fill fill-pink" style="width: ${specPct}%;"></div>
                </div>
            </div>
        `;
    }
}

// Fetch All Shelter Animals
async function fetchAllAnimals() {
    try {
        const res = await fetch('/api/animals');
        allAnimals = await res.json();
        
        populateRfidDropdown();
        renderFosterQueue();
        renderSpecializedTriage();
    } catch (err) {
        console.error('Error fetching animals list:', err);
    }
}

// Filter Directory by Species
function filterDirectorySpecies(species, btnEl) {
    directorySpeciesFilter = species.toLowerCase().trim();
    document.querySelectorAll('.dir-species-chip').forEach(c => c.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    populateRfidDropdown();
}

// Populate Dropdown for Tab 1
function populateRfidDropdown() {
    const select = document.getElementById('rfid-tag-select');
    if (!select) return;

    let filtered = allAnimals;
    if (directorySpeciesFilter !== 'all') {
        filtered = allAnimals.filter(a => {
            const s = (a.species || '').toLowerCase().trim();
            if (directorySpeciesFilter === 'pocket pet') return s.includes('pocket') || s.includes('small');
            return s === directorySpeciesFilter;
        });
    }

    select.innerHTML = '';
    filtered.slice(0, 150).forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.rfid_tag;
        const cleanName = a.name.replace(/\s*\(ANM-[0-9]+\)/, '');
        opt.innerText = `${cleanName} (${a.breed}, ${a.species}) — Ref: ${a.rfid_tag}`;
        select.appendChild(opt);
    });
}

// Poll Active Selected Animal Profile
async function fetchLatestScan() {
    try {
        const res = await fetch('/api/latest-scan');
        const data = await res.json();
        
        const serialMode = document.getElementById('rfid-serial-mode');
        if (serialMode) {
            serialMode.innerText = 'Shelter DB Connected';
            serialMode.className = 'badge badge-lowrisk';
        }
        
        if (data.scanned_tag && data.animal) {
            renderScannedProfile(data.animal);
            updateSerialLog(data.scanned_tag, data.animal);
        }
    } catch (err) {
        console.error('Error polling active record:', err);
    }
}

// Render Active Animal Care Sheet on Tab 1
function renderScannedProfile(animal) {
    const container = document.getElementById('scan-profile-content');
    const badge = document.getElementById('scan-risk-badge');
    if (!container) return;
    
    const pred = animal.los_prediction || {};
    const sar = animal.sar_evaluation || {};
    const cleanName = animal.name.replace(/\s*\(ANM-[0-9]+\)/, '');
    const fee = animal.adoption_fee || (animal.species === 'Dog' ? 150 : (animal.species === 'Cat' ? 75 : 40));
    const bio = animal.bio || 'Gentle companion awaiting a loving forever home.';

    if (badge) {
        if (sar.is_sar_candidate) {
            badge.innerText = '🛡️ Specialized Placement Candidate';
            badge.className = 'badge badge-sar';
        } else if (pred.is_high_risk || (animal.length_of_stay_days >= 30)) {
            badge.innerText = '🧡 Foster Care Placement Alert (&ge;30d)';
            badge.className = 'badge badge-highrisk';
        } else {
            badge.innerText = '✅ Routine Care • Ready for Adoption';
            badge.className = 'badge badge-lowrisk';
        }
    }

    const speciesIcons = {
        'Dog': '🐕', 'Cat': '🐈', 'Rabbit': '🐇', 'Bird': '🦜', 'Pocket Pet': '🐹', 'Small Pet': '🐹', 'Reptile': '🦎'
    };
    const sIcon = speciesIcons[animal.species] || '🐾';

    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
            <div>
                <div style="font-size: 0.78rem; font-weight: 700; color: var(--apple-cyan); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">
                    ${sIcon} ${animal.species} Care Profile
                </div>
                <h3 style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.2rem;">${cleanName}</h3>
                <div style="font-size: 0.88rem; color: var(--text-secondary);">${animal.breed} • ${animal.age_months} Months Old • ${animal.size || 'Medium'} Size</div>
                <div style="font-size: 0.8rem; color: var(--apple-blue); margin-top: 0.35rem;">
                    Microchip / Shelter ID: <code>${animal.rfid_tag}</code>
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--apple-cyan);">${animal.length_of_stay_days}d</div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">Duration in Care</div>
                <div style="font-size: 0.82rem; font-weight: 700; color: var(--apple-orange); margin-top: 0.2rem;">$${fee} Adoption Fee</div>
            </div>
        </div>

        <!-- Care Gauges -->
        <div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.25rem;">
            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.3rem;">
                    <span><i class="ph ph-lightning"></i> Energy Level</span>
                    <strong style="color: var(--apple-cyan);">${animal.energy_level} / 10</strong>
                </div>
                <div style="background: rgba(255,255,255,0.08); height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="width: ${animal.energy_level * 10}%; height: 100%; background: linear-gradient(90deg, var(--apple-blue), var(--apple-cyan)); border-radius: 3px;"></div>
                </div>
            </div>

            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.3rem;">
                    <span><i class="ph ph-brain"></i> Trainability / Adaptation</span>
                    <strong style="color: var(--apple-green);">${animal.trainability} / 10</strong>
                </div>
                <div style="background: rgba(255,255,255,0.08); height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="width: ${animal.trainability * 10}%; height: 100%; background: linear-gradient(90deg, var(--apple-green), #60efff); border-radius: 3px;"></div>
                </div>
            </div>

            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.3rem;">
                    <span><i class="ph ph-heart"></i> Sociability</span>
                    <strong style="color: var(--apple-purple);">${animal.sociability || 5} / 10</strong>
                </div>
                <div style="background: rgba(255,255,255,0.08); height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="width: ${(animal.sociability || 5) * 10}%; height: 100%; background: linear-gradient(90deg, var(--apple-purple), var(--apple-pink)); border-radius: 3px;"></div>
                </div>
            </div>
        </div>

        <div class="trait-chips" style="margin-bottom: 1.25rem;">
            <span class="trait-chip"><i class="ph ph-palette"></i> ${animal.coat_color || 'Standard'}</span>
            <span class="trait-chip"><i class="ph ph-ruler"></i> Size: ${animal.size || 'Medium'}</span>
            <span class="trait-chip"><i class="ph ph-baby"></i> Child Friendly: &ge;${animal.child_friendly_min_age || 0}y</span>
            ${animal.yard_needed === 0 ? '<span class="trait-chip" style="border-color: rgba(48,209,88,0.3); color: #74c69d;"><i class="ph ph-house"></i> Apt Friendly</span>' : ''}
        </div>

        <!-- Staff Care Notes / Bio -->
        <div style="background: rgba(255, 255, 255, 0.03); border-left: 3px solid var(--apple-orange); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; padding: 0.85rem; margin-bottom: 1.25rem; font-size: 0.84rem; color: #cbd5e1; font-style: italic; line-height: 1.55;">
            "${bio}"
        </div>

        <!-- Care Recommendation -->
        <div style="background: rgba(10, 132, 255, 0.08); border: 1px solid rgba(10, 132, 255, 0.25); border-radius: var(--radius-md); padding: 1rem;">
            <div style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.35rem; display: flex; align-items: center; gap: 0.5rem;">
                <i class="ph ph-first-aid" style="color: var(--apple-cyan);"></i> Shelter Care Action Plan:
            </div>
            <div style="font-size: 0.82rem; color: var(--text-secondary); line-height: 1.5;">
                ${sar.is_sar_candidate ? 
                    '<strong style="color: var(--apple-cyan);">Specialized Triage:</strong> Candidate identified for Working K9 & SAR deployment or high-drive handler pairing.' : 
                    (pred.is_high_risk || animal.length_of_stay_days >= 30 ? 
                    '<strong style="color: var(--apple-orange);">Foster Priority:</strong> Animal in care &ge; 30 days. Priority foster placement request and featured social media spotlight queued.' : 
                    '<strong style="color: var(--apple-green);">Standard Adoption:</strong> Animal is healthy, socially acclimated, and active on public adoption portal.')
                }
            </div>
        </div>
    `;
}

// Format Humane Care Log Stream
function updateSerialLog(tagId, animal) {
    const log = document.getElementById('serial-terminal-log');
    if (!log) return;
    const timeStr = new Date().toLocaleTimeString();
    const cleanName = animal.name.replace(/\s*\(ANM-[0-9]+\)/, '');
    
    log.innerHTML = `[${timeStr}] <span class="log-key">RECORD_ACCESSED</span>: ${cleanName} (${animal.breed})
[${timeStr}] <span class="log-key">TAG</span>: ${tagId} • <span class="log-key">SPECIES</span>: ${animal.species}
[${timeStr}] <span class="log-key">CARE_STATUS</span>: ${animal.length_of_stay_days >= 30 ? 'FOSTER_QUEUE' : 'ACTIVE_ADOPTION'} • <span class="log-string">OK_200</span>`;
}

// Trigger Scan Handlers
async function triggerScanFromSelect() {
    const tagId = document.getElementById('rfid-tag-select').value;
    if (!tagId) return;
    
    await fetch('/api/scan-rfid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tag_id: tagId })
    });
    fetchLatestScan();
    showToast(`Loaded companion care record for ${tagId}`, 'info');
}

async function triggerRandomScan() {
    await fetch('/api/scan-rfid', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    fetchLatestScan();
    showToast('Loaded random companion profile', 'info');
}

// Register New Intake
function toggleRegisterForm() {
    const form = document.getElementById('register-animal-form');
    if (!form) return;
    const isHidden = form.style.display === 'none';
    form.style.display = isHidden ? 'block' : 'none';
    if (isHidden) {
        showToast('Fill in companion intake details below', 'info');
    }
}

async function submitNewAnimal() {
    const name = document.getElementById('reg-name').value;
    const species = document.getElementById('reg-species').value;
    const breed = document.getElementById('reg-breed').value;
    const age = parseInt(document.getElementById('reg-age').value) || 18;
    const size = document.getElementById('reg-size').value || 'Medium';
    const fee = parseInt(document.getElementById('reg-fee').value) || 65;
    const energy = parseInt(document.getElementById('reg-energy').value) || 5;
    const trainability = parseInt(document.getElementById('reg-trainability').value) || 6;
    const drive = parseInt(document.getElementById('reg-drive').value) || 7;
    const bio = document.getElementById('reg-bio').value || 'Gentle rescue companion awaiting a loving forever home.';

    if (!name) {
        showToast('Please enter an animal name.', 'error');
        return;
    }

    try {
        const res = await fetch('/api/animals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name, species, breed, age_months: age,
                size, adoption_fee: fee, energy_level: energy,
                trainability, drive_level: drive, bio
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Companion ${name} admitted! Ref: ${data.animal.rfid_tag}`, 'success');
            toggleRegisterForm();
            fetchAllAnimals();
            fetchStats();
        }
    } catch (err) {
        console.error('Error admitting animal:', err);
        showToast('Error registering new intake.', 'error');
    }
}

// Slider Values & Vector Matching
function updateSliderVals() {
    const spaceEl = document.getElementById('slider-space');
    const yardEl = document.getElementById('slider-yard');
    const budgetEl = document.getElementById('slider-budget');
    const exerciseEl = document.getElementById('slider-exercise');
    const childAgeEl = document.getElementById('slider-child-age');
    const groomingEl = document.getElementById('slider-grooming');

    const yardLabels = ['Apartment / No Yard', 'Small Patio/Yard', 'Medium Fenced Yard', 'Acreage / Farm'];

    if (spaceEl) document.getElementById('val-space').innerText = `${spaceEl.value} / 10`;
    if (yardEl) document.getElementById('val-yard').innerText = yardLabels[parseInt(yardEl.value)] || 'Small Yard';
    if (budgetEl) document.getElementById('val-budget').innerText = `${budgetEl.value} / 10`;
    if (exerciseEl) document.getElementById('val-exercise').innerText = `${exerciseEl.value} Hours/Day`;
    if (childAgeEl) document.getElementById('val-child-age').innerText = `${childAgeEl.value} Years Old`;
    if (groomingEl) document.getElementById('val-grooming').innerText = `${groomingEl.value} / 10`;
}

function resetMatchingSliders() {
    if (document.getElementById('slider-space')) document.getElementById('slider-space').value = 5;
    if (document.getElementById('slider-yard')) document.getElementById('slider-yard').value = 1;
    if (document.getElementById('slider-budget')) document.getElementById('slider-budget').value = 5;
    if (document.getElementById('slider-exercise')) document.getElementById('slider-exercise').value = 1.5;
    if (document.getElementById('slider-child-age')) document.getElementById('slider-child-age').value = 10;
    if (document.getElementById('slider-grooming')) document.getElementById('slider-grooming').value = 5;
    if (document.getElementById('matcher-species-select')) document.getElementById('matcher-species-select').value = 'all';
    updateSliderVals();
    runVectorMatch();
    showToast('Adopter lifestyle filters reset', 'info');
}

async function runVectorMatch() {
    const speciesFilter = document.getElementById('matcher-species-select') ? document.getElementById('matcher-species-select').value : 'all';
    const exHours = parseFloat(document.getElementById('slider-exercise').value || 1.5);
    const energyCap = Math.min(10, Math.max(1, Math.round(exHours * 2.5)));
    const maintCap = parseInt(document.getElementById('slider-grooming').value || 5);

    const userProfile = {
        energy_capacity: energyCap,
        exercise_time_hours: exHours,
        maintenance_capacity: maintCap,
        grooming_time_available: maintCap,
        space_limit: parseInt(document.getElementById('slider-space').value || 5),
        yard_size: parseInt(document.getElementById('slider-yard').value || 1),
        budget_limit: parseInt(document.getElementById('slider-budget').value || 5),
        setup_budget: parseInt(document.getElementById('slider-budget').value || 5),
        youngest_child_age: parseInt(document.getElementById('slider-child-age').value || 10)
    };
    
    try {
        const res = await fetch('/api/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_profile: userProfile, species_filter: speciesFilter })
        });
        const data = await res.json();
        
        const countEl = document.getElementById('match-count-text');
        if (countEl) countEl.innerText = `${data.total_evaluated} Evaluated (Peak: ${data.peak_match_score || 0}%)`;
        renderMatchCards(data.matches);
    } catch (err) {
        console.error('Error running lifestyle match:', err);
    }
}

// SVG Radial Progress Ring Generator
function createRadialRingSVG(score) {
    const radius = 24;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;

    return `
        <div class="match-ring-wrapper">
            <svg class="match-ring-svg" viewBox="0 0 58 58">
                <circle class="match-ring-bg" cx="29" cy="29" r="${radius}" />
                <circle class="match-ring-progress" cx="29" cy="29" r="${radius}" 
                    stroke-dasharray="${circumference}" 
                    stroke-dashoffset="${offset}" />
            </svg>
            <div class="match-ring-text">${score}%</div>
        </div>
    `;
}

function renderMatchCards(matches) {
    const list = document.getElementById('matching-results-list');
    if (!list) return;
    
    list.innerHTML = '';
    const speciesIcons = {
        'Dog': '🐕', 'Cat': '🐈', 'Rabbit': '🐇', 'Bird': '🦜', 'Pocket Pet': '🐹', 'Small Pet': '🐹', 'Reptile': '🦎'
    };

    matches.slice(0, 10).forEach((m, idx) => {
        const sim = m.match_analysis || {};
        const pred = m.los_prediction || {};
        const metrics = sim.metrics_breakdown || {};
        const score = sim.compatibility_score || 0;
        const cleanName = m.name.replace(/\s*\(ANM-[0-9]+\)/, '');
        const sIcon = speciesIcons[m.species] || '🐾';
        
        const card = document.createElement('div');
        card.className = `animal-card ${pred.is_high_risk ? 'high-risk' : ''}`;
        card.style.animationDelay = `${idx * 0.04}s`;
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--apple-cyan); font-weight: 700; text-transform: uppercase;">
                        ${sIcon} ${m.species}
                    </div>
                    <h4 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary);">${cleanName}</h4>
                    <div style="font-size: 0.82rem; color: var(--text-secondary);">${m.breed} • Child Friendly: &ge;${m.child_friendly_min_age || 0}y</div>
                </div>
                ${createRadialRingSVG(score)}
            </div>
            
            ${sim.primary_explanation ? `
            <div style="font-size: 0.78rem; color: #cbd5e1; margin-top: 0.65rem; padding: 0.4rem 0.6rem; background: rgba(0,0,0,0.25); border-left: 2px solid var(--apple-cyan); border-radius: var(--radius-xs); line-height: 1.4;">
                <i class="ph ph-heart" style="color: var(--apple-cyan); margin-right: 0.25rem;"></i> ${sim.primary_explanation}
            </div>` : ''}

            <div class="trait-chips" style="margin-top: 0.75rem;">
                <span class="trait-chip" title="Manageable Energy Compatibility"><i class="ph ph-lightning"></i> Energy: ${metrics.energy_match || metrics.exercise_match || 0}%</span>
                <span class="trait-chip" title="Manageable Grooming & Upkeep"><i class="ph ph-scissors"></i> Maint: ${metrics.maintenance_match || metrics.grooming_match || 0}%</span>
                <span class="trait-chip" title="Indoor Space & Yard Fit"><i class="ph ph-house"></i> Space: ${metrics.space_match || 0}%</span>
                <span class="trait-chip" title="Monthly Care Budget Compatibility"><i class="ph ph-wallet"></i> Budget: ${metrics.budget_match || 0}%</span>
                <span class="trait-chip" title="Household Child & Family Safety"><i class="ph ph-users"></i> Family: ${metrics.family_match || metrics.sociability_match || 0}%</span>
            </div>
        `;
        list.appendChild(card);
    });
}

// Render Tab 3 Long-Stay & Foster Care Queue
function renderFosterQueue() {
    const queue = document.getElementById('high-risk-queue');
    const badge = document.getElementById('high-risk-header-badge');
    if (!queue) return;
    
    const longStay = allAnimals.filter(a => (a.los_prediction && a.los_prediction.is_high_risk) || (a.length_of_stay_days >= 30));
    if (badge) badge.innerText = `${longStay.length} Long-Stay Companions`;
    
    queue.innerHTML = '';
    const speciesIcons = {
        'Dog': '🐕', 'Cat': '🐈', 'Rabbit': '🐇', 'Bird': '🦜', 'Pocket Pet': '🐹', 'Small Pet': '🐹', 'Reptile': '🦎'
    };

    longStay.slice(0, 36).forEach((a, idx) => {
        const card = document.createElement('div');
        card.className = 'animal-card high-risk';
        card.style.animationDelay = `${Math.min(idx * 0.04, 0.4)}s`;
        const cleanName = a.name.replace(/\s*\(ANM-[0-9]+\)/, '');
        const sIcon = speciesIcons[a.species] || '🐾';
        
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--apple-orange); font-weight: 700; text-transform: uppercase;">
                        ${sIcon} ${a.species}
                    </div>
                    <h4 style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">${cleanName}</h4>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">${a.breed} • ${a.age_months} Months Old</div>
                </div>
                <span class="badge badge-highrisk">${a.length_of_stay_days}d in Care</span>
            </div>

            <div style="font-size: 0.82rem; color: #cbd5e1; font-style: italic; margin-bottom: 0.75rem;">
                "${a.bio || 'Gentle companion in search of a loving foster family.'}"
            </div>

            <div style="background: rgba(255, 159, 10, 0.1); border: 1px solid rgba(255, 159, 10, 0.25); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.8rem; color: var(--apple-orange); display: flex; justify-content: space-between; align-items: center;">
                <span><i class="ph ph-heart-straight"></i> Foster Placement Host Needed</span>
                <button onclick="dispatchFosterRequest('${cleanName}')" style="background: var(--apple-orange); color: #000; border: none; font-size: 0.75rem; font-weight: 700; padding: 0.25rem 0.6rem; border-radius: var(--radius-pill); cursor: pointer;">
                    Dispatch
                </button>
            </div>
        `;
        queue.appendChild(card);
    });
}

function dispatchFosterRequest(petName) {
    showToast(`Foster placement outreach sent for ${petName}!`, 'success');
}

// Specialized Animal Triage Handling (Tab 4)
function switchTriageFilter(cat, btnEl) {
    currentTriageFilter = cat;
    document.querySelectorAll('.triage-tab-btn').forEach(b => b.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');
    renderSpecializedTriage();
}

async function renderSpecializedTriage() {
    const queue = document.getElementById('sar-candidate-queue');
    const badge = document.getElementById('sar-header-badge');
    if (!queue) return;

    if (!cachedSpecializedData) {
        try {
            const res = await fetch('/api/specialized-triage');
            cachedSpecializedData = await res.json();
        } catch (e) {
            console.error('Error fetching specialized triage data:', e);
        }
    }

    let candidates = [];
    if (cachedSpecializedData) {
        if (currentTriageFilter === 'working_dogs') {
            candidates = cachedSpecializedData.working_dogs || [];
        } else if (currentTriageFilter === 'barn_cats') {
            candidates = cachedSpecializedData.barn_cats || [];
        } else if (currentTriageFilter === 'exotic_rescues') {
            candidates = cachedSpecializedData.exotic_rescues || [];
        } else {
            candidates = [
                ...(cachedSpecializedData.working_dogs || []),
                ...(cachedSpecializedData.barn_cats || []),
                ...(cachedSpecializedData.exotic_rescues || [])
            ];
        }
    } else {
        // Fallback filter from allAnimals
        candidates = allAnimals.filter(a => a.is_sar_candidate);
    }

    if (badge) badge.innerText = `${candidates.length} Candidates`;
    queue.innerHTML = '';

    const speciesIcons = {
        'Dog': '🐕', 'Cat': '🐈', 'Rabbit': '🐇', 'Bird': '🦜', 'Pocket Pet': '🐹', 'Small Pet': '🐹', 'Reptile': '🦎'
    };

    candidates.slice(0, 36).forEach((a, idx) => {
        const sar = a.sar_evaluation || {};
        const cleanName = a.name.replace(/\s*\(ANM-[0-9]+\)/, '');
        const card = document.createElement('div');
        card.className = 'animal-card sar-candidate';
        card.style.animationDelay = `${Math.min(idx * 0.04, 0.4)}s`;
        const sIcon = speciesIcons[a.species] || '🐾';
        
        let triageType = 'Working K9 Candidate';
        let actionMsg = 'Routed to Disaster Search & Rescue Unit';
        if (a.species === 'Cat') {
            triageType = 'Barn & Working Cat';
            actionMsg = 'Placed in Working Barn & Natural Pest Control Program';
        } else if (['Rabbit', 'Bird', 'Pocket Pet', 'Small Pet', 'Reptile'].includes(a.species)) {
            triageType = 'Exotic Sanctuary Care';
            actionMsg = 'Assigned to Specialized Species Habitat Care';
        }

        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem;">
                <div>
                    <div style="font-size: 0.75rem; color: var(--apple-cyan); font-weight: 700; text-transform: uppercase;">
                        ${sIcon} ${triageType}
                    </div>
                    <h4 style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary);">${cleanName}</h4>
                    <div style="font-size: 0.82rem; color: var(--text-secondary);">${a.breed} • Ref: ${a.rfid_tag}</div>
                </div>
                <span class="badge badge-sar">${a.species === 'Dog' && sar.sar_score ? `Fit: ${sar.sar_score}%` : 'Specialized'}</span>
            </div>
            
            <div class="trait-chips" style="margin-bottom: 0.75rem;">
                <span class="trait-chip"><i class="ph ph-lightning"></i> Energy: ${a.energy_level}/10</span>
                <span class="trait-chip"><i class="ph ph-brain"></i> Trainability: ${a.trainability}/10</span>
                <span class="trait-chip"><i class="ph ph-fire"></i> Drive: ${a.drive_level || 5}/10</span>
            </div>
            
            <div style="background: rgba(10, 132, 255, 0.08); border: 1px solid rgba(10, 132, 255, 0.25); padding: 0.65rem 0.85rem; border-radius: var(--radius-sm); font-size: 0.8rem; color: var(--text-secondary);">
                <strong style="color: var(--apple-green);"><i class="ph ph-check-circle"></i> Care Plan:</strong> ${actionMsg}
            </div>
        `;
        queue.appendChild(card);
    });
}

// Fetch and Render Customer Adoption Inquiries & Auto-Fill Staff Email Composer
async function fetchAdoptionRequests() {
    const listEl = document.getElementById('staff-adoption-requests-list');
    const summaryListEl = document.getElementById('staff-adoption-requests-summary-list');
    const badgeEl = document.getElementById('adoption-requests-count-badge');
    const navBadgeEl = document.getElementById('nav-requests-badge');

    try {
        const res = await fetch('/api/adoption-requests');
        const data = await res.json();
        const requests = data.requests || [];
        allAdoptionRequests = requests;

        if (badgeEl) badgeEl.innerText = `${requests.length} Inquiries`;
        if (navBadgeEl) navBadgeEl.innerText = `${requests.length}`;

        if (requests.length === 0) {
            const emptyHtml = `<p style="color: var(--text-secondary); font-size: 0.85rem;">No customer adoption inquiries submitted yet. Submit an adoption inquiry on the <a href="/customer" style="color: var(--apple-cyan);">PET CONNECT Public Portal</a> and it will automatically fill in here for staff dispatch.</p>`;
            if (listEl) listEl.innerHTML = emptyHtml;
            if (summaryListEl) summaryListEl.innerHTML = emptyHtml;
            return;
        }

        // Automatically fill out the Staff Email Composer with the newest customer request if none is loaded yet
        if (!selectedStaffRequestRef || !requests.some(r => r.request_ref === selectedStaffRequestRef)) {
            populateStaffEmailComposer(requests[0], false);
        }

        const renderListInto = (container) => {
            if (!container) return;
            container.innerHTML = '';
            requests.forEach((req) => {
                const isSelected = req.request_ref === selectedStaffRequestRef;
                const isStaffSent = (req.email_delivery_status || '').includes('STAFF') || (req.status || '').includes('STAFF');
                const statusColor = isStaffSent ? 'var(--apple-green)' : 'var(--apple-orange)';
                const gmailUrl = buildGmailComposeUrl(
                    req.applicant_email || req.adopter_email,
                    req.email_subject || `🐾 PET CONNECT Adoption Request Confirmed — ${req.pet_name} [#${req.request_ref}]`,
                    req.email_body_text || ''
                );

                const item = document.createElement('div');
                item.style.cssText = `background: ${isSelected ? 'rgba(10, 132, 255, 0.14)' : 'rgba(0,0,0,0.35)'}; border: 1px solid ${isSelected ? 'var(--apple-blue)' : 'var(--border-subtle)'}; border-radius: var(--radius-sm); padding: 0.9rem 1.05rem; display: flex; justify-content: space-between; align-items: center; gap: 0.85rem; flex-wrap: wrap; transition: all 0.2s ease;`;
                item.innerHTML = `
                    <div style="flex: 1; min-width: 220px;">
                        <div style="font-size: 0.78rem; color: var(--apple-cyan); font-weight: 700;">
                            Ref #${req.request_ref} • ${req.pet_name} (${req.pet_species} — ${req.pet_breed})
                        </div>
                        <div style="font-size: 0.92rem; font-weight: 600; color: var(--text-primary); margin-top: 0.15rem;">
                            Customer: ${req.applicant_name} &lt;${req.applicant_email}&gt; • ${req.applicant_phone || 'No Phone'}
                        </div>
                        <div style="font-size: 0.76rem; color: var(--text-secondary); margin-top: 0.15rem;">
                            Match Score: <strong>${req.compatibility_score || 94}%</strong> • Status: <span style="color: ${statusColor}; font-weight: 600;">${req.email_delivery_status}</span> • ${req.created_at}
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.45rem; flex-wrap: wrap;">
                        <button type="button" class="btn-apple" style="font-size: 0.76rem; padding: 0.38rem 0.75rem;" onclick="loadRequestIntoStaffComposer('${req.request_ref}')">
                            <i class="ph ph-magic-wand"></i> Auto-Fill in Composer
                        </button>
                        <a href="${gmailUrl}" target="_blank" onclick="markRequestSentViaQuickAction('${req.request_ref}', 'GMAIL_WEB')" class="btn-apple-secondary" style="font-size: 0.76rem; text-decoration: none; padding: 0.38rem 0.75rem; border-color: rgba(48,209,88,0.4); color: #30d158;">
                            <i class="ph-fill ph-google-logo"></i> 1-Click Send Gmail
                        </a>
                    </div>
                `;
                container.appendChild(item);
            });
        };

        renderListInto(listEl);
        renderListInto(summaryListEl);
    } catch (err) {
        console.error('Error loading adoption requests:', err);
    }
}

function buildGmailComposeUrl(toEmail, subject, bodyText) {
    const to = encodeURIComponent(toEmail || '');
    const su = encodeURIComponent(subject || 'PET CONNECT Adoption Confirmation');
    const bd = encodeURIComponent(bodyText || '');
    return `https://mail.google.com/mail/?view=cm&fs=1&to=${to}&su=${su}&body=${bd}`;
}

function loadRequestIntoStaffComposer(requestRef) {
    const req = allAdoptionRequests.find(r => r.request_ref === requestRef);
    if (!req) return;
    switchTab('adoption-requests');
    populateStaffEmailComposer(req, true);
}

function populateStaffEmailComposer(req, showNotification = true) {
    selectedStaffRequestRef = req.request_ref;

    const refInput = document.getElementById('staff-email-ref');
    const refBadge = document.getElementById('staff-composer-ref-badge');
    const compSpecies = document.getElementById('staff-comp-species');
    const compPet = document.getElementById('staff-comp-pet');
    const compStatus = document.getElementById('staff-comp-status');
    const compMeta = document.getElementById('staff-comp-meta');

    const toInput = document.getElementById('staff-email-to');
    const nameInput = document.getElementById('staff-email-name');
    const phoneInput = document.getElementById('staff-email-phone');
    const housingInput = document.getElementById('staff-email-housing');
    const subjectInput = document.getElementById('staff-email-subject');
    const noteInput = document.getElementById('staff-email-note');
    const bodyInput = document.getElementById('staff-email-body');
    const previewLink = document.getElementById('staff-preview-html-link');
    const feedbackEl = document.getElementById('staff-dispatch-feedback');

    if (refInput) refInput.value = req.request_ref;
    if (refBadge) refBadge.innerText = `Ref #${req.request_ref}`;
    if (compSpecies) compSpecies.innerText = `🐾 ${req.pet_species || req.species} ADOPTION INQUIRY • ${req.compatibility_score || 94}% COMPATIBILITY`;
    if (compPet) compPet.innerText = `${req.pet_name} (${req.pet_breed || req.breed}) — $${req.adoption_fee || 120} Adoption Fee`;
    if (compStatus) {
        compStatus.innerText = req.email_delivery_status || 'READY FOR STAFF DISPATCH';
        compStatus.className = (req.email_delivery_status || '').includes('STAFF') ? 'badge badge-lowrisk' : 'badge badge-sar';
    }
    if (compMeta) {
        compMeta.innerHTML = `<strong>Applicant:</strong> ${req.applicant_name || req.adopter_name} (&lt;${req.applicant_email || req.adopter_email}&gt;) • <strong>Submitted:</strong> ${req.created_at}${req.personal_note ? `<br><strong>Customer Note:</strong> "${req.personal_note}"` : ''}`;
    }

    if (toInput) toInput.value = req.applicant_email || req.adopter_email || '';
    if (nameInput) nameInput.value = req.applicant_name || req.adopter_name || '';
    if (phoneInput) phoneInput.value = req.applicant_phone || req.adopter_phone || 'Not provided';
    if (housingInput) housingInput.value = `${req.housing_type || 'house_yard'} • Pets: ${req.other_pets || 'none'} • Exp: ${req.experience_level || 'experienced'}`;
    if (subjectInput) subjectInput.value = req.email_subject || `🐾 PET CONNECT Adoption Request Confirmed — ${req.pet_name} [#${req.request_ref}]`;
    if (noteInput) noteInput.value = '';
    if (bodyInput) bodyInput.value = req.email_body_text || '';
    if (previewLink) previewLink.href = `/api/adoption-request/${req.request_ref}/email?format=html`;
    if (feedbackEl) feedbackEl.style.display = 'none';

    if (showNotification) {
        showToast(`Auto-filled customer request #${req.request_ref} for ${req.applicant_email || req.adopter_email}`, 'info');
    }
}

function getComposedEmailPayload(dispatchChannel) {
    const requestRef = (document.getElementById('staff-email-ref')?.value || selectedStaffRequestRef || '').trim();
    const toEmail = (document.getElementById('staff-email-to')?.value || '').trim();
    const toName = (document.getElementById('staff-email-name')?.value || '').trim();
    const subject = (document.getElementById('staff-email-subject')?.value || '').trim();
    const staffNote = (document.getElementById('staff-email-note')?.value || '').trim();
    let bodyText = (document.getElementById('staff-email-body')?.value || '').trim();

    if (staffNote && !bodyText.includes(staffNote)) {
        bodyText = `${bodyText}\n\n--- Shelter Coordinator Note ---\n${staffNote}\n`;
        const bodyEl = document.getElementById('staff-email-body');
        if (bodyEl) bodyEl.value = bodyText;
    }

    return {
        request_ref: requestRef,
        to_email: toEmail,
        to_name: toName,
        subject: subject,
        body_text: bodyText,
        staff_note: staffNote,
        dispatch_channel: dispatchChannel
    };
}

async function staffSendViaGmailWeb() {
    const payload = getComposedEmailPayload('GMAIL_WEB');
    if (!payload.request_ref || !payload.to_email) {
        showToast('Please select a customer adoption request first.', 'error');
        return;
    }

    const gmailUrl = buildGmailComposeUrl(payload.to_email, payload.subject, payload.body_text);
    window.open(gmailUrl, '_blank');
    await recordStaffDispatchOnBackend(payload);
}

async function staffSendViaMailto() {
    const payload = getComposedEmailPayload('MAILTO_CLIENT');
    if (!payload.request_ref || !payload.to_email) {
        showToast('Please select a customer adoption request first.', 'error');
        return;
    }

    const mailtoUrl = `mailto:${encodeURIComponent(payload.to_email)}?subject=${encodeURIComponent(payload.subject)}&body=${encodeURIComponent(payload.body_text)}`;
    window.location.href = mailtoUrl;
    await recordStaffDispatchOnBackend(payload);
}

async function staffApproveAndDispatchBackend() {
    const payload = getComposedEmailPayload('STAFF_CONSOLE');
    if (!payload.request_ref || !payload.to_email) {
        showToast('Please select a customer adoption request first.', 'error');
        return;
    }
    await recordStaffDispatchOnBackend(payload);
}

async function markRequestSentViaQuickAction(requestRef, channel) {
    try {
        await fetch(`/api/adoption-request/${requestRef}/staff-send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dispatch_channel: channel })
        });
        fetchAdoptionRequests();
        showToast(`Opened Gmail with pre-filled confirmation for #${requestRef}`, 'success');
    } catch (err) {
        console.error('Error marking quick send:', err);
    }
}

async function recordStaffDispatchOnBackend(payload) {
    const feedbackEl = document.getElementById('staff-dispatch-feedback');
    try {
        const res = await fetch(`/api/adoption-request/${payload.request_ref}/staff-send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            showToast(`Staff confirmation dispatched for #${payload.request_ref} to ${data.to}!`, 'success');
            if (feedbackEl) {
                feedbackEl.style.display = 'block';
                feedbackEl.style.background = 'rgba(48, 209, 88, 0.14)';
                feedbackEl.style.border = '1px solid rgba(48, 209, 88, 0.4)';
                feedbackEl.style.color = '#74c69d';
                feedbackEl.innerHTML = `<i class="ph-fill ph-check-circle"></i> <strong>Dispatched by Shelter Staff:</strong> Confirmation email for <strong>#${payload.request_ref}</strong> (${data.to}) is marked as <code>${data.delivery_status}</code>.`;
            }
            const compStatus = document.getElementById('staff-comp-status');
            if (compStatus) {
                compStatus.innerText = data.delivery_status;
                compStatus.className = 'badge badge-lowrisk';
            }
            fetchAdoptionRequests();
        } else {
            throw new Error(data.error || 'Could not dispatch staff confirmation.');
        }
    } catch (err) {
        if (feedbackEl) {
            feedbackEl.style.display = 'block';
            feedbackEl.style.background = 'rgba(255, 69, 58, 0.14)';
            feedbackEl.style.border = '1px solid rgba(255, 69, 58, 0.4)';
            feedbackEl.style.color = '#ff6961';
            feedbackEl.innerText = err.message || 'Error dispatching confirmation email.';
        }
    }
}


