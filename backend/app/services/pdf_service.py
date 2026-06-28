"""
PDF report generation service using ReportLab.

Produces a polished, multi-section "Personalized Transformation Plan":
- Cover header + client summary table
- The Strategy (narrative, derived from goal + flagged biomarkers)
- Your Numbers (BMR / TDEE / target + daily macro targets)
- The Daily Diet Plan (uses the generated plan, or a macro-based template)
- Heart-Smart Rules (only when lipid markers are flagged)
- The Training Plan (per-day exercise tables)
- Biomarker Snapshot + Lab Interpretation
- Recovery, Supplements & Golden Rules
- Tracking & Adjusting
- Important medical note
"""

import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PAGE_WIDTH, PAGE_HEIGHT = A4

# Brand palette
NAVY = colors.HexColor("#1F3A5F")
ACCENT = colors.HexColor("#2E6DA4")
LIGHT_ROW = colors.HexColor("#EAF0F6")
GRID = colors.HexColor("#B7C4D4")
RED = colors.HexColor("#C0392B")
GREEN = colors.HexColor("#1E8449")
ORANGE = colors.HexColor("#B9770E")

_ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "lightly_active": 1.375,
    "moderate": 1.55,
    "moderately_active": 1.55,
    "active": 1.725,
    "very_active": 1.725,
    "athlete": 1.9,
    "extra_active": 1.9,
}


class PDFService:
    """Generate the Personalized Transformation Plan PDF from NutriMed AI data."""

    # ------------------------------------------------------------------ public
    def generate_report_pdf(
        self,
        user: dict,
        biomarkers: Optional[dict] = None,
        interpretation: Optional[dict] = None,
        diet_plan: Optional[dict] = None,
        workout_plan: Optional[dict] = None,
        supplements: Optional[list[dict]] = None,
    ) -> bytes:
        self._init_styles()
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=22 * mm,
            bottomMargin=18 * mm,
            leftMargin=16 * mm,
            rightMargin=16 * mm,
            title="Personalized Transformation Plan",
        )

        markers = self._flatten_markers(biomarkers)
        numbers = self._compute_numbers(user, diet_plan)
        goal_label = self._goal_label(user, diet_plan)

        e: list = []
        e += self._cover(user, numbers, goal_label)
        e += self._strategy(user, numbers, goal_label, interpretation, markers)
        e += self._numbers_section(numbers)
        e += self._diet_section(diet_plan, numbers)
        e += self._heart_smart(interpretation, markers)
        e += self._training_section(workout_plan)
        e += self._biomarker_section(markers, interpretation)
        e += self._recovery_supplements(supplements, numbers)
        e += self._tracking_section(goal_label)
        e += self._important_note(interpretation)

        doc.build(e, onFirstPage=self._page_furniture, onLaterPages=self._page_furniture)
        return buffer.getvalue()

    # ------------------------------------------------------------------ styles
    def _init_styles(self) -> None:
        base = getSampleStyleSheet()
        self.s_title = ParagraphStyle(
            "PTitle", parent=base["Title"], fontSize=24, leading=28,
            textColor=NAVY, spaceAfter=2,
        )
        self.s_subtitle = ParagraphStyle(
            "PSubtitle", parent=base["BodyText"], fontSize=12, leading=15,
            textColor=ACCENT, fontName="Helvetica-Oblique", spaceAfter=4,
        )
        self.s_h2 = ParagraphStyle(
            "PH2", parent=base["Heading2"], fontSize=14, leading=17,
            textColor=NAVY, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=2,
        )
        self.s_h3 = ParagraphStyle(
            "PH3", parent=base["Heading3"], fontSize=11, leading=14,
            textColor=ACCENT, fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=2,
        )
        self.s_body = ParagraphStyle(
            "PBody", parent=base["BodyText"], fontSize=9.5, leading=14, spaceAfter=4,
        )
        self.s_bullet = ParagraphStyle(
            "PBullet", parent=base["BodyText"], fontSize=9.5, leading=13,
            leftIndent=10, spaceAfter=2,
        )
        self.s_note = ParagraphStyle(
            "PNote", parent=base["BodyText"], fontSize=8.5, leading=12,
            textColor=colors.grey, fontName="Helvetica-Oblique",
        )
        self.s_cell = ParagraphStyle(
            "PCell", parent=base["BodyText"], fontSize=9, leading=12,
        )
        self.s_cell_b = ParagraphStyle(
            "PCellB", parent=self.s_cell, fontName="Helvetica-Bold",
        )
        self.s_cell_w = ParagraphStyle(
            "PCellW", parent=self.s_cell, fontName="Helvetica-Bold", textColor=colors.white,
        )

    # ------------------------------------------------------------- furniture
    def _page_furniture(self, canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(PAGE_WIDTH - 16 * mm, PAGE_HEIGHT - 12 * mm,
                               "Personalized Transformation Plan")
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.5)
        canvas.line(16 * mm, PAGE_HEIGHT - 14 * mm, PAGE_WIDTH - 16 * mm, PAGE_HEIGHT - 14 * mm)
        canvas.drawString(16 * mm, 10 * mm, "NutriMed AI")
        canvas.drawCentredString(PAGE_WIDTH / 2, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def _header(self, title: str) -> list:
        return [
            Spacer(1, 6),
            Paragraph(title, self.s_h2),
            HRFlowable(width="100%", thickness=1.2, color=NAVY,
                       spaceBefore=1, spaceAfter=6),
        ]

    def _table(self, data, col_widths, header=True, align_center_cols=None) -> Table:
        align_center_cols = align_center_cols or []
        t = Table(data, colWidths=col_widths, hAlign="LEFT")
        cmds = [
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        if header:
            cmds += [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_ROW]),
            ]
        for c in align_center_cols:
            cmds.append(("ALIGN", (c, 0), (c, -1), "CENTER"))
        t.setStyle(TableStyle(cmds))
        return t

    # ------------------------------------------------------------------- data
    @staticmethod
    def _flatten_markers(biomarkers: Optional[dict]) -> dict:
        if not biomarkers:
            return {}
        markers = biomarkers.get("markers")
        if isinstance(markers, dict) and markers:
            return {k: v for k, v in markers.items() if isinstance(v, (int, float))}
        exclude = {"user_id", "report_id", "extracted_at", "created_at", "id"}
        return {
            k: v for k, v in biomarkers.items()
            if k not in exclude and isinstance(v, (int, float))
        }

    def _compute_numbers(self, user: dict, diet_plan: Optional[dict]) -> dict:
        try:
            weight = float(user.get("weight") or user.get("weight_kg") or 0)
        except (TypeError, ValueError):
            weight = 0.0
        try:
            height = float(user.get("height") or user.get("height_cm") or 0)
        except (TypeError, ValueError):
            height = 0.0
        try:
            age = int(user.get("age") or 0)
        except (TypeError, ValueError):
            age = 0
        gender = str(user.get("gender") or "male").lower()
        activity = str(user.get("activity_level") or "moderate").lower()
        mult = _ACTIVITY_MULTIPLIERS.get(activity, 1.55)

        bmr = tdee = bmi = 0.0
        bmi_cat = "N/A"
        if weight and height and age:
            if gender.startswith("f"):
                bmr = 10 * weight + 6.25 * height - 5 * age - 161
            else:
                bmr = 10 * weight + 6.25 * height - 5 * age + 5
            tdee = bmr * mult
            m = height / 100.0
            bmi = weight / (m * m)
            bmi_cat = (
                "Underweight" if bmi < 18.5 else
                "Lean / Healthy" if bmi < 25 else
                "Overweight" if bmi < 30 else "Obese"
            )

        goals = [str(g).lower() for g in (user.get("goals") or [])]
        goal_blob = " ".join(goals) + " " + str((diet_plan or {}).get("goal", "")).lower()
        if any(k in goal_blob for k in ("loss", "cut", "lean_out", "fat")):
            delta, surplus_note = -500, "−500 deficit → ~0.5 kg/week loss"
        elif any(k in goal_blob for k in ("gain", "bulk", "muscle")):
            delta, surplus_note = 300, "+300 surplus → ~0.25 kg/week gain"
        else:
            delta, surplus_note = 0, "maintenance"

        target = (tdee + delta) if tdee else 0.0

        # Prefer an explicit generated diet plan if it carries numbers.
        dp = diet_plan or {}
        if dp.get("calories"):
            try:
                target = float(dp["calories"])
            except (TypeError, ValueError):
                pass
        macros = dp.get("macros") or {}
        protein_g = macros.get("protein_g")
        carbs_g = macros.get("carbs_g")
        fat_g = macros.get("fat_g")
        if not (protein_g and carbs_g and fat_g) and target and weight:
            protein_g = round(2.0 * weight)
            fat_g = round((target * 0.25) / 9)
            carbs_g = round((target - (protein_g * 4 + fat_g * 9)) / 4)

        return {
            "weight": weight, "height": height, "age": age, "gender": gender,
            "activity": activity, "bmr": bmr, "tdee": tdee, "target": target,
            "bmi": bmi, "bmi_cat": bmi_cat, "surplus_note": surplus_note,
            "protein_g": protein_g or 0, "carbs_g": carbs_g or 0, "fat_g": fat_g or 0,
        }

    @staticmethod
    def _goal_label(user: dict, diet_plan: Optional[dict]) -> str:
        goals = user.get("goals") or []
        if goals:
            return ", ".join(str(g).replace("_", " ").title() for g in goals)
        g = (diet_plan or {}).get("goal")
        return str(g).replace("_", " ").title() if g else "General Health"

    @staticmethod
    def _has_lipid_flags(interpretation: Optional[dict], markers: dict) -> bool:
        lipid = {"ldl", "hdl", "triglycerides", "total_cholesterol", "cholesterol"}
        if any(k in markers for k in lipid):
            for section in ("risk_factors", "warnings", "deficiencies"):
                for item in (interpretation or {}).get(section, []):
                    if isinstance(item, dict) and str(item.get("marker", "")).lower() in lipid:
                        return True
        # Fall back: flag if cholesterol/triglycerides are present and high-ish.
        if markers.get("total_cholesterol", 0) >= 200:
            return True
        if markers.get("triglycerides", 0) >= 150 or markers.get("ldl", 0) >= 130:
            return True
        return False

    # --------------------------------------------------------------- sections
    def _cover(self, user, numbers, goal_label) -> list:
        name = user.get("name") or user.get("full_name") or "Client"
        e = [
            Paragraph("PERSONALIZED TRANSFORMATION PLAN", self.s_title),
            Paragraph("Nutrition &bull; Training &bull; Body Recomposition", self.s_subtitle),
            HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=2, spaceAfter=10),
        ]
        h = numbers["height"]
        height_str = f"{h:.0f} cm" if h else "N/A"
        weight_str = f"{numbers['weight']:.0f} kg" if numbers["weight"] else "N/A"
        bmi_str = f"{numbers['bmi']:.1f} ({numbers['bmi_cat']})" if numbers["bmi"] else "N/A"
        rows = [
            [Paragraph("Client", self.s_cell_b), Paragraph(str(name), self.s_cell),
             Paragraph("Age", self.s_cell_b), Paragraph(f"{numbers['age'] or 'N/A'} yrs", self.s_cell)],
            [Paragraph("Height", self.s_cell_b), Paragraph(height_str, self.s_cell),
             Paragraph("Weight", self.s_cell_b), Paragraph(weight_str, self.s_cell)],
            [Paragraph("BMI", self.s_cell_b), Paragraph(bmi_str, self.s_cell),
             Paragraph("Goal", self.s_cell_b), Paragraph(goal_label, self.s_cell)],
            [Paragraph("Activity", self.s_cell_b),
             Paragraph(numbers["activity"].replace("_", " ").title(), self.s_cell),
             Paragraph("Prepared by", self.s_cell_b), Paragraph("NutriMed AI", self.s_cell)],
        ]
        cw = [28 * mm, 52 * mm, 28 * mm, 52 * mm]
        t = Table(rows, colWidths=cw, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, GRID),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_ROW),
            ("BACKGROUND", (2, 0), (2, -1), LIGHT_ROW),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ]))
        e.append(t)
        return e

    def _strategy(self, user, numbers, goal_label, interpretation, markers) -> list:
        e = self._header("1. The Strategy")
        goal_blob = goal_label.lower()
        bmi = numbers["bmi"]
        if "loss" in goal_blob or "fat" in goal_blob or (bmi and bmi >= 25):
            core = (
                f"Your primary goal is <b>{goal_label}</b>. The plan runs a controlled "
                "calorie deficit while keeping protein high, so you lose fat and preserve "
                "lean muscle rather than just dropping scale weight. Strength training "
                "protects muscle; the deficit drives the fat loss."
            )
        elif "gain" in goal_blob or "muscle" in goal_blob or "bulk" in goal_blob:
            core = (
                f"Your primary goal is <b>{goal_label}</b>. With a "
                f"{('BMI of %.1f (%s)' % (bmi, numbers['bmi_cat'])) if bmi else 'lean profile'}, "
                "the correct approach is a <b>lean bulk</b>: a small calorie surplus, hard "
                "progressive-overload training, and patience. Muscle is added gradually while "
                "fat gain is minimised."
            )
        else:
            core = (
                f"Your goal is <b>{goal_label}</b>. This plan keeps you at maintenance "
                "calories with balanced macros and consistent training to improve body "
                "composition and overall health."
            )
        e.append(Paragraph(core, self.s_body))

        flags = []
        for section in ("deficiencies", "risk_factors"):
            for item in (interpretation or {}).get(section, []):
                if isinstance(item, dict) and item.get("label"):
                    flags.append(str(item["label"]))
        if flags:
            e.append(Paragraph(
                "Your recent lab report flagged: <b>" + ", ".join(flags[:6]) + "</b>. "
                "This plan is deliberately built to help improve those markers while you "
                "train — nutrient-dense food, the right supplements, and heart-smart "
                "choices where relevant.", self.s_body))
        return e

    def _numbers_section(self, n) -> list:
        if not n["tdee"]:
            return []
        e = self._header("2. Your Numbers — Calories & Macros")
        e.append(Paragraph(
            "Calculated using the Mifflin–St Jeor equation with an activity multiplier.",
            self.s_note))
        e.append(Spacer(1, 4))
        rows = [
            [Paragraph("Metric", self.s_cell_w), Paragraph("Value", self.s_cell_w),
             Paragraph("Notes", self.s_cell_w)],
            [Paragraph("BMR (resting burn)", self.s_cell), Paragraph(f"~{n['bmr']:.0f} kcal", self.s_cell),
             Paragraph("Calories at complete rest", self.s_cell)],
            [Paragraph("Maintenance (TDEE)", self.s_cell), Paragraph(f"~{n['tdee']:.0f} kcal", self.s_cell),
             Paragraph(f"Activity: {n['activity'].replace('_', ' ')}", self.s_cell)],
            [Paragraph("TARGET", self.s_cell_b), Paragraph(f"~{n['target']:.0f} kcal", self.s_cell_b),
             Paragraph(n["surplus_note"], self.s_cell)],
        ]
        e.append(self._table(rows, [50 * mm, 35 * mm, 75 * mm], align_center_cols=[1]))
        e.append(Spacer(1, 8))
        e.append(Paragraph("Daily Macro Targets", self.s_h3))
        p, c, f = n["protein_g"], n["carbs_g"], n["fat_g"]
        mrows = [
            [Paragraph("Macro", self.s_cell_w), Paragraph("Grams/day", self.s_cell_w),
             Paragraph("Calories", self.s_cell_w), Paragraph("Why it matters", self.s_cell_w)],
            [Paragraph("Protein", self.s_cell), Paragraph(f"{p:.0f} g", self.s_cell),
             Paragraph(f"{p*4:.0f} kcal", self.s_cell), Paragraph("Muscle repair & growth — top priority", self.s_cell)],
            [Paragraph("Carbohydrate", self.s_cell), Paragraph(f"{c:.0f} g", self.s_cell),
             Paragraph(f"{c*4:.0f} kcal", self.s_cell), Paragraph("Fuels training & recovery", self.s_cell)],
            [Paragraph("Fat", self.s_cell), Paragraph(f"{f:.0f} g", self.s_cell),
             Paragraph(f"{f*9:.0f} kcal", self.s_cell), Paragraph("Hormones — keep mostly unsaturated", self.s_cell)],
        ]
        e.append(self._table(mrows, [32 * mm, 26 * mm, 26 * mm, 76 * mm], align_center_cols=[1, 2]))
        return e

    def _diet_section(self, diet_plan, n) -> list:
        e = self._header("3. The Daily Diet Plan")
        meals = self._resolve_meals(diet_plan, n)
        if not meals:
            e.append(Paragraph("No diet plan available yet. Generate one in the app to populate "
                               "this section.", self.s_note))
            return e
        for meal in meals:
            head = f"<b>{meal['name']}</b>"
            if meal.get("kcal"):
                head += f" &nbsp;(~{meal['kcal']} kcal" + (f" | P {meal['protein']}g)" if meal.get("protein") else ")")
            e.append(Paragraph(head, self.s_h3))
            for item in meal["items"]:
                e.append(Paragraph(f"&bull; {item}", self.s_bullet))
        if n.get("target"):
            e.append(Spacer(1, 4))
            e.append(Paragraph(
                f"<b>DAILY TARGET:</b> ~{n['target']:.0f} kcal | Protein ~{n['protein_g']:.0f}g "
                f"| Carbs ~{n['carbs_g']:.0f}g | Fat ~{n['fat_g']:.0f}g", self.s_body))
        return e

    def _resolve_meals(self, diet_plan, n) -> list:
        """Use the generated meal_plan if present, else a macro-scaled template."""
        meal_plan = (diet_plan or {}).get("meal_plan") or []
        out: list = []
        if meal_plan:
            day = meal_plan[0] if isinstance(meal_plan[0], dict) else None
            meals = (day or {}).get("meals", []) if day else meal_plan
            for meal in meals:
                if not isinstance(meal, dict):
                    continue
                items = []
                for fdict in meal.get("foods", []):
                    if isinstance(fdict, dict):
                        nm = fdict.get("name", "")
                        qty = fdict.get("quantity") or fdict.get("portion")
                        items.append(f"{nm} ({qty})" if qty else nm)
                    elif isinstance(fdict, str):
                        items.append(fdict)
                if meal.get("name") and items:
                    out.append({
                        "name": meal["name"],
                        "kcal": meal.get("calories"),
                        "protein": meal.get("protein_g") or meal.get("protein"),
                        "items": items,
                    })
        if out:
            return out
        # Macro-based template (generic, structured like a coach's plan).
        if not n.get("target"):
            return []
        t = n["target"]
        split = [
            ("Meal 1 — Breakfast", 0.22, [
                "3 whole eggs + 2 egg whites (minimal oil) — veg: 4 idli + sambar",
                "50g oats in milk + 1 banana + 10 almonds",
                "Black coffee / green tea (no sugar)"]),
            ("Meal 2 — Mid-Morning", 0.13, [
                "200g Greek yogurt / thick curd + 1 fruit",
                "OR 1 scoop whey protein"]),
            ("Meal 3 — Lunch", 0.28, [
                "150g rice OR 3 rotis",
                "150g chicken / fish — veg: 1.5 cups dal + 100g paneer",
                "Large serving of vegetables + salad"]),
            ("Meal 4 — Pre-Workout", 0.11, [
                "1 banana + 1 tbsp peanut butter on brown bread",
                "OR boiled sweet potato + 1 egg"]),
            ("Meal 5 — Dinner", 0.26, [
                "150g chicken / fish / paneer — veg: soya chunks",
                "2 rotis OR 120g rice",
                "Cooked vegetables + green salad"]),
        ]
        meals = []
        for name, frac, items in split:
            meals.append({
                "name": name,
                "kcal": round(t * frac / 10) * 10,
                "protein": round(n["protein_g"] * frac),
                "items": items,
            })
        return meals

    def _heart_smart(self, interpretation, markers) -> list:
        if not self._has_lipid_flags(interpretation, markers):
            return []
        e = self._header("4. Heart-Smart Rules (Because of Your Lipid Markers)")
        rules = [
            "<b>Eat fish 2–3x/week</b> — omega-3 lowers triglycerides.",
            "<b>Use good oils</b> — mustard, rice-bran, or olive oil. Never reuse frying oil.",
            "<b>Load soluble fiber</b> — oats, dal, vegetables, and fruit actively lower LDL.",
            "<b>Cut sugar & refined carbs</b> — they drive triglycerides up.",
            "<b>Nuts over fried snacks</b> — almonds / walnuts as your fat source.",
        ]
        for r in rules:
            e.append(Paragraph(f"&bull; {r}", self.s_bullet))
        return e

    def _training_section(self, workout_plan) -> list:
        e = self._header("5. The Training Plan")
        if not workout_plan:
            e.append(Paragraph("No workout plan available yet. Generate one in the app to "
                               "populate this section.", self.s_note))
            return e
        meta = []
        if workout_plan.get("goal"):
            meta.append(str(workout_plan["goal"]).replace("_", " ").title())
        if workout_plan.get("difficulty"):
            meta.append(str(workout_plan["difficulty"]).title())
        if workout_plan.get("days_per_week"):
            meta.append(f"{workout_plan['days_per_week']} days/week")
        if meta:
            e.append(Paragraph(" &bull; ".join(meta), self.s_body))
        e.append(Paragraph(
            "Progressive overload is the rule: add weight or reps every week you can. "
            "Rest 90–120s on big lifts, 60s on isolation.", self.s_note))

        days = workout_plan.get("plan") or workout_plan.get("days") or []
        if not isinstance(days, list):
            days = []
        rendered = 0
        for day in days:
            if not isinstance(day, dict):
                continue
            exercises = day.get("exercises", [])
            if not exercises:
                continue
            rows = [[Paragraph("Exercise", self.s_cell_w),
                     Paragraph("Sets × Reps", self.s_cell_w),
                     Paragraph("Rest", self.s_cell_w)]]
            for ex in exercises:
                if not isinstance(ex, dict):
                    continue
                rows.append([
                    Paragraph(str(ex.get("name", "")), self.s_cell),
                    Paragraph(f"{ex.get('sets', '')} × {ex.get('reps', '')}", self.s_cell),
                    Paragraph(str(ex.get("rest", "60s")), self.s_cell),
                ])
            block = [
                Paragraph(str(day.get("day_name", f"Day {rendered + 1}")), self.s_h3),
                self._table(rows, [88 * mm, 36 * mm, 26 * mm], align_center_cols=[1, 2]),
            ]
            e.append(KeepTogether(block))
            rendered += 1
        if rendered == 0:
            e.append(Paragraph("The latest workout plan has no exercises recorded.", self.s_note))
        return e

    def _biomarker_section(self, markers, interpretation) -> list:
        if not markers:
            return []
        e = self._header("6. Biomarker Snapshot")
        details = (interpretation or {}).get("marker_details", {})
        rows = [[Paragraph("Biomarker", self.s_cell_w), Paragraph("Value", self.s_cell_w),
                 Paragraph("Unit", self.s_cell_w), Paragraph("Reference", self.s_cell_w),
                 Paragraph("Status", self.s_cell_w)]]
        status_color = {"low": RED, "high": ORANGE, "normal": GREEN}
        def _clean(v):
            s = str(v).strip()
            return "" if s.lower() in ("", "none", "unknown", "n/a") else s

        for name, value in markers.items():
            d = details.get(name, {})
            st = _clean(d.get("status", "")).lower()
            st_label = st.upper() if st else "—"
            st_style = ParagraphStyle("st", parent=self.s_cell, textColor=status_color.get(st, colors.grey),
                                      fontName="Helvetica-Bold")
            rows.append([
                Paragraph(name.replace("_", " ").title(), self.s_cell),
                Paragraph(str(round(value, 2) if isinstance(value, float) else value), self.s_cell),
                Paragraph(_clean(d.get("unit", "")) or "—", self.s_cell),
                Paragraph(_clean(d.get("range", "")) or "—", self.s_cell),
                Paragraph(st_label, st_style),
            ])
        e.append(self._table(rows, [44 * mm, 22 * mm, 22 * mm, 38 * mm, 24 * mm],
                             align_center_cols=[1, 2, 4]))

        bullets = []
        for section, label in (("deficiencies", "Deficiency"), ("risk_factors", "Risk")):
            for item in (interpretation or {}).get(section, []):
                if isinstance(item, dict) and item.get("label"):
                    detail = item.get("detail", "")
                    bullets.append(f"<b>{label}: {item['label']}</b> — {detail}")
        if bullets:
            e.append(Spacer(1, 6))
            e.append(Paragraph("Interpretation", self.s_h3))
            for b in bullets:
                e.append(Paragraph(f"&bull; {b}", self.s_bullet))
        return e

    def _recovery_supplements(self, supplements, n) -> list:
        e = self._header("7. Recovery, Supplements & Golden Rules")
        golden = [
            "<b>Sleep 7–9 hours</b> — muscle is built during rest, not in the gym.",
            "<b>Hydrate</b> — 3–3.5 litres of water daily.",
            "<b>Hit protein first</b> — if you get one thing right each day, make it protein.",
        ]
        for g in golden:
            e.append(Paragraph(f"&bull; {g}", self.s_bullet))

        if supplements:
            e.append(Spacer(1, 6))
            e.append(Paragraph("Supplement Suggestions", self.s_h3))
            e.append(Paragraph("Non-prescription suggestions only. Confirm with your "
                               "healthcare provider before starting.", self.s_note))
            rows = [[Paragraph("Supplement", self.s_cell_w), Paragraph("Dosage", self.s_cell_w),
                     Paragraph("Timing", self.s_cell_w), Paragraph("Notes", self.s_cell_w)]]
            for s in supplements:
                if not isinstance(s, dict):
                    continue
                rows.append([
                    Paragraph(str(s.get("name", "")), self.s_cell),
                    Paragraph(str(s.get("dosage", "")), self.s_cell),
                    Paragraph(str(s.get("timing", "")), self.s_cell),
                    Paragraph(str(s.get("notes", "")), self.s_cell),
                ])
            e.append(self._table(rows, [32 * mm, 40 * mm, 30 * mm, 60 * mm]))
        return e

    def _tracking_section(self, goal_label) -> list:
        e = self._header("8. Tracking & Adjusting")
        rows = [
            [Paragraph("What", self.s_cell_w), Paragraph("How often", self.s_cell_w),
             Paragraph("Action", self.s_cell_w)],
            [Paragraph("Bodyweight", self.s_cell), Paragraph("Weekly, same time", self.s_cell),
             Paragraph("Trending the wrong way → adjust calories by ~200–300.", self.s_cell)],
            [Paragraph("Progress photos", self.s_cell), Paragraph("Every 2 weeks", self.s_cell),
             Paragraph("Better signal than the scale for recomposition.", self.s_cell)],
            [Paragraph("Lifting log", self.s_cell), Paragraph("Every session", self.s_cell),
             Paragraph("Beat last week's weight or reps = progressive overload.", self.s_cell)],
            [Paragraph("Blood panel", self.s_cell), Paragraph("~3 months", self.s_cell),
             Paragraph("Re-test to confirm flagged markers are improving.", self.s_cell)],
        ]
        e.append(self._table(rows, [34 * mm, 38 * mm, 90 * mm]))
        return e

    def _important_note(self, interpretation) -> list:
        e = [Spacer(1, 10), HRFlowable(width="100%", thickness=0.5, color=GRID, spaceAfter=4)]
        note = (
            "This is an evidence-based template generated by NutriMed AI, not personalized "
            "medical advice. If your lab report flagged any markers, confirm with a doctor or "
            "registered dietitian before starting supplements or a calorie surplus/deficit, "
            "and re-test your bloodwork in ~3 months."
        )
        e.append(Paragraph("<b>Important Note</b>", ParagraphStyle(
            "INote", parent=self.s_note, textColor=RED, fontName="Helvetica-Bold")))
        e.append(Paragraph(note, self.s_note))
        e.append(Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            ParagraphStyle("Gen", parent=self.s_note, alignment=TA_CENTER)))
        return e
