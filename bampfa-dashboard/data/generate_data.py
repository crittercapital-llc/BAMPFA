"""
generate_data.py
Generates realistic dummy data CSVs for the BAMPFA audience analytics dashboard.
Run standalone: python data/generate_data.py

TODO: Replace with live Tesitura CRM export or API pull when available.
"""

import os
import random
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Shared reference data
# ---------------------------------------------------------------------------

ART_EXHIBITIONS = [
    "Defne Ayas: Threshold",
    "Bay Area Now 9",
    "Jockum Nordström: The Lonely Ones",
    "Theaster Gates: Black Image Corporation",
    "Mildred Howard: Room Tone",
    "Radical Presence: Black Performance in Contemporary Art",
    "Tauba Auerbach: S v Z",
    "Hung Liu: Portraits of Promised Lands",
    "Ant Farm: 1968–1978",
    "Uncanny Valley: Being Human in the Age of AI",
    "Paper, Scissors, Stone: Contemporary Japanese Prints",
    "Gordon Matta-Clark: Anarchitect",
    "Dorothea Lange: Politics of Seeing",
    "Barry McGee: Point the Finger",
    "Ana Mendieta: Traces",
]

FILM_TITLES = [
    "Jeanne Dielman, 23 quai du Commerce",
    "Yi Yi (A One and a Two)",
    "Beau Travail",
    "Platform (Zhantai)",
    "Mulholland Drive",
    "In the Mood for Love",
    "Tropical Malady",
    "Cache (Hidden)",
    "The Assassin",
    "Synonyms",
    "First Cow",
    "Portrait of a Lady on Fire",
    "The Worst Person in the World",
    "Drive My Car",
    "Aftersun",
    "Decision to Leave",
    "The Zone of Interest",
    "Past Lives",
    "All of Us Strangers",
    "A Brighter Summer Day",
]

# Bay Area zip codes weighted toward Berkeley/Oakland
BAY_AREA_ZIPS = (
    ["94704", "94705", "94703", "94702", "94709", "94710", "94720"] * 20  # Berkeley heavy
    + ["94601", "94602", "94609", "94611", "94618", "94619", "94606"] * 15  # Oakland
    + ["94107", "94110", "94117", "94103", "94118", "94122", "94114"] * 8   # SF
    + ["94501", "94502", "94608", "94612"] * 5                              # Alameda/nearby
    + ["94530", "94804", "94806"] * 3                                       # Richmond
    + ["94550", "94551", "94560"] * 2                                       # Livermore/Newark
    + ["95008", "95014", "94025"] * 2                                       # South Bay/Peninsula
    + ["94901", "94920", "94930"] * 1                                       # Marin
)

ACQUISITION_CHANNELS = ["At Door", "Online", "Event", "Gift", "Email Campaign"]
MEMBERSHIP_TIERS = ["Individual", "Dual", "Family", "Patron", "Benefactor"]
TIER_WEIGHTS = [0.40, 0.25, 0.15, 0.12, 0.08]

REVIEW_SOURCES = ["Google", "Yelp"]
REVIEW_TEMPLATES = [
    "Wonderful museum in the heart of Berkeley. The {exhibition} show was breathtaking.",
    "BAMPFA always delivers. Saw {film} here — stunning print on the big screen.",
    "Love this place. Staff are knowledgeable and the space feels intimate yet grand.",
    "The {exhibition} exhibition challenged me in the best way. Will be back next month.",
    "Great film programming. Caught a rare 35mm screening of {film}. Pure cinema magic.",
    "A gem of the Bay Area arts scene. Every visit feels special.",
    "Membership is absolutely worth it. Always something new and thought-provoking.",
    "The gallery spaces are beautifully curated. {exhibition} was my favorite show this year.",
    "Solid programming but parking is tough. The content more than makes up for it.",
    "One of the best film archives on the West Coast. {film} on the big screen was a dream.",
    "Arrived late and missed the intro talk, but the exhibition itself was extraordinary.",
    "Good variety of art and film. {exhibition} was a bit dense but rewarding.",
    "A little pricey but the quality is always there. Loved the {film} screening.",
    "Friendly staff, accessible space. The free First Thursday events are a great touch.",
    "Not my usual style of art but {exhibition} really opened my mind. Impressive curation.",
]


# ---------------------------------------------------------------------------
# Seasonality weight: peaks Oct–Nov and Feb–Mar, dip in summer
# ---------------------------------------------------------------------------

MONTH_WEIGHTS = {
    1: 0.80, 2: 1.15, 3: 1.20, 4: 1.00,
    5: 0.85, 6: 0.75, 7: 0.65, 8: 0.70,
    9: 0.90, 10: 1.30, 11: 1.25, 12: 0.95,
}


def season_scale(dt: date) -> float:
    return MONTH_WEIGHTS.get(dt.month, 1.0)


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


# ---------------------------------------------------------------------------
# 1. transactions.csv
# ---------------------------------------------------------------------------

def generate_transactions() -> pd.DataFrame:
    print("Generating transactions.csv ...")
    start_date = date(2022, 1, 1)
    end_date = date(2026, 4, 30)

    total_target = 40_000
    patron_pool = list(range(1, 8001))

    # Pre-assign ~1200 patrons as members (consistent with members.csv)
    member_patron_ids = set(random.sample(patron_pool, 1200))

    records = []
    generated = 0

    all_dates = list(date_range(start_date, end_date))
    # Weight dates by seasonality
    date_weights = [season_scale(d) * (0.3 if d.weekday() >= 5 else 0.14) for d in all_dates]
    total_weight = sum(date_weights)
    date_probs = [w / total_weight for w in date_weights]

    # Sample event dates
    event_dates_sample = np.random.choice(
        len(all_dates), size=total_target, p=date_probs
    )

    for idx in event_dates_sample:
        event_dt = all_dates[idx]

        # Category split: 40% Art, 60% Film
        category = "Art" if random.random() < 0.40 else "Film"
        if category == "Art":
            event_name = random.choice(ART_EXHIBITIONS)
            gallery = random.choice(["G1", "G2"])
        else:
            event_name = random.choice(FILM_TITLES)
            gallery = random.choice(["Cinema", "Outdoor"]) if event_dt.month in [6, 7, 8] else "Cinema"

        patron_id = random.choice(patron_pool)
        is_member = patron_id in member_patron_ids

        # Ticket type
        if is_member:
            ticket_type = "Member"
        else:
            r = random.random()
            if r < 0.30:
                ticket_type = "General"
            elif r < 0.55:
                ticket_type = "Student"
            elif r < 0.70:
                ticket_type = "Senior"
            else:
                ticket_type = "Free"

        # Ticket price
        if ticket_type == "Free":
            ticket_price = 0.0
        elif ticket_type == "Member":
            ticket_price = round(random.uniform(0, 12), 2)
        elif ticket_type == "Student":
            ticket_price = round(random.uniform(8, 14), 2)
        elif ticket_type == "Senior":
            ticket_price = round(random.uniform(10, 16), 2)
        else:  # General
            ticket_price = round(random.uniform(14, 25), 2)

        quantity = random.choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.15, 0.05])[0]

        # Channel: ~65% online
        channel = "Online" if random.random() < 0.65 else "Onsite"

        # Purchase lead days: members buy earlier
        if is_member:
            lead = int(np.random.exponential(12))
        elif channel == "Online":
            lead = int(np.random.exponential(7))
        else:
            lead = int(np.random.exponential(2))
        lead = min(lead, 90)

        purchase_dt = event_dt - timedelta(days=lead)
        if purchase_dt < start_date:
            purchase_dt = start_date

        zip_code = random.choice(BAY_AREA_ZIPS)

        records.append({
            "transaction_id": str(uuid.uuid4()),
            "patron_id": patron_id,
            "transaction_date": purchase_dt.isoformat(),
            "event_date": event_dt.isoformat(),
            "event_name": event_name,
            "event_category": category,
            "gallery": gallery,
            "ticket_type": ticket_type,
            "ticket_price": ticket_price,
            "quantity": quantity,
            "channel": channel,
            "zip_code": zip_code,
            "is_member": is_member,
            "purchase_lead_days": lead,
        })

        generated += 1

    df = pd.DataFrame(records)
    out = os.path.join(OUTPUT_DIR, "transactions.csv")
    df.to_csv(out, index=False)
    print(f"  -> {len(df):,} rows written to {out}")
    return df


# ---------------------------------------------------------------------------
# 2. members.csv
# ---------------------------------------------------------------------------

def generate_members() -> pd.DataFrame:
    print("Generating members.csv ...")
    start_date = date(2022, 1, 1)
    end_date = date(2026, 4, 30)
    n = 1200

    patron_ids = random.sample(range(1, 8001), n)
    records = []

    for pid in patron_ids:
        # Join date skewed toward earlier years (more members joined before 2024)
        days_range = (end_date - start_date).days
        join_offset = int(np.random.beta(1.5, 3) * days_range)
        join_dt = start_date + timedelta(days=join_offset)

        # ~30% lapsed
        lapsed = random.random() < 0.30
        if lapsed:
            lapse_offset = random.randint(90, (end_date - join_dt).days)
            lapse_dt = join_dt + timedelta(days=min(lapse_offset, (end_date - join_dt).days))
            lapse_date = lapse_dt.isoformat()
            last_active = lapse_dt
        else:
            lapse_date = None
            last_active = end_date - timedelta(days=random.randint(0, 60))

        tier = random.choices(MEMBERSHIP_TIERS, weights=TIER_WEIGHTS)[0]
        total_visits = random.randint(1, 40)
        acq = random.choices(
            ACQUISITION_CHANNELS,
            weights=[0.20, 0.35, 0.25, 0.10, 0.10]
        )[0]

        records.append({
            "patron_id": pid,
            "join_date": join_dt.isoformat(),
            "lapse_date": lapse_date,
            "membership_tier": tier,
            "total_visits": total_visits,
            "last_visit_date": last_active.isoformat(),
            "acquisition_channel": acq,
        })

    df = pd.DataFrame(records)
    out = os.path.join(OUTPUT_DIR, "members.csv")
    df.to_csv(out, index=False)
    print(f"  -> {len(df):,} rows written to {out}")
    return df


# ---------------------------------------------------------------------------
# 3. web_traffic.csv
# ---------------------------------------------------------------------------

def generate_web_traffic() -> pd.DataFrame:
    print("Generating web_traffic.csv ...")
    start_date = date(2022, 1, 1)
    end_date = date(2026, 4, 30)
    sources = ["Organic Search", "Social", "Direct", "Email", "Paid"]
    source_weights = [0.35, 0.22, 0.25, 0.10, 0.08]

    records = []
    for d in date_range(start_date, end_date):
        scale = season_scale(d)
        # Weekends get more traffic
        weekend_boost = 1.3 if d.weekday() >= 5 else 1.0
        base_sessions = int(np.random.normal(350, 60) * scale * weekend_boost)
        base_sessions = max(80, base_sessions)

        for source in sources:
            sw = source_weights[sources.index(source)]
            sessions = max(5, int(base_sessions * sw * np.random.normal(1, 0.12)))
            users = max(3, int(sessions * random.uniform(0.72, 0.90)))
            page_views = int(sessions * random.uniform(2.5, 4.5))
            exh_pv = int(page_views * random.uniform(0.18, 0.32) * scale)
            film_pv = int(page_views * random.uniform(0.22, 0.38) * scale)
            mem_pv = int(page_views * random.uniform(0.05, 0.14))
            avg_dur = max(30, int(np.random.normal(185, 45)))

            records.append({
                "date": d.isoformat(),
                "sessions": sessions,
                "users": users,
                "page_views": page_views,
                "source": source,
                "exhibition_page_views": exh_pv,
                "film_page_views": film_pv,
                "membership_page_views": mem_pv,
                "avg_session_duration_seconds": avg_dur,
            })

    df = pd.DataFrame(records)
    out = os.path.join(OUTPUT_DIR, "web_traffic.csv")
    df.to_csv(out, index=False)
    print(f"  -> {len(df):,} rows written to {out}")
    return df


# ---------------------------------------------------------------------------
# 4. reviews.csv
# ---------------------------------------------------------------------------

def generate_reviews() -> pd.DataFrame:
    print("Generating reviews.csv ...")
    start_date = date(2022, 1, 1)
    end_date = date(2026, 4, 30)
    n = 800

    all_dates = list(date_range(start_date, end_date))
    date_weights = [season_scale(d) for d in all_dates]
    total_w = sum(date_weights)
    date_probs = [w / total_w for w in date_weights]
    chosen_indices = np.random.choice(len(all_dates), size=n, p=date_probs)

    records = []
    for idx in chosen_indices:
        d = all_dates[idx]

        # Rating: skewed positive, avg ~4.2
        rating = int(np.random.choice([1, 2, 3, 4, 5], p=[0.03, 0.05, 0.10, 0.32, 0.50]))
        if rating >= 4:
            sentiment = "Positive"
        elif rating == 3:
            sentiment = "Neutral"
        else:
            sentiment = "Negative"

        source = random.choices(REVIEW_SOURCES, weights=[0.65, 0.35])[0]

        template = random.choice(REVIEW_TEMPLATES)
        text = template.format(
            exhibition=random.choice(ART_EXHIBITIONS),
            film=random.choice(FILM_TITLES),
        )

        records.append({
            "date": d.isoformat(),
            "rating": rating,
            "sentiment": sentiment,
            "source": source,
            "text": text,
        })

    df = pd.DataFrame(records)
    df = df.sort_values("date").reset_index(drop=True)
    out = os.path.join(OUTPUT_DIR, "reviews.csv")
    df.to_csv(out, index=False)
    print(f"  -> {len(df):,} rows written to {out}")
    return df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    generate_transactions()
    generate_members()
    generate_web_traffic()
    generate_reviews()
    print("\nAll data files generated successfully.")
