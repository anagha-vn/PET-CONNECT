#!/usr/bin/env python3
"""
Real-World Multi-Species Animal Shelter Dataset Fetcher
PET CONNECT Platform - AI Machine Learning Pipeline
Location: data/fetch_real_datasets.py

Fetches real-world shelter intake, outcome, and length-of-stay (LOS) data from
government open data portals using public Socrata and OpenDataSoft REST APIs.
Requires ZERO external API keys.

Supported Data Sources:
1. Austin Animal Center (AAC) - Socrata API (data.austintexas.gov)
2. Sonoma County Animal Services - Socrata API (data.sonomacounty.ca.gov)
3. Long Beach Animal Care Services - OpenDataSoft API (data.longbeach.gov)
"""

import os
import sys
import argparse
import urllib.request
import urllib.parse
import json
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


def fetch_json(url, timeout=25):
    """Fetches JSON from public URL using standard urllib with User-Agent header."""
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'PetConnect-Shelter-AI-Research/1.0 (Academic/OpenData Research)'}
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or 'utf-8'
        return json.loads(response.read().decode(charset))


def parse_age_to_months(age_str):
    """Converts strings like '2 years', '3 months', '4 weeks', '2 days' into integer months."""
    if not age_str or not isinstance(age_str, str):
        return 24
    age_str = age_str.strip().lower()
    parts = age_str.split()
    if len(parts) >= 2:
        try:
            val = float(parts[0])
            unit = parts[1]
            if 'year' in unit:
                return max(1, int(val * 12))
            elif 'month' in unit:
                return max(1, int(val))
            elif 'week' in unit:
                return max(1, int(val / 4.3))
            elif 'day' in unit:
                return 1
        except ValueError:
            pass
    return 24


def get_season(dt):
    """Determines season from datetime object."""
    if not dt:
        return 'Standard'
    m = dt.month
    if m in [3, 4, 5]:
        return 'Spring Peak'
    elif m in [6, 7, 8]:
        return 'Summer High'
    elif m in [9, 10, 11]:
        return 'Fall Moderate'
    else:
        return 'Winter Standard'


def fetch_austin_dataset(limit=500):
    """
    Fetches completed Outcome records from Austin Animal Center,
    then joins with matching Intakes to calculate ground-truth Length of Stay (LOS).
    """
    print(f"[Austin Animal Center] Fetching {limit} completed outcome records...")
    outcomes_url = (
        f"https://data.austintexas.gov/resource/9t4d-g238.json?"
        f"$order=datetime%20DESC&$limit={limit}"
    )
    try:
        outcomes_data = fetch_json(outcomes_url)
    except Exception as e:
        print(f"[-] Error querying Austin outcomes: {e}")
        return []

    if not outcomes_data:
        print("[-] No outcome records retrieved from Austin.")
        return []

    animal_ids = list({row['animal_id'] for row in outcomes_data if 'animal_id' in row})
    print(f"[Austin Animal Center] Retrieved {len(outcomes_data)} outcomes ({len(animal_ids)} unique animals).")

    # Fetch corresponding intake records in batches of 50
    chunk_size = 50
    intakes_by_id = {}
    for i in range(0, len(animal_ids), chunk_size):
        chunk = animal_ids[i:i + chunk_size]
        ids_quoted = ",".join([f"'{aid}'" for aid in chunk])
        intakes_url = (
            f"https://data.austintexas.gov/resource/wter-evkm.json?"
            f"$where=animal_id%20in({urllib.parse.quote(ids_quoted)})&$limit={chunk_size * 2}"
        )
        try:
            chunk_intakes = fetch_json(intakes_url)
            for row in chunk_intakes:
                aid = row.get('animal_id')
                if aid and aid not in intakes_by_id:
                    intakes_by_id[aid] = row
        except Exception as e:
            print(f"[-] Warning: Failed intake chunk query: {e}")

    print(f"[Austin Animal Center] Successfully matched {len(intakes_by_id)} intake histories.")

    records = []
    for out in outcomes_data:
        aid = out.get('animal_id')
        in_row = intakes_by_id.get(aid)
        if not in_row:
            continue

        in_dt_str = in_row.get('datetime', '')
        out_dt_str = out.get('datetime', '')
        
        try:
            in_dt = datetime.fromisoformat(in_dt_str.replace('Z', '+00:00'))
            out_dt = datetime.fromisoformat(out_dt_str.replace('Z', '+00:00'))
            if in_dt.tzinfo and not out_dt.tzinfo:
                in_dt = in_dt.replace(tzinfo=None)
            elif out_dt.tzinfo and not in_dt.tzinfo:
                out_dt = out_dt.replace(tzinfo=None)
            
            los_days = round((out_dt - in_dt).total_seconds() / (24 * 3600), 2)
            if los_days < 0:
                continue
            los_days = max(0.1, los_days)
        except Exception:
            continue

        raw_species = in_row.get('animal_type', 'Other').title()
        breed = in_row.get('breed', 'Unknown')
        
        if raw_species == 'Other':
            b_lower = breed.lower()
            if 'rabbit' in b_lower:
                species = 'Rabbit'
            elif any(r in b_lower for r in ['guinea pig', 'hamster', 'gerbil', 'mouse', 'rat', 'ferret']):
                species = 'Small Animal'
            elif any(r in b_lower for r in ['turtle', 'tortoise', 'snake', 'lizard', 'iguana', 'gecko']):
                species = 'Reptile'
            elif any(w in b_lower for w in ['bat', 'raccoon', 'opossum', 'skunk', 'squirrel', 'fox']):
                species = 'Wildlife'
            else:
                species = 'Other'
        else:
            species = raw_species

        age_months = parse_age_to_months(in_row.get('age_upon_intake', ''))

        rec = {
            'source_portal': 'Austin Animal Center',
            'id': aid,
            'species': species,
            'breed': breed,
            'color': in_row.get('color', 'Unknown'),
            'sex': in_row.get('sex_upon_intake', 'Unknown'),
            'size': 'Standard',
            'age_months': age_months,
            'intake_date': in_dt_str,
            'outcome_date': out_dt_str,
            'intake_type': in_row.get('intake_type', 'Stray'),
            'intake_condition': in_row.get('intake_condition', 'Normal'),
            'outcome_type': out.get('outcome_type', 'Unknown'),
            'outcome_subtype': out.get('outcome_subtype', ''),
            'length_of_stay_days': los_days,
            'is_high_risk': 1 if los_days >= 30 else 0,
            'intake_season': get_season(in_dt)
        }
        records.append(rec)

    return records


def fetch_sonoma_dataset(limit=500):
    """
    Fetches multi-species records from Sonoma County Animal Shelter.
    Pre-calculated `days_in_shelter` provides ground-truth LOS.
    """
    print(f"[Sonoma County] Fetching {limit} multi-species records...")
    url = (
        f"https://data.sonomacounty.ca.gov/resource/924a-vesw.json?"
        f"$where=days_in_shelter%20is%20not%20null&$limit={limit}"
    )
    try:
        data = fetch_json(url)
    except Exception as e:
        print(f"[-] Error fetching Sonoma County data: {e}")
        return []

    records = []
    for row in data:
        try:
            los_days = float(row.get('days_in_shelter', 0))
        except (ValueError, TypeError):
            continue

        raw_type = row.get('type', 'OTHER').upper()
        breed = row.get('breed', 'Unknown').title()
        
        if raw_type == 'DOG':
            species = 'Dog'
        elif raw_type == 'CAT':
            species = 'Cat'
        else:
            b_lower = breed.lower()
            if 'rabbit' in b_lower:
                species = 'Rabbit'
            elif any(b in b_lower for b in ['chicken', 'parakeet', 'pigeon', 'duck', 'goose', 'peafowl', 'bird']):
                species = 'Bird'
            elif any(b in b_lower for b in ['guinea pig', 'rat', 'mouse', 'hamster']):
                species = 'Small Animal'
            elif any(b in b_lower for b in ['goat', 'sheep', 'horse', 'pig', 'livestock']):
                species = 'Livestock'
            elif any(b in b_lower for b in ['bat', 'wildlife']):
                species = 'Wildlife'
            elif any(b in b_lower for b in ['snake', 'turtle', 'tortoise', 'lizard']):
                species = 'Reptile'
            else:
                species = 'Other'

        size_raw = row.get('size', 'MED').upper()
        size_map = {'SML': 'Small', 'MED': 'Medium', 'LRG': 'Large', 'PUP': 'Small', 'KITTN': 'Small'}
        size = size_map.get(size_raw, 'Medium')

        in_dt_str = row.get('intake_date', '')
        in_dt = None
        if in_dt_str:
            try:
                in_dt = datetime.fromisoformat(in_dt_str.replace('Z', '+00:00'))
            except Exception:
                pass

        rec = {
            'source_portal': 'Sonoma County Shelter',
            'id': row.get('id', row.get('impound_number', 'N/A')),
            'species': species,
            'breed': breed,
            'color': row.get('color', 'Unknown').title(),
            'sex': row.get('sex', 'Unknown'),
            'size': size,
            'age_months': 24,
            'intake_date': in_dt_str,
            'outcome_date': row.get('outcome_date', ''),
            'intake_type': row.get('intake_type', 'STRAY').title(),
            'intake_condition': row.get('intake_condition', 'UNKNOWN').title(),
            'outcome_type': row.get('outcome_type', 'UNKNOWN').title(),
            'outcome_subtype': row.get('outcome_subtype', '').title(),
            'length_of_stay_days': max(0.1, los_days),
            'is_high_risk': 1 if los_days >= 30 else 0,
            'intake_season': get_season(in_dt) if in_dt else 'Standard'
        }
        records.append(rec)

    print(f"[Sonoma County] Processed {len(records)} verified records.")
    return records


def fetch_longbeach_dataset(limit=500):
    """
    Fetches records from Long Beach Animal Care Services via OpenDataSoft v2 API.
    Provides `intake_duration` (Length of Stay in days).
    OpenDataSoft caps per-request limit at 100, so we paginate using offset.
    """
    print(f"[Long Beach Animal Care] Fetching {limit} multi-species records...")
    raw_records = []
    fetched = 0
    batch_size = min(100, limit)

    while fetched < limit:
        req_limit = min(batch_size, limit - fetched)
        url = (
            f"https://data.longbeach.gov/api/v2/catalog/datasets/"
            f"animal-shelter-intakes-and-outcomes/records?limit={req_limit}&offset={fetched}"
        )
        try:
            res = fetch_json(url)
            batch = res.get('records', [])
            if not batch:
                break
            raw_records.extend(batch)
            fetched += len(batch)
        except Exception as e:
            print(f"[-] Error fetching Long Beach data at offset {fetched}: {e}")
            break

    records = []
    for r in raw_records:
        f = r.get('record', {}).get('fields', {})
        try:
            los_days = float(f.get('intake_duration', 0))
        except (ValueError, TypeError):
            continue

        raw_type = f.get('animal_type', 'OTHER').upper()
        if raw_type == 'DOG':
            species = 'Dog'
        elif raw_type == 'CAT':
            species = 'Cat'
        elif raw_type == 'RABBIT':
            species = 'Rabbit'
        elif raw_type == 'BIRD':
            species = 'Bird'
        elif raw_type == 'REPTILE':
            species = 'Reptile'
        elif raw_type == 'GUINEA PIG':
            species = 'Small Animal'
        elif raw_type == 'LIVESTOCK':
            species = 'Livestock'
        elif raw_type == 'WILD':
            species = 'Wildlife'
        else:
            species = 'Other'

        in_dt_str = f.get('intake_date', '')
        in_dt = None
        if in_dt_str:
            try:
                in_dt = datetime.strptime(in_dt_str, '%Y-%m-%d')
            except Exception:
                pass

        rec = {
            'source_portal': 'Long Beach Animal Care',
            'id': f.get('animal_id', 'N/A'),
            'species': species,
            'breed': 'Mixed/Domestic',
            'color': f.get('primary_color', 'Unknown').title(),
            'sex': f.get('sex', 'Unknown'),
            'size': 'Standard',
            'age_months': 24,
            'intake_date': in_dt_str,
            'outcome_date': f.get('outcome_date', ''),
            'intake_type': f.get('intake_type', 'STRAY').title(),
            'intake_condition': f.get('intake_cond', 'NORMAL').title(),
            'outcome_type': f.get('outcome_type', 'UNKNOWN').title(),
            'outcome_subtype': f.get('outcome_subtype', '').title(),
            'length_of_stay_days': max(0.1, los_days),
            'is_high_risk': 1 if los_days >= 30 else 0,
            'intake_season': get_season(in_dt) if in_dt else 'Standard'
        }
        records.append(rec)

    print(f"[Long Beach Animal Care] Processed {len(records)} verified records.")
    return records


def main():
    parser = argparse.ArgumentParser(description="Fetch real multi-species animal shelter data from public APIs.")
    parser.add_argument('--source', choices=['austin', 'sonoma', 'longbeach', 'all'], default='all',
                        help="Data source to query (default: all)")
    parser.add_argument('--limit', type=int, default=300,
                        help="Number of records to fetch per source (default: 300)")
    parser.add_argument('--output', type=str, default=os.path.join(os.path.dirname(__file__), 'real_shelter_multispecies_sample.csv'),
                        help="Output path for CSV dataset")
    args = parser.parse_args()

    all_records = []
    
    if args.source in ['austin', 'all']:
        all_records.extend(fetch_austin_dataset(limit=args.limit))
        
    if args.source in ['sonoma', 'all']:
        all_records.extend(fetch_sonoma_dataset(limit=args.limit))

    if args.source in ['longbeach', 'all']:
        all_records.extend(fetch_longbeach_dataset(limit=args.limit))

    if not all_records:
        print("[-] No records fetched. Check internet connectivity or parameters.")
        sys.exit(1)

    print(f"\n=======================================================")
    print(f"Total verified real-world records fetched: {len(all_records)}")
    print(f"=======================================================")

    if HAS_PANDAS:
        df = pd.DataFrame(all_records)
        df.to_csv(args.output, index=False)
        print(f"\nSaved clean dataset to: {args.output}")
        print("\n--- Species Distribution ---")
        print(df['species'].value_counts())
        print("\n--- Length of Stay (LOS Days) by Species ---")
        print(df.groupby('species')['length_of_stay_days'].agg(['count', 'median', 'mean']).round(1))
        print("\n--- Risk Distribution (High Risk >= 30 Days) ---")
        risk_pct = (df['is_high_risk'].sum() / len(df)) * 100
        print(f"High-Risk Shelter Stay Rate: {risk_pct:.1f}% ({df['is_high_risk'].sum()}/{len(df)} animals)")
    else:
        import csv
        keys = all_records[0].keys()
        with open(args.output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(all_records)
        print(f"\nSaved clean dataset to: {args.output} (written via csv stdlib)")

    print(f"\nFetcher finished successfully!")


if __name__ == '__main__':
    main()
