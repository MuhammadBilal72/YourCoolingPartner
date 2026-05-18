"""
Seeds file for YourCoolingPartner
Run this to populate the database with sample users, jobs, bids, and bookings.
Usage: python -m db.seeds
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.database import SessionLocal, Base, engine, User, Job, Bid, Booking
from auth.auth import get_password_hash

def seed():
    # Recreate tables
    print("=" * 55)
    print("  🌱 YourCoolingPartner — Database Seeder")
    print("=" * 55)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # ------------------------------------------
    # Clear existing data
    # ------------------------------------------
    print("\n🗑️  Clearing existing data...")
    db.query(Booking).delete()
    db.query(Bid).delete()
    db.query(Job).delete()
    db.query(User).delete()
    db.commit()
    print("   ✅ All tables cleared.\n")

    # ------------------------------------------
    # Seed Users
    # ------------------------------------------
    print("👤 Inserting Users...")

    users_data = [
        {"name": "Ahmed Khan",     "mobile_number": "03001234567", "role": "user",       "password": "password123"},
        {"name": "Sara Malik",     "mobile_number": "03011234567", "role": "user",       "password": "password123"},
        {"name": "Usman Ali",      "mobile_number": "03021234567", "role": "technician", "password": "tech123"},
        {"name": "Bilal AC Wala",  "mobile_number": "03031234567", "role": "technician", "password": "tech123"},
        {"name": "Kamran Cooling", "mobile_number": "03041234567", "role": "technician", "password": "tech123"},
    ]

    db_users = []
    for u in users_data:
        user = User(
            name=u["name"],
            mobile_number=u["mobile_number"],
            role=u["role"],
            hashed_password=get_password_hash(u["password"])
        )
        db.add(user)
        db_users.append(user)

    db.commit()
    for u in db_users:
        db.refresh(u)
        print(f"   ✅ User #{u.id}: {u.name} ({u.role}) — Mobile: {u.mobile_number}")

    # ------------------------------------------
    # Seed Jobs
    # ------------------------------------------
    print("\n📋 Inserting Jobs...")

    jobs_data = [
        {"user_id": db_users[0].id, "city": "Lahore",    "town": "Johar Town",  "status": "pending",    "date": "2026-05-20", "time": "10:00 AM"},
        {"user_id": db_users[0].id, "city": "Lahore",    "town": "Gulberg",     "status": "pending",    "date": "2026-05-21", "time": "02:00 PM"},
        {"user_id": db_users[1].id, "city": "Karachi",   "town": "DHA Phase 5", "status": "pending",    "date": "2026-05-22", "time": "11:00 AM"},
        {"user_id": db_users[1].id, "city": "Islamabad", "town": "F-8",         "status": "completed",  "date": "2026-05-15", "time": "09:00 AM"},
    ]

    db_jobs = []
    for j in jobs_data:
        job = Job(**j)
        db.add(job)
        db_jobs.append(job)

    db.commit()
    for j in db_jobs:
        db.refresh(j)
        print(f"   ✅ Job #{j.id}: {j.town}, {j.city} — Status: {j.status}")

    # ------------------------------------------
    # Seed Bids
    # ------------------------------------------
    print("\n💰 Inserting Bids...")

    bids_data = [
        {"job_id": db_jobs[0].id, "technician_id": db_users[2].id, "amount": 3500.0},
        {"job_id": db_jobs[0].id, "technician_id": db_users[3].id, "amount": 3000.0},
        {"job_id": db_jobs[0].id, "technician_id": db_users[4].id, "amount": 4000.0},
        {"job_id": db_jobs[1].id, "technician_id": db_users[3].id, "amount": 2500.0},
        {"job_id": db_jobs[2].id, "technician_id": db_users[4].id, "amount": 5000.0},
    ]

    db_bids = []
    for b in bids_data:
        bid = Bid(**b)
        db.add(bid)
        db_bids.append(bid)

    db.commit()
    for b in db_bids:
        db.refresh(b)
        tech = db.query(User).filter(User.id == b.technician_id).first()
        print(f"   ✅ Bid #{b.id}: {tech.name} bid Rs.{b.amount} on Job #{b.job_id}")

    # ------------------------------------------
    # Seed Bookings
    # ------------------------------------------
    print("\n📅 Inserting Bookings...")

    bookings_data = [
        {"technician_id": db_users[2].id, "user_id": db_users[1].id, "date": "2026-05-15", "time": "09:00 AM", "amount": 4500.0},
    ]

    for bk in bookings_data:
        booking = Booking(**bk)
        db.add(booking)

    db.commit()
    # Refresh and log
    bookings = db.query(Booking).all()
    for bk in bookings:
        tech = db.query(User).filter(User.id == bk.technician_id).first()
        user = db.query(User).filter(User.id == bk.user_id).first()
        print(f"   ✅ Booking #{bk.id}: {tech.name} booked by {user.name} — Rs.{bk.amount}")

    db.close()

    # ------------------------------------------
    # Summary
    # ------------------------------------------
    print("\n" + "=" * 55)
    print(f"  🎉 Seeding Complete!")
    print(f"     Users: {len(users_data)}")
    print(f"     Jobs: {len(jobs_data)}")
    print(f"     Bids: {len(bids_data)}")
    print(f"     Bookings: {len(bookings_data)}")
    print("=" * 55 + "\n")

if __name__ == "__main__":
    seed()
