#!/usr/bin/env python3
"""
Seed script for NutriMed AI.

Loads sample users, biomarkers, and medical profiles into MongoDB.
Hashes passwords with bcrypt, creates proper indexes, and links
documents via user_id / report_id references.

Usage:
    python seed_data.py                  # uses defaults (localhost:27017)
    MONGO_URI=mongodb://... python seed_data.py

Requirements:
    pip install motor passlib[bcrypt]
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "nutrimed_ai")

SEEDS_DIR = Path(__file__).parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(filename: str) -> list:
    with open(SEEDS_DIR / filename, "r") as f:
        return json.load(f)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Index creation
# ---------------------------------------------------------------------------


async def create_indexes(db):
    """Create indexes for all collections."""
    print("Creating indexes...")

    # Users
    await db["users"].create_index("email", unique=True)
    await db["users"].create_index("role")

    # Reports
    await db["reports"].create_index("user_id")
    await db["reports"].create_index([("user_id", 1), ("uploaded_at", -1)])
    await db["reports"].create_index("status")

    # Biomarkers
    await db["biomarkers"].create_index("user_id")
    await db["biomarkers"].create_index("report_id", unique=True)
    await db["biomarkers"].create_index([("user_id", 1), ("extracted_at", -1)])

    # Medical profiles
    await db["medical_profiles"].create_index("user_id", unique=True)

    # Diet plans
    await db["diet_plans"].create_index("user_id")
    await db["diet_plans"].create_index([("user_id", 1), ("created_at", -1)])

    # Workout plans
    await db["workout_plans"].create_index("user_id")
    await db["workout_plans"].create_index([("user_id", 1), ("created_at", -1)])

    # Recommendations
    await db["recommendations"].create_index("user_id")
    await db["recommendations"].create_index([("user_id", 1), ("created_at", -1)])
    await db["recommendations"].create_index("biomarker_id")

    # Progress
    await db["progress"].create_index("user_id")
    await db["progress"].create_index([("user_id", 1), ("date", -1)])

    # Audit logs
    await db["audit_logs"].create_index("user_id")
    await db["audit_logs"].create_index("timestamp")

    print("  Indexes created successfully.")


# ---------------------------------------------------------------------------
# Seed users
# ---------------------------------------------------------------------------


async def seed_users(db) -> dict[str, str]:
    """Seed users and return a mapping of email -> inserted user_id."""
    print("Seeding users...")
    users_data = load_json("seed_users.json")
    email_to_id: dict[str, str] = {}

    for user in users_data:
        existing = await db["users"].find_one({"email": user["email"]})
        if existing:
            email_to_id[user["email"]] = str(existing["_id"])
            print(f"  Skipped (exists): {user['email']}")
            continue

        doc = {
            "name": user["name"],
            "email": user["email"],
            "hashed_password": pwd_context.hash(user["password"]),
            "age": user.get("age"),
            "gender": user.get("gender"),
            "weight": user.get("weight"),
            "height": user.get("height"),
            "activity_level": user.get("activity_level"),
            "goals": user.get("goals", []),
            "role": user.get("role", "user"),
            "created_at": now_utc(),
            "updated_at": now_utc(),
        }
        result = await db["users"].insert_one(doc)
        user_id = str(result.inserted_id)
        email_to_id[user["email"]] = user_id
        print(f"  Created: {user['email']} (id={user_id})")

    return email_to_id


# ---------------------------------------------------------------------------
# Seed biomarkers (with stub reports)
# ---------------------------------------------------------------------------


async def seed_biomarkers(db, email_to_id: dict[str, str]) -> None:
    """Seed biomarker data. Creates a stub report for each biomarker set."""
    print("Seeding biomarkers...")
    biomarkers_data = load_json("seed_biomarkers.json")

    for entry in biomarkers_data:
        user_email = entry["user_email"]
        user_id = email_to_id.get(user_email)
        if not user_id:
            print(f"  Skipped biomarker for unknown user: {user_email}")
            continue

        # Check if biomarkers already exist for this user
        existing = await db["biomarkers"].find_one({"user_id": user_id})
        if existing:
            print(f"  Skipped (exists): biomarkers for {user_email}")
            continue

        # Create a stub report
        report_doc = {
            "user_id": user_id,
            "report_type": entry.get("report_type", "CBC"),
            "file_path": f"/uploads/seed_{user_email.split('@')[0]}_report.pdf",
            "original_filename": f"seed_{user_email.split('@')[0]}_report.pdf",
            "status": "completed",
            "uploaded_at": now_utc(),
            "processed_at": now_utc(),
        }
        report_result = await db["reports"].insert_one(report_doc)
        report_id = str(report_result.inserted_id)

        # Create biomarker document
        markers = entry["markers"]
        biomarker_doc = {
            "user_id": user_id,
            "report_id": report_id,
            "extracted_at": now_utc(),
        }
        # Set each marker as a top-level field
        for marker_name, value in markers.items():
            biomarker_doc[marker_name] = value

        await db["biomarkers"].insert_one(biomarker_doc)
        print(f"  Created: biomarkers for {user_email} ({len(markers)} markers)")


# ---------------------------------------------------------------------------
# Seed medical profiles
# ---------------------------------------------------------------------------


async def seed_medical_profiles(db, email_to_id: dict[str, str]) -> None:
    """Seed medical profiles."""
    print("Seeding medical profiles...")
    profiles_data = load_json("seed_medical_profiles.json")

    for profile in profiles_data:
        user_email = profile["user_email"]
        user_id = email_to_id.get(user_email)
        if not user_id:
            print(f"  Skipped profile for unknown user: {user_email}")
            continue

        existing = await db["medical_profiles"].find_one({"user_id": user_id})
        if existing:
            print(f"  Skipped (exists): profile for {user_email}")
            continue

        doc = {
            "user_id": user_id,
            "blood_type": profile.get("blood_type"),
            "allergies": profile.get("allergies", []),
            "chronic_conditions": profile.get("chronic_conditions", []),
            "medications": profile.get("medications", []),
            "surgeries": profile.get("surgeries", []),
            "family_history": profile.get("family_history", []),
            "dietary_restrictions": profile.get("dietary_restrictions", []),
            "notes": profile.get("notes", ""),
            "created_at": now_utc(),
            "updated_at": now_utc(),
        }
        await db["medical_profiles"].insert_one(doc)
        print(f"  Created: profile for {user_email}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main():
    print(f"Connecting to MongoDB at {MONGO_URI} ...")
    client = AsyncIOMotorClient(MONGO_URI)

    # Verify connection
    try:
        await client.admin.command("ping")
        print("  Connected successfully.")
    except Exception as e:
        print(f"  Failed to connect: {e}")
        sys.exit(1)

    db = client[MONGO_DB_NAME]
    print(f"Using database: {MONGO_DB_NAME}\n")

    await create_indexes(db)
    print()

    email_to_id = await seed_users(db)
    print()

    await seed_biomarkers(db, email_to_id)
    print()

    await seed_medical_profiles(db, email_to_id)
    print()

    print("Seed complete!")
    print(f"  Users: {await db['users'].count_documents({})}")
    print(f"  Reports: {await db['reports'].count_documents({})}")
    print(f"  Biomarkers: {await db['biomarkers'].count_documents({})}")
    print(f"  Medical Profiles: {await db['medical_profiles'].count_documents({})}")

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
