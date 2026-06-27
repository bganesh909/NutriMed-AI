"""Input validation utilities for NutriMed AI."""

import re
from typing import Optional


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """Validate password strength. Returns (is_valid, error_message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, None


def sanitize_filename(filename: str) -> str:
    """Sanitize uploaded filename to prevent path traversal."""
    filename = filename.replace("\\", "/")
    filename = filename.split("/")[-1]
    filename = re.sub(r"[^\w\s\-.]", "", filename)
    filename = filename.strip()
    if not filename:
        filename = "unnamed_file"
    return filename


def validate_biomarker_value(name: str, value: float) -> bool:
    """Check if a biomarker value is within plausible range (not reference range)."""
    plausible_ranges = {
        "hemoglobin": (1.0, 25.0),
        "vitamin_d": (1.0, 200.0),
        "vitamin_b12": (50.0, 5000.0),
        "ldl": (10.0, 500.0),
        "hdl": (5.0, 150.0),
        "triglycerides": (20.0, 2000.0),
        "fasting_sugar": (20.0, 600.0),
        "hba1c": (2.0, 20.0),
        "creatinine": (0.1, 20.0),
        "tsh": (0.01, 100.0),
        "sgpt": (1.0, 5000.0),
        "sgot": (1.0, 5000.0),
        "iron": (5.0, 500.0),
        "calcium": (4.0, 16.0),
        "urea": (5.0, 300.0),
        "uric_acid": (1.0, 20.0),
    }
    if name in plausible_ranges:
        low, high = plausible_ranges[name]
        return low <= value <= high
    return True
