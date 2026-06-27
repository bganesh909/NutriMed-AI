"""
PDF report generator using ReportLab.
Generates professional health reports, diet plans, and workout plans.
"""

import io
import os
import uuid
import logging
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    HRFlowable,
)
from reportlab.platypus.frames import Frame
from reportlab.platypus.doctemplate import PageTemplate

from app.config import get_settings
from app.chart_generator import (
    generate_biomarker_bar_chart,
    generate_progress_chart,
    generate_macro_pie_chart,
    generate_bmi_gauge_chart,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Brand colors
BRAND_PRIMARY = colors.HexColor("#1565C0")
BRAND_SECONDARY = colors.HexColor("#42A5F5")
BRAND_ACCENT = colors.HexColor("#0D47A1")
BRAND_LIGHT = colors.HexColor("#E3F2FD")
STATUS_GREEN = colors.HexColor("#4CAF50")
STATUS_YELLOW = colors.HexColor("#FF9800")
STATUS_RED = colors.HexColor("#F44336")
GRAY_LIGHT = colors.HexColor("#F5F5F5")
GRAY_MEDIUM = colors.HexColor("#9E9E9E")
GRAY_DARK = colors.HexColor("#424242")

PAGE_WIDTH, PAGE_HEIGHT = A4


def _get_styles():
    """Get custom paragraph styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="BrandTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=BRAND_PRIMARY,
        spaceAfter=6,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=BRAND_PRIMARY,
        spaceBefore=16,
        spaceAfter=8,
        borderColor=BRAND_PRIMARY,
        borderWidth=1,
        borderPadding=4,
    ))
    styles.add(ParagraphStyle(
        name="SubHeader",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=BRAND_ACCENT,
        spaceBefore=10,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="BodySmall",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
    ))
    styles.add(ParagraphStyle(
        name="Disclaimer",
        parent=styles["Normal"],
        fontSize=7,
        textColor=GRAY_MEDIUM,
        alignment=TA_CENTER,
        spaceBefore=10,
    ))
    styles.add(ParagraphStyle(
        name="FooterStyle",
        parent=styles["Normal"],
        fontSize=7,
        textColor=GRAY_MEDIUM,
        alignment=TA_CENTER,
    ))

    return styles


def _header_footer(canvas, doc):
    """Add header and footer to each page."""
    canvas.saveState()

    # Header
    canvas.setFillColor(BRAND_PRIMARY)
    canvas.rect(0, PAGE_HEIGHT - 35, PAGE_WIDTH, 35, fill=True, stroke=False)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(20, PAGE_HEIGHT - 25, "NutriMed AI")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_WIDTH - 20, PAGE_HEIGHT - 25, "Health & Nutrition Report")

    # Footer
    canvas.setFillColor(GRAY_LIGHT)
    canvas.rect(0, 0, PAGE_WIDTH, 30, fill=True, stroke=False)
    canvas.setFillColor(GRAY_MEDIUM)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(20, 12, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.drawCentredString(PAGE_WIDTH / 2, 12, "NutriMed AI - AI-Powered Health & Nutrition Platform")
    canvas.drawRightString(PAGE_WIDTH - 20, 12, f"Page {doc.page}")

    canvas.restoreState()


def _status_color(status: str) -> colors.Color:
    """Get color for biomarker status."""
    if status == "normal":
        return STATUS_GREEN
    elif status in ("high", "low"):
        return STATUS_YELLOW
    elif status == "critical":
        return STATUS_RED
    return GRAY_MEDIUM


def _severity_color(severity: str) -> colors.Color:
    """Get color for risk severity."""
    if severity == "low":
        return STATUS_GREEN
    elif severity == "moderate":
        return STATUS_YELLOW
    elif severity in ("high", "critical"):
        return STATUS_RED
    return GRAY_MEDIUM


def _build_patient_info_section(patient: dict, styles) -> list:
    """Build patient info table."""
    elements = []

    elements.append(Paragraph("Patient Information", styles["SectionHeader"]))

    data = [
        ["Name", patient.get("name", "N/A"), "Age", f"{patient.get('age', 'N/A')} years"],
        ["Gender", patient.get("gender", "N/A").title(), "Weight", f"{patient.get('weight_kg', 'N/A')} kg"],
        ["Height", f"{patient.get('height_cm', 'N/A')} cm", "Blood Group", patient.get("blood_group", "N/A")],
    ]

    report_date = patient.get("report_date") or datetime.now().strftime("%Y-%m-%d")
    data.append(["Report Date", report_date, "", ""])

    table = Table(data, colWidths=[80, 150, 80, 150])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BRAND_LIGHT),
        ("BACKGROUND", (2, 0), (2, -1), BRAND_LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), BRAND_ACCENT),
        ("TEXTCOLOR", (2, 0), (2, -1), BRAND_ACCENT),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    return elements


def _build_biomarker_section(biomarkers: list[dict], styles) -> list:
    """Build biomarker summary table with color-coded status."""
    if not biomarkers:
        return []

    elements = []
    elements.append(Paragraph("Biomarker Analysis", styles["SectionHeader"]))

    # Header row
    header = ["Biomarker", "Value", "Unit", "Reference Range", "Status"]
    data = [header]

    for bio in biomarkers:
        status = bio.get("status", "normal")
        ref_range = f"{bio.get('reference_low', '')}-{bio.get('reference_high', '')}"
        row = [
            bio.get("name", ""),
            str(bio.get("value", "")),
            bio.get("unit", ""),
            ref_range,
            status.upper(),
        ]
        data.append(row)

    table = Table(data, colWidths=[130, 60, 60, 100, 70])

    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, GRAY_MEDIUM),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]

    # Color-code status cells
    for i, bio in enumerate(biomarkers):
        row_idx = i + 1
        status = bio.get("status", "normal")
        bg_color = _status_color(status)
        style_commands.append(("BACKGROUND", (4, row_idx), (4, row_idx), bg_color))
        style_commands.append(("TEXTCOLOR", (4, row_idx), (4, row_idx), colors.white))
        style_commands.append(("FONTNAME", (4, row_idx), (4, row_idx), "Helvetica-Bold"))

        # Alternate row shading
        if row_idx % 2 == 0:
            style_commands.append(("BACKGROUND", (0, row_idx), (3, row_idx), GRAY_LIGHT))

    table.setStyle(TableStyle(style_commands))
    elements.append(table)
    elements.append(Spacer(1, 8))

    # Add biomarker chart
    chart_data = [
        {
            "name": b.get("name", ""),
            "value": b.get("value", 0),
            "reference_low": b.get("reference_low", 0),
            "reference_high": b.get("reference_high", 0),
            "unit": b.get("unit", ""),
            "status": b.get("status", "normal"),
        }
        for b in biomarkers
    ]
    chart_bytes = generate_biomarker_bar_chart(chart_data)
    if chart_bytes:
        img = Image(io.BytesIO(chart_bytes), width=450, height=max(150, len(biomarkers) * 22))
        elements.append(img)
        elements.append(Spacer(1, 12))

    return elements


def _build_risk_factors_section(risk_factors: list[dict], deficiencies: list[str], styles) -> list:
    """Build risk factors and deficiencies section."""
    elements = []

    if risk_factors or deficiencies:
        elements.append(Paragraph("Risk Factors & Deficiencies", styles["SectionHeader"]))

    if risk_factors:
        for rf in risk_factors:
            severity = rf.get("severity", "moderate")
            color = _severity_color(severity)
            elements.append(Paragraph(
                f'<font color="{color.hexval()}">[{severity.upper()}]</font> '
                f'<b>{rf.get("name", "")}</b>: {rf.get("description", "")}',
                styles["BodySmall"],
            ))
            elements.append(Spacer(1, 4))

    if deficiencies:
        elements.append(Paragraph("Identified Deficiencies:", styles["SubHeader"]))
        for deficiency in deficiencies:
            elements.append(Paragraph(f"  - {deficiency}", styles["BodySmall"]))
        elements.append(Spacer(1, 8))

    return elements


def _build_diet_section(diet_plan: list[dict], styles) -> list:
    """Build diet plan section with meal tables."""
    if not diet_plan:
        return []

    elements = []
    elements.append(Paragraph("Diet Plan", styles["SectionHeader"]))

    for day_plan in diet_plan:
        elements.append(Paragraph(f"<b>{day_plan.get('day', '')}</b> (Total: {day_plan.get('total_calories', 0):.0f} kcal)", styles["SubHeader"]))

        header = ["Meal", "Time", "Food Item", "Qty", "Cal", "P(g)", "C(g)", "F(g)"]
        data = [header]

        for meal in day_plan.get("meals", []):
            meal_type = meal.get("meal_type", "")
            time = meal.get("time", "")
            for j, item in enumerate(meal.get("items", [])):
                row = [
                    meal_type if j == 0 else "",
                    time if j == 0 else "",
                    item.get("name", ""),
                    item.get("quantity", ""),
                    f"{item.get('calories', 0):.0f}",
                    f"{item.get('protein_g', 0):.1f}",
                    f"{item.get('carbs_g', 0):.1f}",
                    f"{item.get('fat_g', 0):.1f}",
                ]
                data.append(row)

        col_widths = [65, 50, 120, 55, 35, 35, 35, 35]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_SECONDARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (4, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, GRAY_MEDIUM),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))

    return elements


def _build_workout_section(workout_plan: list[dict], styles) -> list:
    """Build workout plan section with exercise tables."""
    if not workout_plan:
        return []

    elements = []
    elements.append(Paragraph("Workout Plan", styles["SectionHeader"]))

    for session in workout_plan:
        elements.append(Paragraph(
            f"<b>{session.get('day', '')}</b> - {session.get('focus', '')}",
            styles["SubHeader"],
        ))

        header = ["Exercise", "Sets", "Reps", "Rest", "Notes"]
        data = [header]

        for ex in session.get("exercises", []):
            data.append([
                ex.get("name", ""),
                str(ex.get("sets", "")),
                str(ex.get("reps", "")),
                f"{ex.get('rest_seconds', 60)}s",
                ex.get("notes", "") or "",
            ])

        table = Table(data, colWidths=[150, 35, 50, 40, 155])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND_SECONDARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (1, 0), (3, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.3, GRAY_MEDIUM),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))

    return elements


def _build_supplements_section(supplements: list[dict], styles) -> list:
    """Build supplement recommendations section."""
    if not supplements:
        return []

    elements = []
    elements.append(Paragraph("Supplement Recommendations", styles["SectionHeader"]))

    header = ["Supplement", "Dosage", "Timing", "Reason"]
    data = [header]
    for supp in supplements:
        data.append([
            supp.get("name", ""),
            supp.get("dosage", ""),
            supp.get("timing", ""),
            supp.get("reason", ""),
        ])

    table = Table(data, colWidths=[100, 80, 80, 170])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_SECONDARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, GRAY_MEDIUM),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 12))

    return elements


def _build_disclaimer(styles) -> list:
    """Build disclaimer section."""
    return [
        Spacer(1, 20),
        HRFlowable(width="100%", thickness=0.5, color=GRAY_MEDIUM),
        Paragraph(
            "DISCLAIMER: This report is generated by NutriMed AI for informational purposes only. "
            "It is not a substitute for professional medical advice, diagnosis, or treatment. "
            "Always consult your physician or qualified healthcare provider before making changes to your diet, "
            "exercise routine, or supplement regimen. The recommendations are based on the data provided and "
            "general health guidelines. Individual results may vary.",
            styles["Disclaimer"],
        ),
    ]


def generate_health_report(report_data: dict) -> dict:
    """
    Generate a comprehensive health report PDF.

    Args:
        report_data: Dict containing patient info, biomarkers, diet, workout, etc.

    Returns:
        Dict with filename, file_path, file_size_bytes
    """
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    filename = f"health_report_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(settings.OUTPUT_DIR, filename)

    styles = _get_styles()

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=45,
        bottomMargin=40,
        leftMargin=30,
        rightMargin=30,
    )

    elements = []

    # Title
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("NutriMed AI", styles["BrandTitle"]))
    elements.append(Paragraph("Comprehensive Health & Nutrition Report", styles["Heading3"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY))
    elements.append(Spacer(1, 12))

    # Patient info
    patient = report_data.get("patient", {})
    elements.extend(_build_patient_info_section(patient, styles))

    # BMI section
    bmi = report_data.get("bmi")
    if bmi:
        bmi_category = report_data.get("bmi_category", "")
        elements.append(Paragraph(f"<b>BMI:</b> {bmi:.1f} ({bmi_category})", styles["Normal"]))
        elements.append(Spacer(1, 4))

        bmi_chart = generate_bmi_gauge_chart(bmi)
        if bmi_chart:
            img = Image(io.BytesIO(bmi_chart), width=280, height=160)
            elements.append(img)
            elements.append(Spacer(1, 8))

    # Macros chart
    macros = report_data.get("macros")
    if macros:
        macro_chart = generate_macro_pie_chart(macros)
        if macro_chart:
            elements.append(Paragraph("Macronutrient Distribution", styles["SubHeader"]))
            img = Image(io.BytesIO(macro_chart), width=250, height=250)
            elements.append(img)
            elements.append(Spacer(1, 8))

    # Biomarkers
    biomarkers = report_data.get("biomarkers", [])
    if biomarkers:
        bio_dicts = [b if isinstance(b, dict) else b.dict() for b in biomarkers]
        elements.extend(_build_biomarker_section(bio_dicts, styles))

    # Progress charts
    history = report_data.get("biomarker_history")
    if history:
        hist_dicts = [h if isinstance(h, dict) else h.dict() for h in history]
        progress_chart = generate_progress_chart(hist_dicts)
        if progress_chart:
            elements.append(Paragraph("Progress Tracking", styles["SectionHeader"]))
            img = Image(io.BytesIO(progress_chart), width=450, height=220)
            elements.append(img)
            elements.append(Spacer(1, 12))

    # Risk factors
    risk_factors = report_data.get("risk_factors", [])
    deficiencies = report_data.get("deficiencies", [])
    rf_dicts = [r if isinstance(r, dict) else r.dict() for r in risk_factors]
    elements.extend(_build_risk_factors_section(rf_dicts, deficiencies, styles))

    # Diet plan
    diet_plan = report_data.get("diet_plan")
    if diet_plan:
        dp_dicts = [d if isinstance(d, dict) else d.dict() for d in diet_plan]
        elements.extend(_build_diet_section(dp_dicts, styles))

    # Workout plan
    workout_plan = report_data.get("workout_plan")
    if workout_plan:
        wp_dicts = [w if isinstance(w, dict) else w.dict() for w in workout_plan]
        elements.extend(_build_workout_section(wp_dicts, styles))

    # Supplements
    supplements = report_data.get("supplements", [])
    if supplements:
        s_dicts = [s if isinstance(s, dict) else s.dict() for s in supplements]
        elements.extend(_build_supplements_section(s_dicts, styles))

    # Notes
    notes = report_data.get("notes", [])
    if notes:
        elements.append(Paragraph("Additional Notes", styles["SectionHeader"]))
        for note in notes:
            elements.append(Paragraph(f"- {note}", styles["BodySmall"]))
        elements.append(Spacer(1, 8))

    # Disclaimer
    elements.extend(_build_disclaimer(styles))

    # Build PDF
    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)

    file_size = os.path.getsize(file_path)

    return {
        "filename": filename,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "message": "Health report generated successfully",
    }


def generate_diet_plan_pdf(data: dict) -> dict:
    """Generate a diet plan PDF."""
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    filename = f"diet_plan_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(settings.OUTPUT_DIR, filename)

    styles = _get_styles()

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=45,
        bottomMargin=40,
        leftMargin=30,
        rightMargin=30,
    )

    elements = []

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("NutriMed AI", styles["BrandTitle"]))
    elements.append(Paragraph("Personalized Diet Plan", styles["Heading3"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY))
    elements.append(Spacer(1, 12))

    # Patient info
    patient = data.get("patient", {})
    elements.extend(_build_patient_info_section(patient, styles))

    # Target info
    target_cal = data.get("target_calories", 0)
    macros = data.get("macros", {})
    pref = data.get("dietary_preference", "")

    elements.append(Paragraph(
        f"<b>Target Calories:</b> {target_cal} kcal | "
        f"<b>Preference:</b> {pref.replace('_', ' ').title()} | "
        f"<b>Protein:</b> {macros.get('protein_g', 0)}g | "
        f"<b>Carbs:</b> {macros.get('carbs_g', 0)}g | "
        f"<b>Fat:</b> {macros.get('fat_g', 0)}g",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 8))

    # Macro pie chart
    if macros:
        macro_chart = generate_macro_pie_chart(macros)
        if macro_chart:
            img = Image(io.BytesIO(macro_chart), width=220, height=220)
            elements.append(img)
            elements.append(Spacer(1, 8))

    # Diet tables
    diet_plan = data.get("diet_plan", [])
    dp_dicts = [d if isinstance(d, dict) else d.dict() for d in diet_plan]
    elements.extend(_build_diet_section(dp_dicts, styles))

    # Notes
    notes = data.get("notes", [])
    if notes:
        elements.append(Paragraph("Notes & Guidelines", styles["SectionHeader"]))
        for note in notes:
            elements.append(Paragraph(f"- {note}", styles["BodySmall"]))

    elements.extend(_build_disclaimer(styles))

    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    file_size = os.path.getsize(file_path)

    return {
        "filename": filename,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "message": "Diet plan PDF generated successfully",
    }


def generate_workout_plan_pdf(data: dict) -> dict:
    """Generate a workout plan PDF."""
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    filename = f"workout_plan_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(settings.OUTPUT_DIR, filename)

    styles = _get_styles()

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=45,
        bottomMargin=40,
        leftMargin=30,
        rightMargin=30,
    )

    elements = []

    elements.append(Spacer(1, 10))
    elements.append(Paragraph("NutriMed AI", styles["BrandTitle"]))
    elements.append(Paragraph("Personalized Workout Plan", styles["Heading3"]))
    elements.append(HRFlowable(width="100%", thickness=2, color=BRAND_PRIMARY))
    elements.append(Spacer(1, 12))

    # Patient info
    patient = data.get("patient", {})
    elements.extend(_build_patient_info_section(patient, styles))

    # Plan summary
    fitness_level = data.get("fitness_level", "")
    goal = data.get("goal", "")
    days = data.get("days_per_week", 0)

    elements.append(Paragraph(
        f"<b>Fitness Level:</b> {fitness_level.title()} | "
        f"<b>Goal:</b> {goal.replace('_', ' ').title()} | "
        f"<b>Days/Week:</b> {days}",
        styles["Normal"],
    ))
    elements.append(Spacer(1, 12))

    # Workout tables
    workout_plan = data.get("workout_plan", [])
    wp_dicts = [w if isinstance(w, dict) else w.dict() for w in workout_plan]
    elements.extend(_build_workout_section(wp_dicts, styles))

    # Notes
    notes = data.get("notes", [])
    if notes:
        elements.append(Paragraph("Training Notes", styles["SectionHeader"]))
        for note in notes:
            elements.append(Paragraph(f"- {note}", styles["BodySmall"]))

    elements.extend(_build_disclaimer(styles))

    doc.build(elements, onFirstPage=_header_footer, onLaterPages=_header_footer)
    file_size = os.path.getsize(file_path)

    return {
        "filename": filename,
        "file_path": file_path,
        "file_size_bytes": file_size,
        "message": "Workout plan PDF generated successfully",
    }
