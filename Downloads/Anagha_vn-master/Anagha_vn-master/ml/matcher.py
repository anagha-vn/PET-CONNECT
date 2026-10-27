import numpy as np


class VectorMatcher:
    """
    PET CONNECT Vector-Based Cosine Similarity & Multi-Dimensional Manageability Engine.
    Maps adopter lifestyle constraints and animal care requirements across 5 primary manageability pillars:
      1. Energy Compatibility (user energy capacity & daily hours vs animal energy & exercise needs)
      2. Maintenance Compatibility (user grooming availability vs animal grooming & care complexity)
      3. Space & Yard Compatibility (home indoor size & yard access vs animal space & outdoor requirements)
      4. Care Budget Compatibility (monthly care budget & setup costs vs animal upkeep and adoption fee)
      5. Family & Household Compatibility (child safety ages & companion sociability)
    Blended with 7D Vector Cosine Similarity for optimal mathematical and practical alignment.
    """

    @staticmethod
    def _clamp(val, low, high, default):
        """Safely converts a value to float and clamps it within [low, high]."""
        try:
            v = float(val)
            if np.isnan(v) or np.isinf(v):
                return float(default)
            return float(max(low, min(high, v)))
        except (TypeError, ValueError):
            return float(default)

    @staticmethod
    def cosine_similarity(v1, v2):
        """Calculates cosine similarity between two 1D numerical feature vectors."""
        vec1 = np.array(v1, dtype=float)
        vec2 = np.array(v2, dtype=float)

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    @classmethod
    def generate_care_checklist(cls, animal_profile):
        """
        Generates a species-aware, actionable care preparation checklist for confirmation emails
        and adopter onboarding on PET CONNECT.
        """
        species = str(animal_profile.get('species', 'Dog')).strip()
        s_lower = species.lower()
        clean_name = str(animal_profile.get('name', 'Companion')).split(' (ANM-')[0]
        ex_hours = cls._clamp(animal_profile.get('exercise_needed_hours', 1.0), 0.1, 6.0, 1.0)
        grooming = int(cls._clamp(animal_profile.get('grooming_needed', 4), 1, 10, 4))
        budget = int(cls._clamp(animal_profile.get('budget_needed', 4), 1, 10, 4))
        yard = int(cls._clamp(animal_profile.get('yard_needed', 0), 0, 3, 0))
        est_monthly = int(budget * 12 + 15)

        checklist = []

        # 1. Activity & Enrichment
        if ex_hours <= 0.5:
            checklist.append(f"Daily Activity: Plan ~{int(ex_hours * 60)} mins of gentle indoor interaction and enrichment for {clean_name}.")
        else:
            checklist.append(f"Daily Activity: Schedule ~{ex_hours:.1f} hours/day for walks, play sessions, and mental stimulation.")

        # 2. Grooming & Upkeep
        if grooming <= 3:
            checklist.append("Grooming Routine: Low-maintenance coat — a quick weekly brush and routine hygiene check is sufficient.")
        elif grooming <= 6:
            checklist.append("Grooming Routine: Moderate upkeep — prepare a soft slicker brush for 2–3 weekly grooming sessions.")
        else:
            checklist.append("Grooming Routine: High-care coat — schedule daily brushing and regular professional grooming every 4–6 weeks.")

        # 3. Habitat & Space Setup
        if 'rabbit' in s_lower:
            checklist.append("Home Setup: Prepare an indoor exercise pen (X-pen), litter box with paper-based pellets, and unlimited timothy hay.")
        elif 'bird' in s_lower:
            checklist.append("Home Setup: Set up a draft-free flight cage with natural wood perches and foraging toys away from kitchen fumes.")
        elif 'pocket' in s_lower or 'small' in s_lower:
            checklist.append("Home Setup: Prepare a spacious multi-zone enclosure with deep paper bedding, hideouts, and chew-safe enrichment.")
        elif 'reptile' in s_lower:
            checklist.append("Home Setup: Verify terrarium temperature gradient, UVB lighting timer, and secure basking hideouts before arrival.")
        elif 'cat' in s_lower:
            checklist.append("Home Setup: Set up a quiet acclimation room with a scratching post, vertical perch, and clean litter station.")
        else:
            if yard == 0:
                checklist.append("Home Setup: Apartment-friendly — prepare a cozy orthopedic bed, walking harness, and interactive puzzle toys.")
            else:
                checklist.append("Home Setup: Inspect fenced yard perimeters and prepare a quiet indoor resting area for post-walk decompression.")

        # 4. Budget & Wellness
        checklist.append(f"Wellness & Budget: Reserve ~${est_monthly}/month for quality nutrition, preventive care, and routine supplies.")

        return checklist

    @classmethod
    def calculate_manageability_dimensions(cls, user_profile, animal_profile):
        """
        Calculates distinct 0-100% manageability sub-scores and descriptive summaries
        for Energy, Maintenance, Space, Budget, and Family safety.
        """
        user_profile = user_profile or {}
        animal_profile = animal_profile or {}

        # --- 1. User Profiles & Clamped Aliases ---
        user_ex_hours = cls._clamp(user_profile.get('exercise_time_hours', 1.5), 0.2, 8.0, 1.5)
        raw_energy = user_profile.get('energy_capacity')
        if raw_energy is not None:
            user_energy = cls._clamp(raw_energy, 1.0, 10.0, 5.0)
        else:
            user_energy = cls._clamp(user_ex_hours * 3.33, 1.0, 10.0, 5.0)

        raw_maint = user_profile.get('maintenance_capacity')
        if raw_maint is None:
            raw_maint = user_profile.get('grooming_time_available', 5.0)
        user_maint = cls._clamp(raw_maint, 1.0, 10.0, 5.0)

        user_space = cls._clamp(user_profile.get('space_limit', 5.0), 1.0, 10.0, 5.0)
        user_yard = int(cls._clamp(user_profile.get('yard_size', 1), 0, 3, 1))
        user_budget = cls._clamp(user_profile.get('budget_limit', 5.0), 1.0, 10.0, 5.0)
        user_setup = cls._clamp(user_profile.get('setup_budget', user_budget), 1.0, 10.0, user_budget)
        user_child_age = cls._clamp(user_profile.get('youngest_child_age', 10.0), 0.0, 18.0, 10.0)

        # --- 2. Animal Profile Fields ---
        species = str(animal_profile.get('species', 'Dog')).strip()
        a_energy = cls._clamp(animal_profile.get('energy_level', 5.0), 1.0, 10.0, 5.0)
        a_ex_hours = cls._clamp(animal_profile.get('exercise_needed_hours', 1.0), 0.1, 6.0, 1.0)
        a_grooming = cls._clamp(animal_profile.get('grooming_needed', 5.0), 1.0, 10.0, 5.0)
        a_space = cls._clamp(animal_profile.get('space_needed', 5.0), 1.0, 10.0, 5.0)
        a_yard = int(cls._clamp(animal_profile.get('yard_needed', 0), 0, 3, 0))
        a_budget = cls._clamp(animal_profile.get('budget_needed', 5.0), 1.0, 10.0, 5.0)
        a_setup = cls._clamp(animal_profile.get('setup_budget_needed', 5.0), 1.0, 10.0, 5.0)
        a_fee = int(cls._clamp(animal_profile.get('adoption_fee', 75), 0, 1000, 75))
        min_child_age = cls._clamp(animal_profile.get('child_friendly_min_age', 0.0), 0.0, 18.0, 0.0)
        sociability = cls._clamp(animal_profile.get('sociability', 5.0), 1.0, 10.0, 5.0)
        special_meds = int(cls._clamp(animal_profile.get('special_medical_needs', 0), 0, 2, 0))
        is_indoor_species = species in ['Cat', 'Rabbit', 'Bird', 'Pocket Pet', 'Small Pet', 'Reptile']

        # --- Dimension 1: Energy Compatibility (0-100%) ---
        diff_energy = a_energy - user_energy
        pen_energy = (diff_energy * 10.0) if diff_energy > 0 else (abs(diff_energy) * 3.0)
        diff_ex = a_ex_hours - user_ex_hours
        pen_ex = (diff_ex * 25.0) if diff_ex > 0 else (abs(diff_ex) * 8.0)
        energy_match = max(0.0, min(100.0, 100.0 - 0.5 * (pen_energy + pen_ex)))

        if a_ex_hours <= 0.5 and user_ex_hours <= 1.0:
            energy_summary = f"Calm & relaxed — needs ~{int(a_ex_hours * 60)}m daily activity, ideal for easy-going home days."
            energy_status = 'excellent'
        elif a_ex_hours >= 2.0 and user_ex_hours >= 2.0:
            energy_summary = f"High endurance sync — matches your {user_ex_hours}h/day active lifestyle and outdoor stamina."
            energy_status = 'excellent'
        elif abs(a_ex_hours - user_ex_hours) <= 0.5:
            energy_summary = f"Activity aligned — requires ~{a_ex_hours}h daily activity, matching your schedule."
            energy_status = 'good'
        elif a_ex_hours > user_ex_hours:
            energy_summary = f"High energy demand — pet needs ~{a_ex_hours}h/day (exceeds your {user_ex_hours}h capacity)."
            energy_status = 'challenging'
        else:
            energy_summary = f"Gentle pace — pet requires only ~{a_ex_hours}h/day, very manageable with light strolls."
            energy_status = 'good'

        # --- Dimension 2: Maintenance Compatibility (0-100%) ---
        diff_maint = a_grooming - user_maint
        pen_maint = (diff_maint * 12.0) if diff_maint > 0 else (abs(diff_maint) * 2.5)
        if special_meds == 1 and user_maint < 6:
            pen_maint += 12.0
        maintenance_match = max(0.0, min(100.0, 100.0 - pen_maint))

        if a_grooming <= 2 and not special_meds:
            maintenance_summary = "Low maintenance — wash-and-wear coat with minimal brushing required."
            maintenance_status = 'excellent'
        elif a_grooming <= 5:
            maintenance_summary = "Moderate care — weekly light brushing and standard routine upkeep."
            maintenance_status = 'good'
        elif special_meds:
            maintenance_summary = "Attentive care — requires regular coat care and special wellness routine."
            maintenance_status = 'challenging' if user_maint < 6 else 'good'
        else:
            maintenance_summary = "High maintenance — requires regular brushing, detangling, or styling."
            maintenance_status = 'challenging' if user_maint < 7 else 'good'

        # --- Dimension 3: Space & Yard Compatibility (0-100%) ---
        diff_space = a_space - user_space
        pen_space = (diff_space * 10.0) if diff_space > 0 else (abs(diff_space) * 2.0)
        if user_yard == 0:
            if not is_indoor_species and a_yard >= 2:
                pen_space += 32.0
            elif not is_indoor_species and a_yard == 1:
                pen_space += 10.0
        elif user_yard < a_yard:
            pen_space += (a_yard - user_yard) * 14.0
        space_match = max(0.0, min(100.0, 100.0 - pen_space))

        if user_yard == 0 or a_yard == 0:
            if is_indoor_species:
                space_summary = "Apartment friendly — thrives happily indoors without requiring a private yard."
                space_status = 'excellent'
            elif a_space <= 4:
                space_summary = "Apartment adaptable — relaxed indoors with neighborhood walks."
                space_status = 'good'
            else:
                space_summary = "Apartment notice — requires dedicated daily park excursions since no private yard."
                space_status = 'moderate'
        elif user_yard >= a_yard:
            space_summary = "Spacious match — your home and yard provide ample space for active play."
            space_status = 'excellent'
        else:
            space_summary = "Prefers larger yard — energetic companion that benefits from secure fenced space."
            space_status = 'moderate'

        # --- Dimension 4: Care Budget Compatibility (0-100%) ---
        diff_budget = a_budget - user_budget
        pen_budget = (diff_budget * 13.0) if diff_budget > 0 else (abs(diff_budget) * 2.0)
        diff_setup = a_setup - user_setup
        if diff_setup > 0:
            pen_budget += diff_setup * 4.0
        budget_match = max(0.0, min(100.0, 100.0 - pen_budget))

        est_monthly = int(a_budget * 12 + 15)
        if a_budget <= 3:
            budget_summary = f"Budget friendly — low monthly care (~${est_monthly}/mo) and ${a_fee} adoption fee."
            budget_status = 'excellent'
        elif a_budget <= 6:
            budget_summary = f"Moderate upkeep — routine nutrition and veterinary care (~${est_monthly}/mo)."
            budget_status = 'good'
        else:
            budget_summary = f"Higher care budget — specialized nutrition or care (~${int(a_budget * 15 + 25)}/mo)."
            budget_status = 'moderate'

        # --- Dimension 5: Family & Household Compatibility (0-100%) ---
        pen_fam = 0.0
        if user_child_age < min_child_age:
            pen_fam = (min_child_age - user_child_age) * 10.0 + 15.0
        if sociability >= 7:
            pen_fam = max(0.0, pen_fam - 6.0)
        elif sociability <= 3:
            pen_fam += 10.0
        family_match = max(0.0, min(100.0, 100.0 - pen_fam))

        if user_child_age >= min_child_age and sociability >= 6:
            family_summary = f"Family safe — gentle, patient temperament suitable for children age {int(min_child_age)}+."
            family_status = 'excellent'
        elif user_child_age < min_child_age:
            family_summary = f"Child safety notice — best for older kids age {int(min_child_age)}+ due to delicate handling."
            family_status = 'challenging'
        else:
            family_summary = "Peaceful companion — best suited for mature or quieter home environments."
            family_status = 'good'

        return {
            'scores': {
                'energy_match': round(energy_match, 1),
                'maintenance_match': round(maintenance_match, 1),
                'space_match': round(space_match, 1),
                'budget_match': round(budget_match, 1),
                'family_match': round(family_match, 1)
            },
            'details': {
                'energy': {
                    'score': round(energy_match, 1),
                    'summary': energy_summary,
                    'status': energy_status,
                    'animal_energy': a_energy,
                    'animal_exercise_hours': a_ex_hours
                },
                'maintenance': {
                    'score': round(maintenance_match, 1),
                    'summary': maintenance_summary,
                    'status': maintenance_status,
                    'grooming_needed': a_grooming
                },
                'space': {
                    'score': round(space_match, 1),
                    'summary': space_summary,
                    'status': space_status,
                    'yard_needed': a_yard,
                    'space_needed': a_space
                },
                'budget': {
                    'score': round(budget_match, 1),
                    'summary': budget_summary,
                    'status': budget_status,
                    'estimated_monthly': est_monthly,
                    'adoption_fee': a_fee
                },
                'family': {
                    'score': round(family_match, 1),
                    'summary': family_summary,
                    'status': family_status,
                    'min_child_age': int(min_child_age)
                }
            }
        }

    @classmethod
    def generate_explanations(cls, user_profile, animal_profile, manageability=None):
        """Generates natural, human explanations for why this animal matches the adopter's manageability."""
        explanations = []
        if manageability is None:
            manageability = cls.calculate_manageability_dimensions(user_profile, animal_profile)

        details = manageability['details']
        scores = manageability['scores']

        if scores['energy_match'] >= 85:
            explanations.append(f"⚡ {details['energy']['summary']}")
        elif scores['energy_match'] < 60:
            explanations.append(f"⚡ Note: {details['energy']['summary']}")

        if scores['maintenance_match'] >= 85:
            explanations.append(f"✂️ {details['maintenance']['summary']}")
        elif scores['maintenance_match'] < 60:
            explanations.append(f"✂️ Note: {details['maintenance']['summary']}")

        if scores['space_match'] >= 85:
            explanations.append(f"🏡 {details['space']['summary']}")

        if scores['budget_match'] >= 85:
            explanations.append(f"💰 {details['budget']['summary']}")

        if scores['family_match'] < 70:
            explanations.append(f"👶 Note: {details['family']['summary']}")
        elif scores['family_match'] >= 90:
            explanations.append(f"👶 {details['family']['summary']}")

        if len(explanations) < 2:
            sociability = animal_profile.get('sociability', 5)
            explanations.append(f"🐾 Well-balanced rescue companion (Sociability: {sociability}/10) suited to your lifestyle.")

        return explanations[:4]

    @classmethod
    def calculate_match(cls, user_profile, animal_profile):
        """
        Calculates combined 7D Vector Cosine Similarity and Multi-Dimensional Manageability breakdown.
        Supports Dogs, Cats, Rabbits, Birds, Pocket Pets, and Reptiles.
        """
        user_profile = user_profile or {}
        animal_profile = animal_profile or {}

        # 1. Indoor Space (1-10)
        u_space = cls._clamp(user_profile.get('space_limit', 5), 1.0, 10.0, 5.0)
        a_space = cls._clamp(animal_profile.get('space_needed', 5), 1.0, 10.0, 5.0)

        # 2. Yard Size Access (0: None, 1: Small, 2: Medium, 3: Large -> scaled to 1-10)
        u_yard = cls._clamp(user_profile.get('yard_size', 1), 0.0, 3.0, 1.0) * 3.3 + 0.1
        a_yard = cls._clamp(animal_profile.get('yard_needed', 0), 0.0, 3.0, 0.0) * 3.3 + 0.1

        # 3. Monthly Budget (1-10)
        u_budget = cls._clamp(user_profile.get('budget_limit', 5), 1.0, 10.0, 5.0)
        a_budget = cls._clamp(animal_profile.get('budget_needed', 5), 1.0, 10.0, 5.0)

        # 4. Daily Exercise Time Available (hours -> 1-10 scale)
        u_exercise = min(10.0, cls._clamp(user_profile.get('exercise_time_hours', 1.5), 0.2, 8.0, 1.5) * 2.5)
        a_exercise = min(10.0, cls._clamp(animal_profile.get('exercise_needed_hours', 1.0), 0.1, 6.0, 1.0) * 2.5)

        # 5. Sociability & Child Compatibility (1-10)
        u_child_age = cls._clamp(user_profile.get('youngest_child_age', 10), 0.0, 18.0, 10.0)
        a_min_child_age = cls._clamp(animal_profile.get('child_friendly_min_age', 0), 0.0, 18.0, 0.0)
        child_safety_penalty = 3.0 if u_child_age < a_min_child_age else 0.0
        u_sociability = max(1.0, cls._clamp(user_profile.get('sociability_pref', 5), 1.0, 10.0, 5.0) - child_safety_penalty)
        a_sociability = cls._clamp(animal_profile.get('sociability', 5), 1.0, 10.0, 5.0)

        # 6. Grooming / Maintenance Time Available vs Needed (1-10)
        raw_maint = user_profile.get('maintenance_capacity')
        if raw_maint is None:
            raw_maint = user_profile.get('grooming_time_available', 5)
        u_grooming = cls._clamp(raw_maint, 1.0, 10.0, 5.0)
        a_grooming = cls._clamp(animal_profile.get('grooming_needed', 5), 1.0, 10.0, 5.0)

        # 7. Setup Budget (1-10)
        u_setup = cls._clamp(user_profile.get('setup_budget', 5), 1.0, 10.0, 5.0)
        a_setup = cls._clamp(animal_profile.get('setup_budget_needed', 5), 1.0, 10.0, 5.0)

        u_vector = [u_space, u_yard, u_budget, u_exercise, u_sociability, u_grooming, u_setup]
        a_vector = [a_space, a_yard, a_budget, a_exercise, a_sociability, a_grooming, a_setup]

        # Pure 7D Vector Cosine Similarity
        cos_sim = cls.cosine_similarity(u_vector, a_vector)

        # Multi-Dimensional Manageability Sub-Scores
        manageability = cls.calculate_manageability_dimensions(user_profile, animal_profile)
        m_scores = manageability['scores']
        m_details = manageability['details']

        # Weighted composite manageability score (Energy: 28%, Maint: 24%, Space: 20%, Budget: 16%, Family: 12%)
        manageability_composite = (
            0.28 * m_scores['energy_match'] +
            0.24 * m_scores['maintenance_match'] +
            0.20 * m_scores['space_match'] +
            0.16 * m_scores['budget_match'] +
            0.12 * m_scores['family_match']
        )

        # Overall Compatibility Percentage (40% Vector Cosine Geometry + 60% Personal Manageability)
        overall_score = round(0.40 * (cos_sim * 100.0) + 0.60 * manageability_composite, 1)
        explanations = cls.generate_explanations(user_profile, animal_profile, manageability)

        if overall_score >= 90:
            compatibility_tier = "Ideal Match"
        elif overall_score >= 78:
            compatibility_tier = "Strong Match"
        elif overall_score >= 62:
            compatibility_tier = "Moderate Match"
        else:
            compatibility_tier = "High Care Demand"

        clean_name = str(animal_profile.get('name', 'Companion')).split(' (ANM-')[0]
        if m_scores['energy_match'] >= 85 and m_scores['maintenance_match'] >= 85:
            primary_explanation = f"{clean_name} matches your manageable energy and low-maintenance upkeep routine."
        elif m_scores['space_match'] >= 90:
            primary_explanation = f"{clean_name} thrives in your living space and fits your care capacity."
        elif explanations:
            primary_explanation = explanations[0].replace('⚡ ', '').replace('✂️ ', '').replace('🏡 ', '').replace('💰 ', '').replace('👶 ', '')
        else:
            primary_explanation = "Compatible companion matching your lifestyle manageability profile."

        care_checklist = cls.generate_care_checklist(animal_profile)

        return {
            'cosine_similarity': round(cos_sim, 4),
            'compatibility_score': overall_score,
            'compatibility_tier': compatibility_tier,
            'manageability_composite': round(manageability_composite, 1),
            'metrics_breakdown': {
                'energy_match': m_scores['energy_match'],
                'maintenance_match': m_scores['maintenance_match'],
                'space_match': m_scores['space_match'],
                'budget_match': m_scores['budget_match'],
                'family_match': m_scores['family_match'],
                'exercise_match': m_scores['energy_match'],
                'grooming_match': m_scores['maintenance_match'],
                'yard_match': m_scores['space_match'],
                'sociability_match': m_scores['family_match']
            },
            'manageability_details': m_details,
            'explanations': explanations,
            'primary_explanation': primary_explanation,
            'care_checklist': care_checklist,
            'user_vector': u_vector,
            'animal_vector': a_vector
        }
