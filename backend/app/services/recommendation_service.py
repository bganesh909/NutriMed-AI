"""
Recommendation service -- orchestrates lab interpretation, nutrition, and fitness
into a unified recommendation, including non-prescription supplement suggestions.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status

from app.repositories.biomarker_repository import BiomarkerRepository
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.user_repository import UserRepository
from app.services.lab_interpretation_service import LabInterpretationService
from app.services.nutrition_service import NutritionService
from app.services.fitness_service import FitnessService


# Non-prescription supplement suggestions based on deficiency/risk labels
_SUPPLEMENT_MAP: dict[str, dict] = {
    "Vitamin D deficiency": {
        "name": "Vitamin D3",
        "dosage": "1000-2000 IU daily",
        "notes": "Take with a fat-containing meal for better absorption.",
        "prescription_required": False,
    },
    "Vitamin D insufficiency": {
        "name": "Vitamin D3",
        "dosage": "1000 IU daily",
        "notes": "Maintain adequate sun exposure alongside supplementation.",
        "prescription_required": False,
    },
    "Vitamin B12 deficiency": {
        "name": "Vitamin B12 (Methylcobalamin)",
        "dosage": "1000 mcg daily",
        "notes": "Sublingual form may offer better absorption.",
        "prescription_required": False,
    },
    "Anemia (low hemoglobin)": {
        "name": "Iron bisglycinate",
        "dosage": "25-50 mg elemental iron daily",
        "notes": "Take with vitamin C for enhanced absorption. Avoid with tea/coffee.",
        "prescription_required": False,
    },
    "Iron deficiency": {
        "name": "Iron bisglycinate",
        "dosage": "25-50 mg elemental iron daily",
        "notes": "Take with vitamin C. Recheck levels after 3 months.",
        "prescription_required": False,
    },
    "Low ferritin (depleted iron stores)": {
        "name": "Iron with Folic Acid",
        "dosage": "25 mg iron + 400 mcg folic acid daily",
        "notes": "Low ferritin precedes anemia. Early supplementation recommended.",
        "prescription_required": False,
    },
    "Low calcium": {
        "name": "Calcium citrate with Vitamin D",
        "dosage": "500-600 mg calcium + 400 IU vitamin D, twice daily",
        "notes": "Take separately from iron supplements (2 hours apart).",
        "prescription_required": False,
    },
    "Folate deficiency": {
        "name": "Folic acid",
        "dosage": "400-800 mcg daily",
        "notes": "Especially important for women of childbearing age.",
        "prescription_required": False,
    },
    "Low magnesium": {
        "name": "Magnesium glycinate",
        "dosage": "200-400 mg daily",
        "notes": "Take before bed; may improve sleep quality.",
        "prescription_required": False,
    },
    "Low HDL cholesterol": {
        "name": "Omega-3 Fish Oil",
        "dosage": "1000-2000 mg EPA+DHA daily",
        "notes": "Choose a quality supplement with high EPA/DHA ratio.",
        "prescription_required": False,
    },
    "High triglycerides": {
        "name": "Omega-3 Fish Oil",
        "dosage": "2000-4000 mg EPA+DHA daily",
        "notes": "High-dose omega-3 can lower triglycerides. Consult physician if on blood thinners.",
        "prescription_required": False,
    },
    "High LDL cholesterol": {
        "name": "Plant sterols / Psyllium fiber",
        "dosage": "2g plant sterols or 10g psyllium daily",
        "notes": "Plant sterols can reduce LDL by 5-15%. Not a substitute for medical treatment.",
        "prescription_required": False,
    },
    "Low potassium (hypokalemia)": {
        "name": "Potassium citrate",
        "dosage": "99 mg daily (OTC max)",
        "notes": "Dietary sources preferred: bananas, potatoes, spinach.",
        "prescription_required": False,
    },
}


class RecommendationService:
    def __init__(
        self,
        recommendation_repo: RecommendationRepository,
        biomarker_repo: BiomarkerRepository,
        user_repo: UserRepository,
        lab_service: LabInterpretationService,
        nutrition_service: NutritionService,
        fitness_service: FitnessService,
    ) -> None:
        self.recommendation_repo = recommendation_repo
        self.biomarker_repo = biomarker_repo
        self.user_repo = user_repo
        self.lab_service = lab_service
        self.nutrition_service = nutrition_service
        self.fitness_service = fitness_service

    async def get_recommendations(self, user_id: str) -> list[dict]:
        return await self.recommendation_repo.get_by_user(user_id)

    async def get_latest(self, user_id: str) -> dict:
        rec = await self.recommendation_repo.get_latest(user_id)
        if not rec:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No recommendations found for this user",
            )
        return rec

    async def generate(
        self,
        user_id: str,
        report_id: Optional[str] = None,
    ) -> dict:
        # 1. Fetch user profile
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # 2. Fetch biomarkers (from specific report or latest)
        if report_id:
            biomarker_doc = await self.biomarker_repo.get_by_report(report_id)
        else:
            biomarker_doc = await self.biomarker_repo.get_latest_by_user(user_id)

        if not biomarker_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No biomarkers found. Upload and analyse a report first.",
            )

        markers = biomarker_doc.get("markers", {})
        gender = (user.get("gender") or "male").lower()

        # 3. Lab interpretation
        interpretation = self.lab_service.interpret(markers, gender)

        # 4. Supplement suggestions
        supplements = self._suggest_supplements(interpretation)

        # 5. Nutrition summary
        weight = user.get("weight") or user.get("weight_kg") or 70
        height = user.get("height") or user.get("height_cm") or 170
        age = user.get("age") or 30
        activity = user.get("activity_level") or "moderate"
        goal = user.get("goal") or "maintenance"
        if isinstance(goal, list):
            goal = goal[0] if goal else "maintenance"

        nutrition_calc = self.nutrition_service.calculate_all(
            weight_kg=weight,
            height_cm=height,
            age=age,
            gender=gender,
            activity_level=activity,
            goal=goal,
        )

        # 6. Fitness adaptations
        fitness_adaptations = self.fitness_service.get_biomarker_adaptations(
            markers, gender
        )

        # 7. Build summary
        summary_parts = []
        if interpretation["deficiencies"]:
            labels = [d["label"] for d in interpretation["deficiencies"]]
            summary_parts.append(f"Deficiencies found: {', '.join(labels)}.")
        if interpretation["risk_factors"]:
            labels = [r["label"] for r in interpretation["risk_factors"]]
            summary_parts.append(f"Risk factors: {', '.join(labels)}.")
        if interpretation["warnings"]:
            labels = [w["label"] for w in interpretation["warnings"]]
            summary_parts.append(f"Warnings: {', '.join(labels)}.")
        if not summary_parts:
            summary_parts.append("All biomarkers are within normal ranges.")

        summary_parts.append(
            f"Recommended daily intake: {nutrition_calc['target_calories']} kcal "
            f"(BMI: {nutrition_calc['bmi']} - {nutrition_calc['bmi_category']})."
        )
        if fitness_adaptations:
            summary_parts.append(
                f"Workout adaptations: {'; '.join(fitness_adaptations)}"
            )

        summary = " ".join(summary_parts)

        # 8. Persist
        full_interpretation = {
            **interpretation,
            "nutrition": nutrition_calc,
            "fitness_adaptations": fitness_adaptations,
        }

        rec_doc = {
            "user_id": user_id,
            "interpretation": full_interpretation,
            "supplements": supplements,
            "summary": summary,
            "created_at": datetime.now(timezone.utc),
        }
        saved = await self.recommendation_repo.create(rec_doc)
        return saved

    @staticmethod
    def _suggest_supplements(interpretation: dict) -> list[dict]:
        """Map deficiencies/risk_factors/warnings to non-prescription supplements."""
        suggestions: list[dict] = []
        seen: set[str] = set()

        for category in ("deficiencies", "risk_factors", "warnings"):
            for finding in interpretation.get(category, []):
                label = finding["label"]
                supp = _SUPPLEMENT_MAP.get(label)
                if supp and supp["name"] not in seen:
                    seen.add(supp["name"])
                    suggestions.append(supp)

        return suggestions
