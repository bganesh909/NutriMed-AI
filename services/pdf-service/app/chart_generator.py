"""
Chart generation module using matplotlib.
Generates biomarker charts, progress charts, macro pie charts, and BMI gauges.
"""

import io
import math
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np


def generate_biomarker_bar_chart(biomarkers: list[dict]) -> bytes:
    """
    Generate a horizontal bar chart showing biomarker values with reference range overlay.

    Args:
        biomarkers: List of dicts with name, value, reference_low, reference_high, unit, status

    Returns:
        PNG image bytes
    """
    if not biomarkers:
        return b""

    # Limit to 15 biomarkers per chart for readability
    data = biomarkers[:15]

    fig, ax = plt.subplots(figsize=(10, max(4, len(data) * 0.6)))

    names = [b["name"] for b in data]
    values = [b["value"] for b in data]
    ref_lows = [b["reference_low"] for b in data]
    ref_highs = [b["reference_high"] for b in data]
    statuses = [b.get("status", "normal") for b in data]

    y_pos = np.arange(len(names))

    # Color bars based on status
    colors = []
    for status in statuses:
        if status == "normal":
            colors.append("#4CAF50")  # green
        elif status == "high":
            colors.append("#FF9800")  # orange
        elif status == "low":
            colors.append("#FF9800")  # orange
        elif status == "critical":
            colors.append("#F44336")  # red
        else:
            colors.append("#2196F3")  # blue

    bars = ax.barh(y_pos, values, color=colors, alpha=0.8, height=0.5)

    # Draw reference range as transparent region
    for i, (low, high) in enumerate(zip(ref_lows, ref_highs)):
        max_val = max(values[i], high) * 1.2
        ax.barh(i, high - low, left=low, color="#E0E0E0", alpha=0.3, height=0.7)
        ax.axvline(x=low, color="#9E9E9E", linestyle="--", linewidth=0.5, alpha=0.5)
        ax.axvline(x=high, color="#9E9E9E", linestyle="--", linewidth=0.5, alpha=0.5)

    # Add value labels
    for i, (val, bar) in enumerate(zip(values, bars)):
        unit = data[i].get("unit", "")
        ax.text(val + max(values) * 0.02, i, f" {val} {unit}", va="center", fontsize=8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Value", fontsize=10)
    ax.set_title("Biomarker Analysis", fontsize=13, fontweight="bold", pad=15)

    # Add legend
    legend_elements = [
        patches.Patch(facecolor="#4CAF50", alpha=0.8, label="Normal"),
        patches.Patch(facecolor="#FF9800", alpha=0.8, label="Out of Range"),
        patches.Patch(facecolor="#F44336", alpha=0.8, label="Critical"),
        patches.Patch(facecolor="#E0E0E0", alpha=0.3, label="Reference Range"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=8)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_progress_chart(history: list[dict]) -> bytes:
    """
    Generate line chart showing biomarker progress over time.

    Args:
        history: List of dicts with name, dates, values, unit

    Returns:
        PNG image bytes
    """
    if not history:
        return b""

    fig, ax = plt.subplots(figsize=(10, 5))

    for item in history[:6]:  # Limit to 6 biomarkers for clarity
        ax.plot(item["dates"], item["values"], marker="o", linewidth=2, label=f"{item['name']} ({item['unit']})")

        # Annotate last value
        if item["values"]:
            ax.annotate(
                f"{item['values'][-1]}",
                (item["dates"][-1], item["values"][-1]),
                textcoords="offset points",
                xytext=(10, 5),
                fontsize=8,
            )

    ax.set_xlabel("Date", fontsize=10)
    ax.set_ylabel("Value", fontsize=10)
    ax.set_title("Biomarker Progress Over Time", fontsize=13, fontweight="bold", pad=15)
    ax.legend(fontsize=8, loc="best")
    ax.grid(True, alpha=0.3)

    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_macro_pie_chart(macros: dict) -> bytes:
    """
    Generate pie chart showing macronutrient distribution.

    Args:
        macros: Dict with protein_g, carbs_g, fat_g

    Returns:
        PNG image bytes
    """
    protein = macros.get("protein_g", 0)
    carbs = macros.get("carbs_g", 0)
    fat = macros.get("fat_g", 0)

    if protein + carbs + fat == 0:
        return b""

    labels = [
        f"Protein\n{protein}g",
        f"Carbs\n{carbs}g",
        f"Fat\n{fat}g",
    ]
    sizes = [protein * 4, carbs * 4, fat * 9]  # Convert to calories
    total_cal = sum(sizes)
    percentages = [s / total_cal * 100 if total_cal > 0 else 0 for s in sizes]

    colors = ["#FF6384", "#36A2EB", "#FFCE56"]
    explode = (0.05, 0.05, 0.05)

    fig, ax = plt.subplots(figsize=(6, 6))

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        explode=explode,
        autopct="%1.1f%%",
        shadow=False,
        startangle=140,
        textprops={"fontsize": 10},
    )

    for autotext in autotexts:
        autotext.set_fontsize(9)
        autotext.set_fontweight("bold")

    ax.set_title(
        f"Macronutrient Distribution ({int(total_cal)} kcal)",
        fontsize=13,
        fontweight="bold",
        pad=20,
    )

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def generate_bmi_gauge_chart(bmi: float) -> bytes:
    """
    Generate a semi-circular gauge chart for BMI.

    Args:
        bmi: BMI value

    Returns:
        PNG image bytes
    """
    fig, ax = plt.subplots(figsize=(6, 3.5))

    # BMI categories and their angles on the gauge (0-180 degrees)
    categories = [
        {"label": "Underweight", "range": (0, 18.5), "color": "#2196F3", "angle_start": 0, "angle_end": 37},
        {"label": "Normal", "range": (18.5, 25), "color": "#4CAF50", "angle_start": 37, "angle_end": 90},
        {"label": "Overweight", "range": (25, 30), "color": "#FF9800", "angle_start": 90, "angle_end": 126},
        {"label": "Obese I", "range": (30, 35), "color": "#FF5722", "angle_start": 126, "angle_end": 153},
        {"label": "Obese II+", "range": (35, 50), "color": "#F44336", "angle_start": 153, "angle_end": 180},
    ]

    # Draw gauge arcs
    for cat in categories:
        theta1 = cat["angle_start"]
        theta2 = cat["angle_end"]
        wedge = patches.Wedge(
            center=(0.5, 0),
            r=0.45,
            theta1=theta1,
            theta2=theta2,
            facecolor=cat["color"],
            alpha=0.7,
            width=0.12,
            transform=ax.transAxes,
        )
        ax.add_patch(wedge)

    # Calculate needle angle for BMI
    bmi_clamped = max(10, min(bmi, 50))
    # Map BMI 10-50 to angle 0-180
    needle_angle = (bmi_clamped - 10) / 40 * 180
    needle_rad = math.radians(needle_angle)

    # Draw needle
    needle_length = 0.35
    needle_x = 0.5 + needle_length * math.cos(needle_rad)
    needle_y = needle_length * math.sin(needle_rad)
    ax.annotate(
        "",
        xy=(needle_x, needle_y),
        xytext=(0.5, 0),
        arrowprops=dict(arrowstyle="->", color="black", lw=2),
        transform=ax.transAxes,
    )

    # Center circle
    circle = plt.Circle((0.5, 0), 0.03, color="black", transform=ax.transAxes, zorder=5)
    ax.add_patch(circle)

    # BMI value text
    ax.text(
        0.5, -0.1, f"BMI: {bmi:.1f}",
        ha="center", va="center", fontsize=16, fontweight="bold",
        transform=ax.transAxes,
    )

    # Category label
    category_name = "Normal"
    for cat in categories:
        if cat["range"][0] <= bmi < cat["range"][1]:
            category_name = cat["label"]
            break
    if bmi >= 50:
        category_name = "Obese II+"

    ax.text(
        0.5, -0.2, category_name,
        ha="center", va="center", fontsize=12, fontstyle="italic",
        transform=ax.transAxes,
    )

    # Category labels on gauge
    label_positions = [
        (0.12, 0.15, "Under-\nweight", 8),
        (0.32, 0.38, "Normal", 8),
        (0.68, 0.38, "Over-\nweight", 8),
        (0.85, 0.18, "Obese", 8),
    ]
    for x, y, label, size in label_positions:
        ax.text(x, y, label, ha="center", va="center", fontsize=size, alpha=0.7, transform=ax.transAxes)

    ax.set_xlim(-0.1, 1.1)
    ax.set_ylim(-0.3, 0.6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Body Mass Index (BMI)", fontsize=13, fontweight="bold", pad=10)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()
