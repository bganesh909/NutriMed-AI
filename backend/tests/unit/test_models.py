"""
Unit tests for Pydantic models: UserModel, BiomarkerModel, ReportModel,
MedicalProfileModel, ProgressModel.

Covers creation, validation, to_dict, from_dict.
"""

from datetime import date, datetime, timezone

import pytest

from app.models.user import ActivityLevel, Gender, UserModel, UserRole
from app.models.biomarker import BiomarkerModel
from app.models.report import ReportModel, ReportStatus, ReportType
from app.models.medical_profile import MedicalProfileModel
from app.models.progress import ProgressModel


# ---------------------------------------------------------------------------
# UserModel
# ---------------------------------------------------------------------------


class TestUserModel:
    def test_create_minimal(self):
        user = UserModel(
            name="Alice",
            email="alice@example.com",
            hashed_password="$2b$12$xxx",
        )
        assert user.name == "Alice"
        assert user.role == UserRole.USER
        assert user.goals == []
        assert user.age is None

    def test_create_full(self):
        user = UserModel(
            name="Bob",
            email="bob@example.com",
            hashed_password="$2b$12$xxx",
            age=28,
            gender=Gender.MALE,
            weight=75.0,
            height=175.0,
            activity_level=ActivityLevel.MODERATELY_ACTIVE,
            goals=["muscle_gain"],
            role=UserRole.ADMIN,
        )
        assert user.age == 28
        assert user.gender == "male"
        assert user.activity_level == "moderately_active"
        assert user.role == "admin"

    def test_to_dict_excludes_id(self):
        user = UserModel(
            name="Charlie",
            email="c@test.com",
            hashed_password="hash",
        )
        d = user.to_dict()
        assert "id" not in d
        assert "name" in d
        assert "email" in d

    def test_from_dict_with_mongo_id(self):
        doc = {
            "_id": "64a1b2c3d4e5f6a7b8c9d0e1",
            "name": "Dave",
            "email": "dave@test.com",
            "hashed_password": "hash",
            "role": "user",
        }
        user = UserModel.from_dict(doc)
        assert user.id == "64a1b2c3d4e5f6a7b8c9d0e1"
        assert user.name == "Dave"

    def test_from_dict_without_id(self):
        doc = {
            "name": "Eve",
            "email": "eve@test.com",
            "hashed_password": "hash",
        }
        user = UserModel.from_dict(doc)
        assert user.id is None

    def test_enum_values_serialized_as_strings(self):
        user = UserModel(
            name="F",
            email="f@test.com",
            hashed_password="h",
            gender=Gender.FEMALE,
        )
        d = user.to_dict()
        assert d["gender"] == "female"


# ---------------------------------------------------------------------------
# BiomarkerModel
# ---------------------------------------------------------------------------


class TestBiomarkerModel:
    def test_create_minimal(self):
        bio = BiomarkerModel(user_id="u1", report_id="r1")
        assert bio.hemoglobin is None
        assert bio.vitamin_d is None

    def test_create_with_values(self):
        bio = BiomarkerModel(
            user_id="u1",
            report_id="r1",
            hemoglobin=14.5,
            vitamin_d=25.0,
            ldl=120.0,
            fasting_sugar=95.0,
        )
        assert bio.hemoglobin == 14.5
        assert bio.vitamin_d == 25.0

    def test_to_dict(self):
        bio = BiomarkerModel(user_id="u1", report_id="r1", hemoglobin=14.5)
        d = bio.to_dict()
        assert "id" not in d
        assert d["hemoglobin"] == 14.5
        assert d["user_id"] == "u1"

    def test_from_dict(self):
        doc = {
            "_id": "abc123",
            "user_id": "u1",
            "report_id": "r1",
            "tsh": 3.5,
        }
        bio = BiomarkerModel.from_dict(doc)
        assert bio.id == "abc123"
        assert bio.tsh == 3.5


# ---------------------------------------------------------------------------
# ReportModel
# ---------------------------------------------------------------------------


class TestReportModel:
    def test_create(self):
        report = ReportModel(
            user_id="u1",
            report_type=ReportType.CBC,
            file_path="/uploads/test.pdf",
            original_filename="test.pdf",
        )
        assert report.status == "uploaded"
        assert report.report_type == "CBC"

    def test_all_report_types(self):
        for rt in ReportType:
            report = ReportModel(
                user_id="u1",
                report_type=rt,
                file_path="/test",
                original_filename="x",
            )
            assert report.report_type == rt.value

    def test_status_transitions(self):
        for s in ReportStatus:
            report = ReportModel(
                user_id="u1",
                report_type=ReportType.LIPID,
                file_path="/test",
                original_filename="x",
                status=s,
            )
            assert report.status == s.value

    def test_to_dict(self):
        report = ReportModel(
            user_id="u1",
            report_type=ReportType.CBC,
            file_path="/test",
            original_filename="cbc.pdf",
        )
        d = report.to_dict()
        assert "id" not in d
        assert d["report_type"] == "CBC"

    def test_from_dict(self):
        doc = {
            "_id": "rpt123",
            "user_id": "u1",
            "report_type": "CBC",
            "file_path": "/test",
            "original_filename": "cbc.pdf",
            "status": "completed",
        }
        report = ReportModel.from_dict(doc)
        assert report.id == "rpt123"
        assert report.status == "completed"


# ---------------------------------------------------------------------------
# MedicalProfileModel
# ---------------------------------------------------------------------------


class TestMedicalProfileModel:
    def test_create_minimal(self):
        profile = MedicalProfileModel(user_id="u1")
        assert profile.conditions == []
        assert profile.allergies == []
        assert profile.medications == []

    def test_create_full(self):
        profile = MedicalProfileModel(
            user_id="u1",
            conditions=["type_2_diabetes", "hypertension"],
            allergies=["penicillin"],
            injuries=["lower_back"],
            medications=["metformin"],
        )
        assert len(profile.conditions) == 2
        assert "penicillin" in profile.allergies

    def test_to_dict(self):
        profile = MedicalProfileModel(
            user_id="u1",
            conditions=["asthma"],
        )
        d = profile.to_dict()
        assert "id" not in d
        assert d["conditions"] == ["asthma"]

    def test_from_dict(self):
        doc = {
            "_id": "mp123",
            "user_id": "u1",
            "conditions": ["hypertension"],
            "allergies": [],
            "injuries": [],
            "medications": ["lisinopril"],
        }
        profile = MedicalProfileModel.from_dict(doc)
        assert profile.id == "mp123"
        assert profile.medications == ["lisinopril"]


# ---------------------------------------------------------------------------
# ProgressModel
# ---------------------------------------------------------------------------


class TestProgressModel:
    def test_create_minimal(self):
        prog = ProgressModel(user_id="u1")
        assert prog.weight is None
        assert prog.notes == ""
        assert prog.measurements == {}

    def test_create_full(self):
        prog = ProgressModel(
            user_id="u1",
            date=date(2026, 6, 1),
            weight=74.5,
            body_fat_pct=18.5,
            measurements={"waist": 82.0, "chest": 100.0},
            biomarker_snapshot={"hemoglobin": 14.5},
            notes="Feeling good",
        )
        assert prog.weight == 74.5
        assert prog.measurements["waist"] == 82.0

    def test_to_dict_serializes_date(self):
        prog = ProgressModel(
            user_id="u1",
            date=date(2026, 6, 15),
            weight=75.0,
        )
        d = prog.to_dict()
        assert d["date"] == "2026-06-15"
        assert "id" not in d

    def test_from_dict(self):
        doc = {
            "_id": "prog123",
            "user_id": "u1",
            "date": "2026-06-15",
            "weight": 75.0,
            "body_fat_pct": None,
            "measurements": {},
            "biomarker_snapshot": {},
            "notes": "",
        }
        prog = ProgressModel.from_dict(doc)
        assert prog.id == "prog123"
        assert prog.weight == 75.0
