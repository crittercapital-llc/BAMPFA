"""
data/fetch_all_reviews.py
─────────────────────────
One-time (and periodic refresh) script to pull ALL BAMPFA Google reviews
via SerpAPI and save to data/google_reviews_live.csv.

Usage:
    # Full pull (first time — fetches everything, ~90 API calls)
    python data/fetch_all_reviews.py

    # Incremental refresh (only reviews newer than last CSV entry)
    python data/fetch_all_reviews.py --incremental

Requirements:
    pip install requests python-dotenv

SerpAPI free tier: 100 searches/month.
A full pull of ~903 reviews uses ~91 searches. Run once, then use
--incremental for monthly top-ups (~2-5 searches).
"""

import argparse
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

BAMPFA_LUDOCID = "16873726739869704312"
OUTPUT_PATH = Path(__file__).parent / "google_reviews_live.csv"
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")

# Polite delay between pages so we don't hammer the API
DELAY_SECONDS = 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_page(next_page_token: str | None = None) -> dict:
    params = {
        "engine": "google_maps_reviews",
        "ludocid": BAMPFA_LUDOCID,
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "sort_by": "newestFirst",
    }
    if next_page_token:
        params["next_page_token"] = next_page_token

    resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def parse_reviews(data: dict) -> list[dict]:
    rows = []
    for r in data.get("reviews", []):
        iso_date = r.get("iso_date") or r.get("date", "")
        try:
            date = pd.Timestamp(iso_date)
        except Exception:
            date = pd.NaT

        user = r.get("user", {})
        author = user.get("name", "Anonymous") if isinstance(user, dict) else "Anonymous"

        rows.append({
            "date":   date,
            "rating": int(r.get("rating", 3)),
            "text":   r.get("snippet", "") or r.get("text", ""),
            "author": author,
            "source": "serpapi_google_reviews",
        })
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only fetch reviews newer than the latest date already in the CSV",
    )
    args = parser.parse_args()

    if not SERPAPI_KEY:
        raise SystemExit("❌  SERPAPI_KEY not set. Add it to your .env file.")

    # Load existing CSV if present
    existing_df = pd.DataFrame()
    latest_existing_date = None

    if OUTPUT_PATH.exists():
        existing_df = pd.read_csv(OUTPUT_PATH, parse_dates=["date"])
        if not existing_df.empty and "date" in existing_df.columns:
            latest_existing_date = existing_df["date"].max()
            print(f"📂  Existing CSV: {len(existing_df):,} reviews, latest date: {latest_existing_date.date()}")

    if args.incremental and latest_existing_date is None:
        print("⚠️  --incremental requested but no existing CSV found. Running full pull instead.")
        args.incremental = False

    # Fetch pages
    all_rows = []
    page_num = 0
    next_page_token = None
    stop_early = False

    print(f"\n{'🔄 Incremental' if args.incremental else '📥 Full'} pull starting…\n")

    while True:
        page_num += 1
        print(f"  Fetching page {page_num}…", end=" ", flush=True)

        try:
            data = fetch_page(next_page_token)
        except requests.HTTPError as e:
            print(f"\n❌  HTTP error on page {page_num}: {e}")
            break
        except Exception as e:
            print(f"\n❌  Error on page {page_num}: {e}")
            break

        rows = parse_reviews(data)
        if not rows:
            print("no reviews — done.")
            break

        # In incremental mode, stop when we reach reviews we already have
        if args.incremental and latest_existing_date is not None:
            filtered = []
            for row in rows:
                if pd.notna(row["date"]) and row["date"] > latest_existing_date:
                    filtered.append(row)
                else:
                    stop_early = True
            rows = filtered
            if stop_early and not rows:
                print(f"reached existing data — stopping.")
                break

        all_rows.extend(rows)
        print(f"got {len(rows)} reviews (total so far: {len(all_rows):,})")

        next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
        if not next_page_token:
            print(f"\n✅  No more pages.")
            break

        if stop_early:
            break

        time.sleep(DELAY_SECONDS)

    if not all_rows:
        print("\nℹ️  No new reviews fetched.")
        return

    new_df = pd.DataFrame(all_rows)
    new_df["date"] = pd.to_datetime(new_df["date"], errors="coerce")

    # Merge with existing if incremental
    if args.incremental and not existing_df.empty:
        combined = pd.concat([new_df, existing_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date", "author", "text"])
    else:
        combined = new_df

    combined = combined.sort_values("date", ascending=False).reset_index(drop=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    print(f"\n💾  Saved {len(combined):,} total reviews → {OUTPUT_PATH}")
    print(f"    New reviews added: {len(new_df):,}")
    print(f"    Date range: {combined['date'].min().date()} → {combined['date'].max().date()}")
    print(f"\n🔑  API calls used this run: ~{page_num}")


if __name__ == "__main__":
    main()
