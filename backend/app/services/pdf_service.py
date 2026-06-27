"""
PDF report generation service using ReportLab.

Generates a professional PDF with:
- Header with logo placeholder and title
- Patient info table
- Biomarker results table with status
- Lab interpretation (deficiencies, risks, warnings)
- Diet plan summary
- Workout plan summary
- Supplement suggestions
"""

import io
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch, mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class PDFService:
    """Generate PDF reports from NutriMed AI data."""

    def generate_report_pdf(
        self,
        user: dict,
        biomarkers: Optional[dict] = None,
        interpretation: Optional[dict] = None,
        diet_plan: Optional[dict] = None,
        workout_plan: Optional[dict] = None,
        supplements: Optional[list[dict]] = None,
    ) -> bytes:
        """Build a full PDF report and return raw bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=15 * mm,
            rightMargin=15 * mm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Title"],
            fontSize=22,
            spaceAfter=6,
            textColor=colors.HexColor("#1a5276"),
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=6,
            textColor=colors.HexColor("#2c3e50"),
        )
        body_style = styles["BodyText"]

        elements: list = []

        # ---- Header ----
        elements.append(Paragraph("NutriMed AI", title_style))
        elements.append(
            Paragraph(
                "Personalised Health & Nutrition Report",
                ParagraphStyle(
                    "Subtitle",
                    parent=body_style,
                    fontSize=12,
                    textColor=colors.grey,
                ),
            )
        )
        elements.append(Spacer(1, 10))
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        elements.append(Paragraph(f"Generated: {generated}", body_style))
        elements.append(Spacer(1, 12))

        # ---- Patient Info ----
        elements.append(Paragraph("Patient Information", heading_style))
        user_name = user.get("name") or user.get("full_name", "N/A")
        patient_data = [
            ["Name", user_name],
            ["Email", user.get("email", "N/A")],
            ["Age", str(user.get("age", "N/A"))],
            ["Gender", str(user.get("gender", "N/A")).title()],
            ["Height", f"{user.get('height') or user.get('height_cm', 'N/A')} cm"],
            ["Weight", f"{user.get('weight') or user.get('weight_kg', 'N/A')} kg"],
        ]
        patient_table = Table(patient_data, colWidths=[2 * inch, 4 * inch])
        patient_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eaf2f8")),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(patient_table)
        elements.append(Spacer(1, 12))

        # ---- Biomarker Results ----
        if biomarkers:
            elements.append(Paragraph("Biomarker Results", heading_style))
            markers = biomarkers.get("markers", biomarkers)
            marker_details = {}
            if interpretation:
                marker_details = interpretation.get("marker_details", {})

            bio_data = [["Biomarker", "Value", "Unit", "Range", "Status"]]
            for marker_name, value in markers.items():
                detail = marker_details.get(marker_name, {})
                unit = detail.get("unit", "")
                ref_range = detail.get("range", "")
                status_val = detail.get("status", "")
                bio_data.append([
                    marker_name.replace("_", " ").title(),
                    str(round(value, 2) if isinstance(value, float) else value),
                    unit,
                    ref_range,
                    status_val.upper() if status_val else "",
                ])

            bio_table = Table(
                bio_data,
                colWidths=[2 * inch, 1 * inch, 0.8 * inch, 1 * inch, 0.8 * inch],
            )
            status_colors = {
                "LOW": colors.HexColor("#e74c3c"),
                "HIGH": colors.HexColor("#e67e22"),
                "NORMAL": colors.HexColor("#27ae60"),
            }
            style_cmds = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ]
            # Color-code status cells
            for row_idx in range(1, len(bio_data)):
                status_text = bio_data[row_idx][4]
                color = status_colors.get(status_text)
                if color:
                    style_cmds.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), color))
                    style_cmds.append(("FONTNAME", (4, row_idx), (4, row_idx), "Helvetica-Bold"))

            bio_table.setStyle(TableStyle(style_cmds))
            elements.append(bio_table)
            elements.append(Spacer(1, 12))

        # ---- Interpretation ----
        if interpretation:
            elements.append(Paragraph("Lab Interpretation", heading_style))

            for section, label in [
                ("deficiencies", "Deficiencies"),
                ("risk_factors", "Risk Factors"),
                ("warnings", "Warnings"),
            ]:
                items = interpretation.get(section, [])
                if items:
                    elements.append(
                        Paragraph(
                            f"<b>{label}:</b>",
                            ParagraphStyle("SectionLabel", parent=body_style, fontSize=11),
                        )
                    )
                    for item in items:
                        bullet_text = (
                            f"&bull; <b>{item['label']}</b> "
                            f"({item['marker']}: {item['value']}) - {item['detail']}"
                        )
                        elements.append(Paragraph(bullet_text, body_style))
                    elements.append(Spacer(1, 6))

            normals = interpretation.get("normal", [])
            if normals:
                normal_str = ", ".join(
                    n.replace("_", " ").title() for n in normals
                )
                elements.append(
                    Paragraph(f"<b>Normal:</b> {normal_str}", body_style)
                )
                elements.append(Spacer(1, 12))

        # ---- Diet Plan ----
        if diet_plan:
            elements.append(Paragraph("Diet Plan", heading_style))
            elements.append(
                Paragraph(
                    f"Goal: {diet_plan.get('goal', 'N/A')} | "
                    f"Calories: {diet_plan.get('calories', 'N/A')} kcal",
                    body_style,
                )
            )
            macros = diet_plan.get("macros", {})
            if macros:
                elements.append(
                    Paragraph(
                        f"Protein: {macros.get('protein_g', 'N/A')}g | "
                        f"Carbs: {macros.get('carbs_g', 'N/A')}g | "
                        f"Fat: {macros.get('fat_g', 'N/A')}g",
                        body_style,
                    )
                )
            meal_plan = diet_plan.get("meal_plan", [])
            for day in meal_plan[:7]:
                if isinstance(day, dict):
                    day_name = day.get("day", day.get("day_name", ""))
                    if day_name:
                        elements.append(
                            Paragraph(f"<b>{day_name}</b>", body_style)
                        )
                    meals = day.get("meals", [])
                    for meal in meals:
                        if isinstance(meal, dict):
                            meal_name = meal.get("name", "")
                            foods = meal.get("foods", [])
                            food_names = ", ".join(
                                f.get("name", "") for f in foods if isinstance(f, dict)
                            )
                            elements.append(
                                Paragraph(
                                    f"&nbsp;&nbsp;&bull; {meal_name}: {food_names}",
                                    body_style,
                                )
                            )
            elements.append(Spacer(1, 12))

        # ---- Workout Plan ----
        if workout_plan:
            elements.append(Paragraph("Workout Plan", heading_style))
            elements.append(
                Paragraph(
                    f"Goal: {workout_plan.get('goal', 'N/A')} | "
                    f"Difficulty: {workout_plan.get('difficulty', 'N/A')} | "
                    f"Days/week: {workout_plan.get('days_per_week', 'N/A')}",
                    body_style,
                )
            )
            plan_days = workout_plan.get("plan", workout_plan.get("days", []))
            for day in plan_days[:7]:
                if isinstance(day, dict):
                    day_name = day.get("day_name", "")
                    if day_name:
                        elements.append(
                            Paragraph(f"<b>{day_name}</b>", body_style)
                        )
                    exercises = day.get("exercises", [])
                    for ex in exercises:
                        if isinstance(ex, dict):
                            elements.append(
                                Paragraph(
                                    f"&nbsp;&nbsp;&bull; {ex.get('name', '')} - "
                                    f"{ex.get('sets', '')}x{ex.get('reps', '')} "
                                    f"(rest: {ex.get('rest', '60s')})",
                                    body_style,
                                )
                            )
            elements.append(Spacer(1, 12))

        # ---- Supplements ----
        if supplements:
            elements.append(Paragraph("Supplement Suggestions", heading_style))
            elements.append(
                Paragraph(
                    "<i>Non-prescription suggestions only. Consult your healthcare provider.</i>",
                    ParagraphStyle("Disclaimer", parent=body_style, fontSize=9, textColor=colors.grey),
                )
            )
            supp_data = [["Supplement", "Dosage", "Notes"]]
            for s in supplements:
                supp_data.append([
                    s.get("name", ""),
                    s.get("dosage", ""),
                    s.get("notes", ""),
                ])
            supp_table = Table(
                supp_data,
                colWidths=[2 * inch, 1.5 * inch, 2.5 * inch],
            )
            supp_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
                    ]
                )
            )
            elements.append(supp_table)
            elements.append(Spacer(1, 12))

        # ---- Footer ----
        elements.append(Spacer(1, 20))
        elements.append(
            Paragraph(
                "Disclaimer: This report is generated by NutriMed AI for informational purposes only. "
                "It is not a substitute for professional medical advice. Always consult your physician "
                "before making changes to your diet, exercise, or supplement routine.",
                ParagraphStyle(
                    "Footer",
                    parent=body_style,
                    fontSize=8,
                    textColor=colors.grey,
                    alignment=1,
                ),
            )
        )

        doc.build(elements)
        return buffer.getvalue()
