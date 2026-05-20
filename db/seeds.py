"""
Seeds file for YourCoolingPartner
Run this to populate the database with sample data.
Usage: python -m db.seeds
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, Base, engine, User, Job, Bid, Booking, Conversation, Message
from auth.auth import get_password_hash

def seed():
    print("=" * 55)
    print("  🌱 YourCoolingPartner — Database Seeder")
    print("=" * 55)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    print("\n🧹 Truncating tables (except users)...")
    db.query(Message).delete()
    db.query(Conversation).delete()
    db.query(Booking).delete()
    db.query(Bid).delete()
    db.query(Job).delete()
    db.commit()

    # ------------------------------------------
    # Seed Users
    # ------------------------------------------
    print("\n👤 Inserting Users...")

    users_data = [
        {"name": "Ahmed Khan",     "mobile_number": "03001234567", "role": "user",       "password": "password123"},
        {"name": "Sara Malik",     "mobile_number": "03011234567", "role": "user",       "password": "password123"},
        {"name": "Usman Ali",      "mobile_number": "03021234567", "role": "technician", "password": "tech123"},
        {"name": "Bilal AC Wala",  "mobile_number": "03031234567", "role": "technician", "password": "tech123"},
        {"name": "Kamran Cooling", "mobile_number": "03041234567", "role": "technician", "password": "tech123"},
    ]

    db_users = []
    for u in users_data:
        existing = db.query(User).filter(User.mobile_number == u["mobile_number"]).first()
        if not existing:
            user = User(
                name=u["name"],
                mobile_number=u["mobile_number"],
                role=u["role"],
                hashed_password=get_password_hash(u["password"])
            )
            db.add(user)
            db_users.append(user)
        else:
            db_users.append(existing)

    db.commit()
    for u in db_users:
        db.refresh(u)
        print(f"   ✅ User #{u.id}: {u.name} ({u.role}) — Mobile: {u.mobile_number}")

    db.close()

    # ------------------------------------------
    # Summary
    # ------------------------------------------
    print("\n" + "=" * 55)
    print(f"  🎉 Seeding Complete!")
    print(f"     Users: {len(users_data)}")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    seed()
