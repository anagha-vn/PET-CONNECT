from config import Config

class SpecializedPlacementRouter:
    """
    Specialized Placement Triage:
    Humane shelter placement router evaluating companion profiles for specialized home environments:
      - WORKING_K9: High-drive, high-stamina dogs suited for Search & Rescue, detection, or working sport handlers.
      - BARN_CAT: Independent, high-prey-drive working cats suited for safe rural barn/sanctuary rodent deterrence.
      - EXOTIC_SPECIALIST: Reptiles or complex birds requiring specialized vivarium setups or exotic foster care.
      - STANDARD_ADOPTION: Loving family home companions.
    """
    
    @staticmethod
    def evaluate_candidate(animal_profile):
        """
        Evaluates an animal profile for specialized sanctuary routing or standard adoption.
        
        animal_profile: dict with keys: species, energy_level, trainability, drive_level, 
                        sociability, setup_budget_needed, special_medical_needs, size
        """
        species = animal_profile.get('species', 'Dog')
        energy = int(animal_profile.get('energy_level', 5))
        trainability = int(animal_profile.get('trainability', 5))
        drive = int(animal_profile.get('drive_level', 5))
        sociability = int(animal_profile.get('sociability', 5))
        setup_budget = int(animal_profile.get('setup_budget_needed', 5))
        special_meds = int(animal_profile.get('special_medical_needs', 0))
        
        th = getattr(Config, 'SAR_THRESHOLDS', {'energy_level': 8, 'trainability': 8, 'drive_level': 8})
        criteria = getattr(Config, 'SPECIALIZED_PLACEMENT_CRITERIA', {})
        
        # 1. Working K9 Evaluation
        is_working_k9 = (
            species == 'Dog' and
            energy >= th.get('energy_level', 8) and
            trainability >= th.get('trainability', 8) and
            drive >= th.get('drive_level', 8)
        )
        
        # 2. Barn Cat Evaluation
        is_barn_cat = (
            species == 'Cat' and
            drive >= 7 and
            sociability <= 4
        )
        
        # 3. Exotic Specialist Evaluation
        is_exotic_specialist = (
            species in ['Reptile', 'Bird'] and
            (special_meds >= 1 or setup_budget >= 7)
        )
        
        reasons = []
        if is_working_k9:
            placement_type = 'WORKING_K9'
            routing_status = 'SPECIALIZED_WORKING_K9_PLACEMENT'
            suppress_civilian = True
            fit_score = round(((drive / 10.0) * 0.40 + (energy / 10.0) * 0.30 + (trainability / 10.0) * 0.30) * 100, 1)
            description = "Exceptional working drive, stamina, and handler focus. Routed to Search & Rescue task forces or working K9 partners."
            reasons.append(f"Exceeds high working energy threshold ({energy}/10 >= {th.get('energy_level', 8)}).")
            reasons.append(f"Exceptional trainability rating ({trainability}/10 >= {th.get('trainability', 8)}).")
            reasons.append(f"High task and prey drive ({drive}/10 >= {th.get('drive_level', 8)}).")

        elif is_barn_cat:
            placement_type = 'BARN_CAT'
            routing_status = 'SPECIALIZED_BARN_CAT_PLACEMENT'
            suppress_civilian = True
            fit_score = round(((drive / 10.0) * 0.60 + ((10 - sociability) / 10.0) * 0.40) * 100, 1)
            description = "Independent feline with strong prey drive. Well-suited for safe, working barn homes or rural rodent deterrence."
            reasons.append(f"High natural rodent-deterrence drive ({drive}/10 >= 7).")
            reasons.append(f"Prefers independent, low-touch outdoor shelter life (sociability {sociability}/10 <= 4).")

        elif is_exotic_specialist:
            placement_type = 'EXOTIC_SPECIALIST'
            routing_status = 'SPECIALIZED_EXOTIC_CARE_PLACEMENT'
            suppress_civilian = False
            fit_score = round(((setup_budget / 10.0) * 0.50 + (special_meds / 2.0) * 0.50) * 100, 1)
            description = "Requires specialized habitat parameters (UVB, humidity, or aviary enclosure) and experienced exotic care."
            if special_meds >= 1:
                reasons.append(f"Requires experienced exotic medical management (needs score {special_meds}/2).")
            if setup_budget >= 7:
                reasons.append(f"Requires high-tier specialized vivarium/lighting equipment (setup index {setup_budget}/10).")

        else:
            placement_type = 'STANDARD_ADOPTION'
            routing_status = 'STANDARD_FAMILY_ADOPTION'
            suppress_civilian = False
            fit_score = round((sociability / 10.0) * 100, 1)
            description = "Balanced companion temperament ideally suited for standard loving family adoption."
            reasons.append(f"Companionable temperament suitable for typical civilian household (sociability {sociability}/10).")
            
        return {
            'placement_type': placement_type,
            'is_specialized': placement_type != 'STANDARD_ADOPTION',
            'is_sar_candidate': is_working_k9,
            'routing_status': routing_status,
            'suppress_civilian_adoption': suppress_civilian,
            'specialized_score': fit_score,
            'sar_score': fit_score,
            'placement_description': description,
            'tactical_metrics': {
                'drive_score': round(drive * 10.0, 1),
                'energy_stamina': round(energy * 10.0, 1),
                'trainability_rating': round(trainability * 10.0, 1),
                'scent_work_potential': round(drive * 10.0, 1),
                'physical_stamina': round(energy * 10.0, 1),
                'handler_responsiveness': round(trainability * 10.0, 1)
            },
            'eval_summary': reasons,
            'reasons': reasons
        }


# Backwards compatibility alias
OutlierSARRouter = SpecializedPlacementRouter
