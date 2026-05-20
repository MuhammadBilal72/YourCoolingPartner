"""
Test Agent: Fetch technicians from Google Maps and seed into database.

Fetches up to 500 AC / repair technicians near a given area using the
Google Places API (New), then inserts them as 'technician' users in the
local database.  Skips businesses that have no phone number.  Logs every
insertion with the full User object.

Usage:
    python -m agent.test_agent --intent "AC Repair" --city Lahore --town "Johar Town" --limit 500

Dependencies:
    - .env file with GOOGLE_MAPS_API_KEY
    - Database tables must exist (run `python -m db.seeds` first if needed)
"""

import argparse
import os
import sys
import time

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from db.database import SessionLocal, User
from auth.auth import get_password_hash

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
DEFAULT_PASSWORD = "tech123"


def fetch_businesses(
    intent: str,
    city: str,
    town: str,
    limit: int = 500,
) -> list[dict]:
    """
    Fetch businesses from Google Places API (New) using multiple related
    search queries and pagination to reach the requested limit.
    """
    if not GOOGLE_MAPS_API_KEY:
        print("   ❌ GOOGLE_MAPS_API_KEY not found in .env")
        return []

    search_queries = [
        f"{intent} in {town}, {city}",
        f"{intent} near {town}, {city}",
        f"{intent} {town} {city}",
        f"AC technician {town} {city}",
        f"AC repair shop {town} {city}",
        f"air conditioner service {town} {city}",
        f"HVAC repair {town} {city}",
        f"refrigeration service {town} {city}",
        f"cooling repair {town} {city}",
        f"AC parts and service {town} {city}",
    ]

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_MAPS_API_KEY,
        "X-Goog-FieldMask": (
            "places.id,places.displayName,places.nationalPhoneNumber,"
            "places.formattedAddress,places.location,places.rating,nextPageToken"
        ),
    }

    all_businesses: list[dict] = []
    seen_place_ids: set[str] = set()

    for query in search_queries:
        if len(all_businesses) >= limit:
            break

        print(f"\n🔍 Searching: \"{query}\"")
        page_token = None
        page_count = 0

        while len(all_businesses) < limit:
            url = "https://places.googleapis.com/v1/places:searchText"
            payload: dict = {"textQuery": query, "pageSize": 20}
            if page_token:
                payload["pageToken"] = page_token

            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                print(f"   ❌ API error on page {page_count + 1}: {e}")
                break

            places = data.get("places", [])
            if not places:
                print("   ⚠️  No more places returned")
                break

            for place in places:
                pid = place.get("id")
                if pid and pid in seen_place_ids:
                    continue
                if pid:
                    seen_place_ids.add(pid)
                all_businesses.append(place)

            page_count += 1
            print(
                f"   📄 Page {page_count}: +{len(places)} places "
                f"(total unique: {len(all_businesses)})"
            )

            page_token = data.get("nextPageToken")
            if not page_token:
                print("   ✅ No more pages available")
                break

            time.sleep(0.5)

        print(f"   ➡️  Finished query, running total: {len(all_businesses)}")

    return all_businesses[:limit]


def seed_technicians(businesses: list[dict]) -> int:
    """Insert businesses as technician users. Skips records without a phone."""
    db = SessionLocal()
    inserted = 0
    skipped_no_phone = 0
    skipped_duplicate = 0

    for biz in businesses:
        name = (biz.get("displayName") or {}).get("text", "").strip()
        phone = (biz.get("nationalPhoneNumber") or "").strip()
        address = (biz.get("formattedAddress") or "").strip()
        loc = biz.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")

        if not name:
            continue

        if not phone:
            print(f"   ⏭️  Skipping '{name}' — No phone number")
            skipped_no_phone += 1
            continue

        existing = db.query(User).filter(User.mobile_number == phone).first()
        if existing:
            print(
                f"   ⏭️  Skipping '{name}' — Phone already exists "
                f"(User #{existing.id})"
            )
            skipped_duplicate += 1
            continue

        location_str = (
            f"{lat},{lng}" if lat is not None and lng is not None else None
        )

        user = User(
            name=name,
            mobile_number=phone,
            role="technician",
            hashed_password=get_password_hash(DEFAULT_PASSWORD),
            location=location_str,
            address=address,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"   ✅ Inserting business : {user}")
        inserted += 1

    db.close()

    print(
        f"\n📊 Summary: {inserted} inserted, "
        f"{skipped_no_phone} skipped (no phone), "
        f"{skipped_duplicate} skipped (duplicate)"
    )
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch technicians from Google Maps and seed into database"
    )
    parser.add_argument(
        "--intent",
        default="AC Repair",
        help="Service type to search for (default: 'AC Repair')",
    )
    parser.add_argument(
        "--city",
        default="Lahore",
        help="City name (default: 'Lahore')",
    )
    parser.add_argument(
        "--town",
        default="Johar Town",
        help="Town / area name (default: 'Johar Town')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of businesses to fetch (default: 500)",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help="Default password for all seeded technician accounts",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("  🔧 YourCoolingPartner — Test Agent: Fetch & Seed Technicians")
    print("=" * 60)
    print(f"\n📋 Search Parameters:")
    print(f"   Intent : {args.intent}")
    print(f"   City   : {args.city}")
    print(f"   Town   : {args.town}")
    print(f"   Limit  : {args.limit}")

    businesses = fetch_businesses(args.intent, args.city, args.town, args.limit)

    print(f"\n📦 Total businesses fetched from API: {len(businesses)}")

    if not businesses:
        print("\n❌ No businesses to seed. Exiting.")
        return

    inserted = seed_technicians(businesses)

    print(f"\n🎉 Done! {inserted} technicians added to the users table.")


if __name__ == "__main__":
    main()
