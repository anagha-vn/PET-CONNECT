import os
import sys
import sqlite3
import pandas as pd
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import Config


def generate_shelter_dataset(num_samples=2500):
    """
    Generates a realistic multi-species animal sanctuary dataset.
    Supported Species:
      - Dogs (e.g. Golden Retriever, Labrador Retriever, German Shepherd, Beagle, Boxer, Husky, Border Collie, Dachshund, Poodle Mix, Belgian Malinois)
      - Cats (e.g. Domestic Shorthair, Siamese, Maine Coon, Tabby, Ragdoll, British Shorthair)
      - Rabbits (e.g. Holland Lop, Netherland Dwarf, Mini Rex, Lionhead, Dutch Rabbit)
      - Birds (e.g. Cockatiel, Budgerigar/Parakeet, Green-Cheeked Conure, Lovebird, Finch)
      - Pocket Pets (e.g. Guinea Pig, Syrian Hamster, Ferret, Chinchilla, Fancy Rat)
      - Reptiles (e.g. Bearded Dragon, Leopard Gecko, Ball Python, Russian Tortoise, Corn Snake)
    """
    np.random.seed(42)

    species_list = ['Dog', 'Cat', 'Rabbit', 'Bird', 'Pocket Pet', 'Reptile']
    species_probs = [0.38, 0.28, 0.12, 0.08, 0.08, 0.06]

    breeds_by_species = {
        'Dog': [
            'Golden Retriever', 'Labrador Retriever', 'German Shepherd', 'Beagle',
            'Boxer', 'Husky', 'Border Collie', 'Dachshund', 'Poodle Mix', 'Belgian Malinois'
        ],
        'Cat': [
            'Domestic Shorthair', 'Siamese', 'Maine Coon', 'Tabby', 'Ragdoll', 'British Shorthair'
        ],
        'Rabbit': [
            'Holland Lop', 'Netherland Dwarf', 'Mini Rex', 'Lionhead', 'Dutch Rabbit'
        ],
        'Bird': [
            'Cockatiel', 'Budgerigar/Parakeet', 'Green-Cheeked Conure', 'Lovebird', 'Finch'
        ],
        'Pocket Pet': [
            'Guinea Pig', 'Syrian Hamster', 'Ferret', 'Chinchilla', 'Fancy Rat'
        ],
        'Reptile': [
            'Bearded Dragon', 'Leopard Gecko', 'Ball Python', 'Russian Tortoise', 'Corn Snake'
        ]
    }

    colors = [
        'Black', 'Brown/Tan', 'White', 'Golden', 'Brindle', 'Spotted',
        'Grey/Silver', 'Calico/Tricolor', 'Emerald/Yellow', 'Sandy/Orange'
    ]
    intake_seasons = ['Spring Peak', 'Summer High', 'Fall Moderate', 'Winter Standard']

    bios_by_species = {
        'Dog': [
            "Affectionate retriever who loves water fetch, belly rubs, and trail walks. Surrendered due to family relocation; thrives in active homes.",
            "High-drive working canine with sharp focus and boundless stamina. Thrives when given agility coursework, scent tracking, or tactical jobs.",
            "Sweet family companion who adores children, car rides, and nap time on plush dog beds. Fully house-trained and walks gently on leash.",
            "Gentle senior companion surrendered when previous owner moved to assisted living. Calm, loving, and content with quiet neighborhood strolls.",
            "Playful and curious youngster who gets along swimmingly with other dogs. Quick learner who loves interactive treat puzzle toys."
        ],
        'Cat': [
            "Affectionate purr-machine who loves sunbeams, catnip mice, and warm lap cuddles during quiet evenings.",
            "Independent spirit who loves birdwatching from window perches. Independent temperament makes them an ideal safe working barn companion.",
            "Sweet Siamese mix who purrs the moment you enter the room. Enjoys perch lounging, slow blinks, and gentle chin scratches.",
            "Gentle giant who loves being brushed, gazing out windows, and curling up like a soft cloud beside your feet.",
            "Playful kitten-at-heart who greets visitors at the door with soft meows, headbutts, and cheerful curiosity."
        ],
        'Rabbit': [
            "Gentle senior rabbit surrendered due to landlord restrictions; loves dandelion greens, timothy hay, and soft forehead rubs.",
            "Curious Holland Lop who loves cardboard foraging tunnels, fresh mint leaves, and doing energetic morning binkies across rugs.",
            "Calm Netherland Dwarf who enjoys gentle strokes along their ears, chew toys, and quiet companionship while you work or read.",
            "Docile Mini Rex with velvet-soft fur who enjoys hopping through obstacle tunnels and nibbling fresh romaine stalks.",
            "Friendly Dutch Rabbit pair who love exploring bunny-proofed rooms, snacking on coriander, and resting side-by-side."
        ],
        'Bird': [
            "Vibrant Cockatiel who whistles cheerful tunes in the morning and loves perching on trusted shoulders for head scratches.",
            "Inquisitive Green-Cheeked Conure who loves learning target training tricks, flying laps, and enjoying fresh morning veggie chop.",
            "Gentle Budgerigar pair surrendered after owner downsizing; loves singing melodies together and exploring leafy kale greens.",
            "Curious Lovebird with bright plumage who enjoys interactive wooden bell toys and cuddling inside a warm fleece hut.",
            "Peaceful flock of Finches whose gentle chirping brings a serene, cheerful atmosphere to any sunny living space."
        ],
        'Pocket Pet': [
            "Inseparable pair of bonded Guinea Pigs who wheek with pure joy whenever the vegetable crisper opens; docile and love lap towel cuddles.",
            "Curious Syrian Hamster who enjoys burrowing in deep aspen bedding, running on their silent wheel at dusk, and snacking on pumpkin seeds.",
            "Playful Ferret duo who love bounding through flexible tunnels, playing hide-and-seek, and dozing together in fleece hammocks.",
            "Friendly Fancy Rat duo who love solving food puzzles, riding on shoulders, and learning clever clicker tricks.",
            "Velvety Chinchilla who loves evening dust baths, wooden chew blocks, and bouncing playfully between cage ledges."
        ],
        'Reptile': [
            "Docile Bearded Dragon accustomed to gentle handling; loves basking under warm UVB, eating turnip greens, and calmly hanging out on sweaters.",
            "Gentle Leopard Gecko who is easy to hold, enjoys waxworm treats, and spends peaceful afternoons in moist moss hides.",
            "Healthy Ball Python with great feeding history; calm temperament when handled and loves exploring sturdy climbing branches.",
            "Russian Tortoise with a delightful personality; loves roaming secure outdoor grass pens in summer and munching dandelion weeds.",
            "Curious and docile Corn Snake with striking markings; calm during handling and thrives in a well-regulated terrarium."
        ]
    }

    names_by_species = {
        'Dog': ['Max', 'Bella', 'Charlie', 'Luna', 'Cooper', 'Daisy', 'Milo', 'Rocky', 'Zus', 'Thor', 'Apollo', 'Rex', 'Shadow', 'Duke', 'Maverick', 'Rosie', 'Bailey', 'Scout'],
        'Cat': ['Oliver', 'Cleo', 'Simba', 'Nala', 'Felix', 'Willow', 'Jasper', 'Mochi', 'Chloe', 'Leo', 'Mia', 'Whiskers', 'Pepper', 'Smokey'],
        'Rabbit': ['Barnaby', 'Clover', 'Thumper', 'Brambles', 'Hazel', 'Pippin', 'Boba', 'Peanut', 'Snowball', 'Carrot', 'Bunny', 'Mallow'],
        'Bird': ['Sunny', 'Kiwi', 'Pip', 'Mango', 'Bluebell', 'Echo', 'Skye', 'Peaches', 'Chirpy', 'Rio', 'Zephyr', 'Pico'],
        'Pocket Pet': ['Pip & Squeak', 'Nutmeg', 'Gizmo', 'Marshmallow', 'Fudge', 'Cheeks', 'Button', 'Waffles', 'Truffle', 'Bandit', 'Oatmeal'],
        'Reptile': ['Ziggy', 'Yoshi', 'Pascal', 'Spike', 'Draco', 'Atlas', 'Noodle', 'Basil', 'Cleo', 'Echo', 'Titan', 'Sunny']
    }

    # Curated first 15 demo companions across all species and specialized triage categories
    curated_demo = [
        {
            'name': 'Max', 'species': 'Dog', 'breed': 'Golden Retriever', 'age_months': 26,
            'coat_color': 'Golden', 'size': 'Large', 'energy_level': 6, 'trainability': 8, 'drive_level': 5,
            'space_needed': 6, 'yard_needed': 2, 'exercise_needed_hours': 1.5, 'child_friendly_min_age': 0,
            'grooming_needed': 6, 'setup_budget_needed': 6, 'budget_needed': 6, 'sociability': 9,
            'adoption_fee': 180, 'length_of_stay_days': 12, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Devoted cuddlebug with a heart of pure gold. Loves fetching tennis balls, swimming, and resting his chin softly on your knee.'
        },
        {
            'name': 'Oliver', 'species': 'Cat', 'breed': 'Tabby', 'age_months': 18,
            'coat_color': 'Brown/Tan', 'size': 'Medium', 'energy_level': 4, 'trainability': 6, 'drive_level': 4,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.5, 'child_friendly_min_age': 0,
            'grooming_needed': 3, 'setup_budget_needed': 4, 'budget_needed': 4, 'sociability': 8,
            'adoption_fee': 75, 'length_of_stay_days': 8, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Sunbeam enthusiast and master biscuit maker. Chirps softly whenever you walk into the room and loves warm lap naps.'
        },
        {
            'name': 'Barnaby', 'species': 'Rabbit', 'breed': 'Holland Lop', 'age_months': 14,
            'coat_color': 'Brown/Tan', 'size': 'Small', 'energy_level': 4, 'trainability': 5, 'drive_level': 3,
            'space_needed': 2, 'yard_needed': 0, 'exercise_needed_hours': 0.5, 'child_friendly_min_age': 6,
            'grooming_needed': 4, 'setup_budget_needed': 4, 'budget_needed': 3, 'sociability': 7,
            'adoption_fee': 75, 'length_of_stay_days': 15, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Gentle senior rabbit surrendered due to landlord restrictions; loves dandelion greens, timothy hay, and soft head rubs.'
        },
        {
            'name': 'Sunny', 'species': 'Bird', 'breed': 'Cockatiel', 'age_months': 20,
            'coat_color': 'Emerald/Yellow', 'size': 'Small', 'energy_level': 5, 'trainability': 7, 'drive_level': 4,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.8, 'child_friendly_min_age': 8,
            'grooming_needed': 3, 'setup_budget_needed': 4, 'budget_needed': 3, 'sociability': 8,
            'adoption_fee': 30, 'length_of_stay_days': 10, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Friendly shoulder buddy who loves to whistle cheerful tunes, peek over your shoulder, and nibble on crisp apple slices.'
        },
        {
            'name': 'Pip & Squeak', 'species': 'Pocket Pet', 'breed': 'Guinea Pig', 'age_months': 12,
            'coat_color': 'Calico/Tricolor', 'size': 'Small', 'energy_level': 3, 'trainability': 4, 'drive_level': 2,
            'space_needed': 2, 'yard_needed': 0, 'exercise_needed_hours': 0.4, 'child_friendly_min_age': 5,
            'grooming_needed': 3, 'setup_budget_needed': 3, 'budget_needed': 3, 'sociability': 8,
            'adoption_fee': 25, 'length_of_stay_days': 9, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Inseparable, gentle pair who wheek with pure joy whenever the veggie container opens. Love fresh parsley and cozy fleece beds.'
        },
        {
            'name': 'Ziggy', 'species': 'Reptile', 'breed': 'Bearded Dragon', 'age_months': 22,
            'coat_color': 'Sandy/Orange', 'size': 'Medium', 'energy_level': 2, 'trainability': 4, 'drive_level': 2,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.3, 'child_friendly_min_age': 7,
            'grooming_needed': 2, 'setup_budget_needed': 7, 'budget_needed': 3, 'sociability': 6,
            'adoption_fee': 60, 'length_of_stay_days': 20, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Docile, gentle companion who loves basking under warm UVB, enjoying chin strokes, and snacking on fresh turnip greens.'
        },
        {
            'name': 'Thor', 'species': 'Dog', 'breed': 'Belgian Malinois', 'age_months': 24,
            'coat_color': 'Brown/Tan', 'size': 'Large', 'energy_level': 10, 'trainability': 9, 'drive_level': 10,
            'space_needed': 8, 'yard_needed': 3, 'exercise_needed_hours': 2.8, 'child_friendly_min_age': 10,
            'grooming_needed': 4, 'setup_budget_needed': 8, 'budget_needed': 8, 'sociability': 5,
            'adoption_fee': 220, 'length_of_stay_days': 28, 'is_high_risk': 0,
            'specialized_placement': 'WORKING_K9',
            'bio': 'High-drive working canine with sharp focus and boundless stamina. Thrives when given complex tasks, agility courses, or scent work.'
        },
        {
            'name': 'Shadow', 'species': 'Cat', 'breed': 'Domestic Shorthair', 'age_months': 30,
            'coat_color': 'Black', 'size': 'Medium', 'energy_level': 7, 'trainability': 5, 'drive_level': 9,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.8, 'child_friendly_min_age': 12,
            'grooming_needed': 2, 'setup_budget_needed': 4, 'budget_needed': 4, 'sociability': 3,
            'adoption_fee': 50, 'length_of_stay_days': 22, 'is_high_risk': 0,
            'specialized_placement': 'BARN_CAT',
            'bio': 'Independent, fierce working cat with high prey drive. Perfectly suited for safe barn or rural property rodent deterrence.'
        },
        {
            'name': 'Draco', 'species': 'Reptile', 'breed': 'Ball Python', 'age_months': 36,
            'coat_color': 'Spotted', 'size': 'Medium', 'energy_level': 2, 'trainability': 3, 'drive_level': 3,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.2, 'child_friendly_min_age': 8,
            'grooming_needed': 1, 'setup_budget_needed': 8, 'budget_needed': 4, 'sociability': 4,
            'adoption_fee': 70, 'length_of_stay_days': 35, 'is_high_risk': 1,
            'specialized_placement': 'EXOTIC_SPECIALIST',
            'bio': 'Healthy Ball Python requiring specialized humidity vivarium and experienced reptile handling foster care.'
        },
        {
            'name': 'Kiwi', 'species': 'Bird', 'breed': 'Green-Cheeked Conure', 'age_months': 28,
            'coat_color': 'Emerald/Yellow', 'size': 'Small', 'energy_level': 7, 'trainability': 8, 'drive_level': 6,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 1.2, 'child_friendly_min_age': 8,
            'grooming_needed': 3, 'setup_budget_needed': 7, 'budget_needed': 4, 'sociability': 6,
            'adoption_fee': 40, 'length_of_stay_days': 34, 'is_high_risk': 1,
            'specialized_placement': 'EXOTIC_SPECIALIST',
            'bio': 'Intelligent Conure needing experienced avian foster for dietary enrichment and positive reinforcement training.'
        },
        {
            'name': 'Cleo', 'species': 'Cat', 'breed': 'Siamese', 'age_months': 22,
            'coat_color': 'White', 'size': 'Medium', 'energy_level': 5, 'trainability': 7, 'drive_level': 5,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.5, 'child_friendly_min_age': 0,
            'grooming_needed': 2, 'setup_budget_needed': 4, 'budget_needed': 4, 'sociability': 9,
            'adoption_fee': 85, 'length_of_stay_days': 7, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Conversational, affectionate sweetheart who loves following you around the house and curling right into your lap.'
        },
        {
            'name': 'Rex', 'species': 'Dog', 'breed': 'German Shepherd', 'age_months': 20,
            'coat_color': 'Black', 'size': 'Large', 'energy_level': 9, 'trainability': 9, 'drive_level': 9,
            'space_needed': 8, 'yard_needed': 3, 'exercise_needed_hours': 2.5, 'child_friendly_min_age': 8,
            'grooming_needed': 5, 'setup_budget_needed': 7, 'budget_needed': 7, 'sociability': 6,
            'adoption_fee': 200, 'length_of_stay_days': 24, 'is_high_risk': 0,
            'specialized_placement': 'WORKING_K9',
            'bio': 'Sharp, loyal German Shepherd with intense focus and drive. Exceptional candidate for working K9 search and protection training.'
        },
        {
            'name': 'Clover', 'species': 'Rabbit', 'breed': 'Mini Rex', 'age_months': 16,
            'coat_color': 'Spotted', 'size': 'Small', 'energy_level': 4, 'trainability': 5, 'drive_level': 3,
            'space_needed': 2, 'yard_needed': 0, 'exercise_needed_hours': 0.5, 'child_friendly_min_age': 6,
            'grooming_needed': 3, 'setup_budget_needed': 4, 'budget_needed': 3, 'sociability': 7,
            'adoption_fee': 70, 'length_of_stay_days': 18, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Velvet-soft bundle of curiosity who loves cardboard tunnels, apple twigs, and sitting side-by-side for forehead strokes.'
        },
        {
            'name': 'Fudge', 'species': 'Pocket Pet', 'breed': 'Chinchilla', 'age_months': 18,
            'coat_color': 'Grey/Silver', 'size': 'Small', 'energy_level': 4, 'trainability': 4, 'drive_level': 2,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.5, 'child_friendly_min_age': 8,
            'grooming_needed': 4, 'setup_budget_needed': 5, 'budget_needed': 3, 'sociability': 6,
            'adoption_fee': 30, 'length_of_stay_days': 14, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Gentle evening companion with extraordinarily soft fur. Loves volcanic dust baths and nibbling safe apple wood sticks.'
        },
        {
            'name': 'Atlas', 'species': 'Reptile', 'breed': 'Russian Tortoise', 'age_months': 48,
            'coat_color': 'Sandy/Orange', 'size': 'Medium', 'energy_level': 2, 'trainability': 3, 'drive_level': 2,
            'space_needed': 3, 'yard_needed': 0, 'exercise_needed_hours': 0.3, 'child_friendly_min_age': 7,
            'grooming_needed': 1, 'setup_budget_needed': 6, 'budget_needed': 3, 'sociability': 5,
            'adoption_fee': 55, 'length_of_stay_days': 21, 'is_high_risk': 0,
            'specialized_placement': 'STANDARD_ADOPTION',
            'bio': 'Charming, calm herbivore with an inquisitive personality. Loves warm soaks, dandelion greens, and sunny garden strolls.'
        }
    ]

    data = []

    # Demo operational RFID tags
    demo_rfids = [
        'TAG_99A1001', 'TAG_99A1002', 'TAG_99A1003', 'TAG_99A1004', 'TAG_99A1005',
        'TAG_99A1006', 'TAG_99A1007', 'TAG_99A1008', 'TAG_99A1009', 'TAG_99A1010',
        'TAG_99A1011', 'TAG_99A1012', 'TAG_99A1013', 'TAG_99A1014', 'TAG_99A1015'
    ]

    for i in range(num_samples):
        animal_id = f"ANM-{1000 + i}"
        if i < len(demo_rfids):
            rfid_tag = demo_rfids[i]
        else:
            rfid_tag = f"TAG_{np.random.randint(1000000, 9999999):X}"

        # First use curated demo companions
        if i < len(curated_demo):
            item = dict(curated_demo[i])
            species = item['species']
            breed = item['breed']
            name = item['name']
            age_months = item['age_months']
            coat_color = item['coat_color']
            size = item['size']
            energy_level = item['energy_level']
            trainability = item['trainability']
            drive_level = item['drive_level']
            space_needed = item['space_needed']
            yard_needed = item['yard_needed']
            exercise_needed_hours = item['exercise_needed_hours']
            child_friendly_min_age = item['child_friendly_min_age']
            grooming_needed = item['grooming_needed']
            setup_budget_needed = item['setup_budget_needed']
            budget_needed = item['budget_needed']
            sociability = item['sociability']
            adoption_fee = item['adoption_fee']
            los_days = item['length_of_stay_days']
            is_high_risk = item['is_high_risk']
            specialized_placement = item['specialized_placement']
            bio = item['bio']
            surrender_history = 0
            special_medical_needs = 1 if specialized_placement == 'EXOTIC_SPECIALIST' else 0
            intake_season = np.random.choice(intake_seasons)
            shelter_capacity_utilization_pct = 70.0
            vocalization_level = 3
            separation_anxiety_risk = 2
            leash_reactivity_score = 2
            cat_friendly_score = 7
            dog_friendly_score = 7
        else:
            species = np.random.choice(species_list, p=species_probs)
            breed = np.random.choice(breeds_by_species[species])
            name = np.random.choice(names_by_species[species])
            coat_color = np.random.choice(colors)

            is_working_breed = (species == 'Dog' and breed in ['Belgian Malinois', 'German Shepherd', 'Border Collie', 'Boxer', 'Labrador Retriever'])

            if species == 'Dog':
                age_months = int(np.random.gamma(shape=2.4, scale=14)) + 2
                size = np.random.choice(['Small', 'Medium', 'Large', 'Extra Large'], p=[0.18, 0.35, 0.37, 0.10])
                space_needed = np.random.randint(4, 10)
                yard_needed = np.random.choice([1, 2, 3], p=[0.4, 0.45, 0.15])
                exercise_needed_hours = round(float(np.random.choice([1.0, 1.5, 2.0, 2.5, 3.0])), 1)
                adoption_fee = int(np.random.choice([150, 175, 190, 220, 250]))

                if is_working_breed and np.random.rand() > 0.40:
                    energy_level = np.random.choice([8, 9, 10])
                    trainability = np.random.choice([8, 9, 10])
                    drive_level = np.random.choice([8, 9, 10])
                else:
                    energy_level = np.random.randint(3, 9)
                    trainability = np.random.randint(3, 9)
                    drive_level = np.random.randint(2, 8)

                grooming_needed = np.random.randint(3, 8)
                budget_needed = np.random.randint(5, 8)
                setup_budget_needed = np.random.randint(5, 8)
                sociability = np.random.randint(4, 10)
                child_friendly_min_age = int(np.random.choice([0, 3, 6, 8], p=[0.35, 0.35, 0.2, 0.1]))

            elif species == 'Cat':
                age_months = int(np.random.gamma(shape=2.2, scale=12)) + 2
                size = np.random.choice(['Small', 'Medium', 'Large'], p=[0.25, 0.55, 0.20])
                space_needed = np.random.randint(2, 5)
                yard_needed = 0
                exercise_needed_hours = 0.5
                adoption_fee = int(np.random.choice([60, 70, 75, 85, 90]))
                
                # Barn cat potential
                if np.random.rand() < 0.08:
                    energy_level = np.random.randint(6, 9)
                    trainability = np.random.randint(3, 6)
                    drive_level = np.random.choice([7, 8, 9])
                    sociability = np.random.choice([2, 3, 4])
                else:
                    energy_level = np.random.randint(2, 7)
                    trainability = np.random.randint(3, 7)
                    drive_level = np.random.randint(2, 6)
                    sociability = np.random.randint(5, 10)

                grooming_needed = np.random.randint(2, 7)
                budget_needed = np.random.randint(3, 6)
                setup_budget_needed = np.random.randint(3, 5)
                child_friendly_min_age = int(np.random.choice([0, 3, 5], p=[0.5, 0.35, 0.15]))

            elif species == 'Rabbit':
                age_months = int(np.random.gamma(shape=2.0, scale=9)) + 3
                size = np.random.choice(['Small', 'Medium'], p=[0.75, 0.25])
                space_needed = np.random.randint(2, 4)
                yard_needed = 0
                exercise_needed_hours = 0.5
                adoption_fee = int(np.random.choice([60, 70, 75, 80]))
                energy_level = np.random.randint(3, 6)
                trainability = np.random.randint(3, 6)
                drive_level = np.random.randint(1, 4)
                grooming_needed = np.random.randint(3, 5)
                budget_needed = np.random.randint(3, 5)
                setup_budget_needed = np.random.randint(3, 5)
                sociability = np.random.randint(5, 8)
                child_friendly_min_age = int(np.random.choice([5, 6, 8], p=[0.4, 0.4, 0.2]))

            elif species == 'Bird':
                age_months = int(np.random.gamma(shape=2.2, scale=10)) + 4
                size = np.random.choice(['Small', 'Medium'], p=[0.85, 0.15])
                space_needed = np.random.randint(2, 4)
                yard_needed = 0
                exercise_needed_hours = 0.8
                adoption_fee = int(np.random.choice([20, 25, 30, 35]))
                energy_level = np.random.randint(4, 8)
                trainability = np.random.randint(5, 9)
                drive_level = np.random.randint(2, 5)
                grooming_needed = np.random.randint(2, 4)
                budget_needed = np.random.randint(2, 4)
                setup_budget_needed = np.random.randint(4, 7)
                sociability = np.random.randint(5, 9)
                child_friendly_min_age = 8 if breed in ['Finch', 'Budgerigar/Parakeet'] else 6

            elif species == 'Pocket Pet':
                age_months = int(np.random.randint(3, 30))
                size = 'Small'
                space_needed = np.random.randint(1, 3)
                yard_needed = 0
                exercise_needed_hours = 0.4
                adoption_fee = int(np.random.choice([15, 20, 25, 30]))
                energy_level = np.random.randint(2, 5)
                trainability = np.random.randint(2, 5)
                drive_level = np.random.randint(1, 3)
                grooming_needed = np.random.randint(1, 4)
                budget_needed = np.random.randint(2, 4)
                setup_budget_needed = np.random.randint(2, 5)
                sociability = np.random.randint(5, 8)
                # Fragility based min age
                child_friendly_min_age = 5 if breed == 'Guinea Pig' else (8 if breed in ['Syrian Hamster', 'Fancy Rat'] else 10)

            else:  # Reptile
                age_months = int(np.random.randint(6, 48))
                size = np.random.choice(['Small', 'Medium'], p=[0.6, 0.4])
                space_needed = np.random.randint(2, 4)
                yard_needed = 0
                exercise_needed_hours = 0.3
                adoption_fee = int(np.random.choice([40, 50, 60, 75]))
                energy_level = np.random.randint(1, 4)
                trainability = np.random.randint(2, 4)
                drive_level = np.random.randint(1, 3)
                grooming_needed = 1
                budget_needed = np.random.randint(2, 4)
                setup_budget_needed = np.random.randint(6, 9)  # vivarium, UVB, thermostat
                sociability = np.random.randint(3, 7)
                child_friendly_min_age = int(np.random.choice([7, 8, 10], p=[0.5, 0.3, 0.2]))

            bio = np.random.choice(bios_by_species[species])
            vocalization_level = np.random.randint(1, 8)
            separation_anxiety_risk = np.random.randint(1, 7) if species in ['Dog', 'Cat'] else 1
            leash_reactivity_score = np.random.randint(1, 8) if species == 'Dog' else 1
            cat_friendly_score = np.random.randint(3, 9)
            dog_friendly_score = np.random.randint(3, 9)

            surrender_history = int(np.random.choice([0, 1], p=[0.8, 0.2]))
            special_medical_needs = int(np.random.choice([0, 1, 2], p=[0.78, 0.18, 0.04]))
            shelter_capacity_utilization_pct = round(float(np.random.uniform(45.0, 92.0)), 1)
            intake_season = np.random.choice(intake_seasons)

            # Grounded Length of Stay (LOS) risk calculation
            risk_points = 0.0
            # Age factor
            if species in ['Dog', 'Cat'] and age_months >= 72:
                risk_points += 2.5
            elif species == 'Rabbit' and age_months >= 48:
                risk_points += 2.0
            elif species == 'Pocket Pet' and age_months >= 24:
                risk_points += 2.0
            elif species == 'Reptile' and age_months >= 48:
                risk_points += 1.5

            if size in ['Large', 'Extra Large'] and species == 'Dog':
                risk_points += 1.0

            # Medical factor
            if special_medical_needs == 2:
                risk_points += 3.5
            elif special_medical_needs == 1:
                risk_points += 1.8

            if surrender_history == 1:
                risk_points += 2.5

            # Specialized vivarium / habitat equipment barrier
            if species in ['Reptile', 'Bird'] and setup_budget_needed >= 7:
                risk_points += 1.5

            if separation_anxiety_risk >= 7:
                risk_points += 2.0
            if leash_reactivity_score >= 8:
                risk_points += 2.0
            if energy_level >= 9 and trainability <= 4 and species == 'Dog':
                risk_points += 2.5

            if shelter_capacity_utilization_pct >= 85.0:
                risk_points += 1.2

            is_high_risk = 1 if (risk_points >= 4.5 or (surrender_history == 1 and special_medical_needs >= 1)) else 0

            if is_high_risk:
                los_days = int(np.random.uniform(30, 80))
            else:
                los_days = int(np.random.uniform(3, 27))

            # Specialized Placement Routing Evaluation
            if species == 'Dog' and energy_level >= 8 and trainability >= 8 and drive_level >= 8:
                specialized_placement = 'WORKING_K9'
            elif species == 'Cat' and drive_level >= 7 and sociability <= 4:
                specialized_placement = 'BARN_CAT'
            elif species in ['Reptile', 'Bird'] and (special_medical_needs >= 1 or setup_budget_needed >= 7):
                specialized_placement = 'EXOTIC_SPECIALIST'
            else:
                specialized_placement = 'STANDARD_ADOPTION'

        is_sar_candidate = 1 if specialized_placement == 'WORKING_K9' else 0

        if specialized_placement == 'WORKING_K9':
            status = 'WORKING_K9_PLACEMENT'
        elif specialized_placement == 'BARN_CAT':
            status = 'BARN_CAT_PLACEMENT'
        elif specialized_placement == 'EXOTIC_SPECIALIST':
            status = 'EXOTIC_SPECIALIST_PLACEMENT'
        elif is_high_risk:
            status = 'CARE_TRIAGE_PRIORITY'
        else:
            status = 'AVAILABLE'

        data.append({
            'id': animal_id,
            'rfid_tag': rfid_tag,
            'name': f"{name} ({animal_id})",
            'species': species,
            'breed': breed,
            'age_months': age_months,
            'coat_color': coat_color,
            'size': size,
            'energy_level': energy_level,
            'trainability': trainability,
            'drive_level': drive_level,
            'vocalization_level': vocalization_level,
            'separation_anxiety_risk': separation_anxiety_risk,
            'leash_reactivity_score': leash_reactivity_score,
            'cat_friendly_score': cat_friendly_score,
            'dog_friendly_score': dog_friendly_score,
            'space_needed': space_needed,
            'yard_needed': yard_needed,
            'exercise_needed_hours': exercise_needed_hours,
            'child_friendly_min_age': child_friendly_min_age,
            'grooming_needed': grooming_needed,
            'setup_budget_needed': setup_budget_needed,
            'budget_needed': budget_needed,
            'sociability': sociability,
            'surrender_history': surrender_history,
            'special_medical_needs': special_medical_needs,
            'shelter_capacity_utilization_pct': shelter_capacity_utilization_pct,
            'intake_season': intake_season,
            'length_of_stay_days': los_days,
            'is_high_risk': is_high_risk,
            'is_sar_candidate': is_sar_candidate,
            'specialized_placement': specialized_placement,
            'status': status,
            'adoption_fee': adoption_fee,
            'bio': bio,
            'personality_bio': bio
        })

    df = pd.DataFrame(data)

    # Save primary dataset CSV
    os.makedirs(os.path.dirname(Config.CSV_DATA_PATH), exist_ok=True)
    df.to_csv(Config.CSV_DATA_PATH, index=False)

    # Save dedicated real shelter dataset copy
    dataset_copy_path = os.path.join(os.path.dirname(Config.CSV_DATA_PATH), 'real_shelter_dataset.csv')
    df.to_csv(dataset_copy_path, index=False)
    print(f"Generated multi-species shelter dataset with {len(df)} records at {Config.CSV_DATA_PATH} and {dataset_copy_path}")

    # Seed SQLite Database
    conn = sqlite3.connect(Config.DATABASE_PATH)
    df.to_sql('animals', conn, if_exists='replace', index=False)
    conn.close()
    print(f"Seeded SQLite database at {Config.DATABASE_PATH}")
    return df


if __name__ == '__main__':
    generate_shelter_dataset()
