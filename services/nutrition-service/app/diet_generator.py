"""
Diet plan generation module.
Generates template-based diet plans with optional LLM personalization.
Supports multiple cuisines, dietary preferences, and medical conditions.
"""

import logging
import random
from typing import Optional

import httpx

from app.calculator import calculate_bmr, calculate_tdee, calculate_macros, calculate_hydration
from app.food_database import get_foods_by_preference, search_foods
from app.config import get_settings

logger = logging.getLogger(__name__)


# ---- Meal Templates ----

INDIAN_VEGETARIAN_TEMPLATES = {
    "early_morning": [
        [{"name": "Warm Lemon Water", "qty": "250ml", "cal": 5, "p": 0, "c": 1, "f": 0}],
        [{"name": "Soaked Almonds", "qty": "6 pieces (10g)", "cal": 58, "p": 2.1, "c": 2.2, "f": 5.0},
         {"name": "Warm Water", "qty": "250ml", "cal": 0, "p": 0, "c": 0, "f": 0}],
    ],
    "breakfast": [
        [{"name": "Oats Porridge with Milk", "qty": "200ml", "cal": 220, "p": 9, "c": 35, "f": 5},
         {"name": "Banana", "qty": "1 medium (120g)", "cal": 107, "p": 1.3, "c": 27, "f": 0.4},
         {"name": "Chia Seeds", "qty": "1 tbsp (10g)", "cal": 49, "p": 1.7, "c": 4.2, "f": 3.1}],
        [{"name": "Idli", "qty": "3 pieces (120g)", "cal": 117, "p": 6, "c": 24, "f": 0.3},
         {"name": "Sambar", "qty": "1 bowl (150ml)", "cal": 98, "p": 4.8, "c": 15, "f": 2.3},
         {"name": "Coconut Chutney", "qty": "2 tbsp", "cal": 50, "p": 0.5, "c": 3, "f": 4}],
        [{"name": "Moong Dal Chilla", "qty": "2 pieces", "cal": 180, "p": 12, "c": 22, "f": 4},
         {"name": "Curd", "qty": "100g", "cal": 60, "p": 3.1, "c": 4.7, "f": 3.1},
         {"name": "Green Chutney", "qty": "2 tbsp", "cal": 15, "p": 0.5, "c": 2, "f": 0.5}],
        [{"name": "Poha", "qty": "1 plate (200g)", "cal": 320, "p": 7, "c": 60, "f": 6},
         {"name": "Buttermilk", "qty": "200ml", "cal": 40, "p": 3.3, "c": 4.8, "f": 0.9}],
        [{"name": "Multigrain Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 36, "f": 3},
         {"name": "Paneer Bhurji", "qty": "100g", "cal": 220, "p": 14, "c": 4, "f": 16}],
    ],
    "mid_morning": [
        [{"name": "Mixed Fruit Bowl", "qty": "150g", "cal": 80, "p": 1, "c": 20, "f": 0.3}],
        [{"name": "Sprouts Salad", "qty": "100g", "cal": 100, "p": 7, "c": 15, "f": 1}],
        [{"name": "Buttermilk", "qty": "200ml", "cal": 40, "p": 3.3, "c": 4.8, "f": 0.9},
         {"name": "Roasted Chana", "qty": "30g", "cal": 110, "p": 6.5, "c": 18, "f": 1.5}],
        [{"name": "Greek Yogurt", "qty": "100g", "cal": 97, "p": 9, "c": 3.6, "f": 5},
         {"name": "Walnuts", "qty": "5 pieces (15g)", "cal": 98, "p": 2.3, "c": 2.1, "f": 9.8}],
    ],
    "lunch": [
        [{"name": "Brown Rice", "qty": "150g cooked", "cal": 185, "p": 4.1, "c": 38, "f": 1.5},
         {"name": "Dal Tadka", "qty": "1 bowl (150ml)", "cal": 180, "p": 9.8, "c": 24, "f": 5.3},
         {"name": "Mixed Veg Sabzi", "qty": "150g", "cal": 90, "p": 3, "c": 12, "f": 3.5},
         {"name": "Cucumber Raita", "qty": "100g", "cal": 50, "p": 2.5, "c": 4, "f": 2.5},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2}],
        [{"name": "Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 40, "f": 1},
         {"name": "Chole", "qty": "1 bowl (150g)", "cal": 240, "p": 11.3, "c": 33, "f": 7.5},
         {"name": "Onion Salad", "qty": "50g", "cal": 20, "p": 0.6, "c": 4.7, "f": 0.1},
         {"name": "Curd", "qty": "100g", "cal": 60, "p": 3.1, "c": 4.7, "f": 3.1}],
        [{"name": "Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 40, "f": 1},
         {"name": "Palak Paneer", "qty": "150g", "cal": 240, "p": 12, "c": 9, "f": 18},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2}],
    ],
    "evening_snack": [
        [{"name": "Green Tea", "qty": "1 cup", "cal": 2, "p": 0, "c": 0, "f": 0},
         {"name": "Roasted Makhana", "qty": "30g", "cal": 100, "p": 3, "c": 18, "f": 0.3}],
        [{"name": "Fruit Smoothie", "qty": "250ml", "cal": 150, "p": 5, "c": 28, "f": 2}],
        [{"name": "Peanuts (roasted)", "qty": "30g", "cal": 170, "p": 7.7, "c": 4.8, "f": 14.8}],
        [{"name": "Sprout Chaat", "qty": "100g", "cal": 120, "p": 7, "c": 18, "f": 2}],
    ],
    "dinner": [
        [{"name": "Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 40, "f": 1},
         {"name": "Moong Dal", "qty": "1 bowl (150ml)", "cal": 158, "p": 10.5, "c": 28.5, "f": 0.6},
         {"name": "Stir-fried Vegetables", "qty": "150g", "cal": 80, "p": 3, "c": 10, "f": 3}],
        [{"name": "Khichdi", "qty": "200g", "cal": 210, "p": 7, "c": 38, "f": 3},
         {"name": "Curd", "qty": "100g", "cal": 60, "p": 3.1, "c": 4.7, "f": 3.1},
         {"name": "Papad (roasted)", "qty": "1 piece", "cal": 35, "p": 2, "c": 5, "f": 1}],
        [{"name": "Bajra Roti", "qty": "2 pieces", "cal": 220, "p": 7, "c": 42, "f": 3},
         {"name": "Toor Dal", "qty": "1 bowl (150ml)", "cal": 177, "p": 11.6, "c": 31.5, "f": 0.6},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2}],
    ],
    "bedtime": [
        [{"name": "Warm Turmeric Milk", "qty": "200ml", "cal": 100, "p": 5, "c": 10, "f": 4}],
        [{"name": "Warm Milk with Nutmeg", "qty": "200ml", "cal": 90, "p": 5, "c": 9, "f": 4}],
    ],
}

INDIAN_NON_VEG_TEMPLATES = {
    "early_morning": INDIAN_VEGETARIAN_TEMPLATES["early_morning"],
    "breakfast": [
        [{"name": "Egg Omelette", "qty": "2 eggs", "cal": 180, "p": 12, "c": 2, "f": 14},
         {"name": "Multigrain Toast", "qty": "2 slices", "cal": 160, "p": 8, "c": 26, "f": 2.5}],
        [{"name": "Boiled Eggs", "qty": "3 whole", "cal": 234, "p": 18.6, "c": 1.6, "f": 16},
         {"name": "Roti", "qty": "1 piece", "cal": 100, "p": 3.5, "c": 20, "f": 0.5}],
        *INDIAN_VEGETARIAN_TEMPLATES["breakfast"][:2],
    ],
    "mid_morning": INDIAN_VEGETARIAN_TEMPLATES["mid_morning"],
    "lunch": [
        [{"name": "Brown Rice", "qty": "150g cooked", "cal": 185, "p": 4.1, "c": 38, "f": 1.5},
         {"name": "Chicken Curry", "qty": "150g", "cal": 225, "p": 22.5, "c": 7.5, "f": 12},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2},
         {"name": "Curd", "qty": "100g", "cal": 60, "p": 3.1, "c": 4.7, "f": 3.1}],
        [{"name": "Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 40, "f": 1},
         {"name": "Fish Curry", "qty": "150g", "cal": 180, "p": 21, "c": 6, "f": 8.3},
         {"name": "Dal", "qty": "1 bowl (100ml)", "cal": 120, "p": 6.5, "c": 16, "f": 3.5},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2}],
        *INDIAN_VEGETARIAN_TEMPLATES["lunch"][:1],
    ],
    "evening_snack": INDIAN_VEGETARIAN_TEMPLATES["evening_snack"],
    "dinner": [
        [{"name": "Roti", "qty": "2 pieces", "cal": 200, "p": 7, "c": 40, "f": 1},
         {"name": "Grilled Chicken Breast", "qty": "150g", "cal": 248, "p": 46.5, "c": 0, "f": 5.4},
         {"name": "Stir-fried Vegetables", "qty": "150g", "cal": 80, "p": 3, "c": 10, "f": 3}],
        [{"name": "Brown Rice", "qty": "100g cooked", "cal": 123, "p": 2.7, "c": 25.6, "f": 1},
         {"name": "Egg Curry", "qty": "2 eggs", "cal": 220, "p": 14, "c": 6, "f": 16},
         {"name": "Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2}],
        *INDIAN_VEGETARIAN_TEMPLATES["dinner"][:1],
    ],
    "bedtime": INDIAN_VEGETARIAN_TEMPLATES["bedtime"],
}

WESTERN_TEMPLATES = {
    "breakfast": [
        [{"name": "Scrambled Eggs", "qty": "3 eggs", "cal": 270, "p": 18, "c": 3, "f": 21},
         {"name": "Whole Wheat Toast", "qty": "2 slices", "cal": 160, "p": 8, "c": 26, "f": 2.5},
         {"name": "Avocado", "qty": "50g", "cal": 80, "p": 1, "c": 4.3, "f": 7.4}],
        [{"name": "Overnight Oats", "qty": "200g", "cal": 280, "p": 12, "c": 42, "f": 7},
         {"name": "Blueberries", "qty": "80g", "cal": 46, "p": 0.6, "c": 11.6, "f": 0.2},
         {"name": "Almond Butter", "qty": "1 tbsp (16g)", "cal": 98, "p": 3.4, "c": 3, "f": 8.9}],
        [{"name": "Greek Yogurt Parfait", "qty": "200g yogurt", "cal": 194, "p": 18, "c": 7.2, "f": 10},
         {"name": "Granola", "qty": "40g", "cal": 180, "p": 4, "c": 28, "f": 6},
         {"name": "Mixed Berries", "qty": "80g", "cal": 40, "p": 0.6, "c": 9, "f": 0.3}],
    ],
    "mid_morning": [
        [{"name": "Apple", "qty": "1 medium (180g)", "cal": 94, "p": 0.5, "c": 24.8, "f": 0.4},
         {"name": "Almonds", "qty": "15g", "cal": 87, "p": 3.2, "c": 3.3, "f": 7.5}],
        [{"name": "Protein Shake", "qty": "300ml", "cal": 180, "p": 25, "c": 10, "f": 3}],
    ],
    "lunch": [
        [{"name": "Grilled Chicken Salad", "qty": "300g", "cal": 350, "p": 35, "c": 15, "f": 16},
         {"name": "Olive Oil Dressing", "qty": "1 tbsp", "cal": 120, "p": 0, "c": 0, "f": 14}],
        [{"name": "Turkey & Avocado Wrap", "qty": "1 wrap", "cal": 380, "p": 28, "c": 32, "f": 16},
         {"name": "Side Salad", "qty": "100g", "cal": 25, "p": 1, "c": 5, "f": 0.3}],
        [{"name": "Quinoa Bowl with Grilled Veggies", "qty": "300g", "cal": 380, "p": 14, "c": 52, "f": 12},
         {"name": "Grilled Chicken", "qty": "100g", "cal": 165, "p": 31, "c": 0, "f": 3.6}],
    ],
    "evening_snack": [
        [{"name": "Protein Bar", "qty": "1 bar (60g)", "cal": 200, "p": 20, "c": 22, "f": 7}],
        [{"name": "Cottage Cheese", "qty": "100g", "cal": 72, "p": 12.4, "c": 2.7, "f": 1},
         {"name": "Cherry Tomatoes", "qty": "80g", "cal": 14, "p": 0.7, "c": 3.1, "f": 0.2}],
    ],
    "dinner": [
        [{"name": "Grilled Salmon", "qty": "150g", "cal": 312, "p": 30, "c": 0, "f": 19.5},
         {"name": "Steamed Broccoli", "qty": "150g", "cal": 53, "p": 3.6, "c": 10.8, "f": 0.6},
         {"name": "Sweet Potato", "qty": "150g", "cal": 135, "p": 3, "c": 31, "f": 0.2}],
        [{"name": "Lean Beef Stir-fry", "qty": "200g", "cal": 300, "p": 28, "c": 12, "f": 15},
         {"name": "Brown Rice", "qty": "100g cooked", "cal": 123, "p": 2.7, "c": 25.6, "f": 1}],
        [{"name": "Baked Chicken Breast", "qty": "150g", "cal": 248, "p": 46.5, "c": 0, "f": 5.4},
         {"name": "Roasted Vegetables", "qty": "200g", "cal": 100, "p": 3, "c": 15, "f": 4},
         {"name": "Quinoa", "qty": "100g cooked", "cal": 120, "p": 4.4, "c": 21.3, "f": 1.9}],
    ],
}

MEDITERRANEAN_TEMPLATES = {
    "breakfast": [
        [{"name": "Whole Grain Toast with Olive Oil", "qty": "2 slices", "cal": 200, "p": 6, "c": 28, "f": 8},
         {"name": "Tomato & Cucumber Salad", "qty": "100g", "cal": 20, "p": 1, "c": 4, "f": 0.2},
         {"name": "Feta Cheese", "qty": "30g", "cal": 79, "p": 4.3, "c": 1.2, "f": 6.4},
         {"name": "Olives", "qty": "30g", "cal": 44, "p": 0.3, "c": 1.8, "f": 4.1}],
        [{"name": "Shakshuka (2 eggs)", "qty": "250g", "cal": 280, "p": 16, "c": 12, "f": 18},
         {"name": "Whole Grain Pita", "qty": "1 piece", "cal": 130, "p": 5, "c": 24, "f": 1.5}],
    ],
    "mid_morning": [
        [{"name": "Hummus", "qty": "50g", "cal": 85, "p": 3.5, "c": 8, "f": 4.5},
         {"name": "Carrot Sticks", "qty": "80g", "cal": 33, "p": 0.7, "c": 7.7, "f": 0.2}],
        [{"name": "Mixed Nuts", "qty": "30g", "cal": 175, "p": 5, "c": 7, "f": 15}],
    ],
    "lunch": [
        [{"name": "Grilled Fish", "qty": "150g", "cal": 180, "p": 30, "c": 0, "f": 6},
         {"name": "Greek Salad", "qty": "200g", "cal": 120, "p": 5, "c": 8, "f": 8},
         {"name": "Couscous", "qty": "100g cooked", "cal": 112, "p": 3.8, "c": 23, "f": 0.2}],
        [{"name": "Falafel", "qty": "4 pieces (120g)", "cal": 200, "p": 8, "c": 22, "f": 10},
         {"name": "Tabbouleh", "qty": "100g", "cal": 90, "p": 2.5, "c": 12, "f": 4},
         {"name": "Hummus", "qty": "50g", "cal": 85, "p": 3.5, "c": 8, "f": 4.5}],
    ],
    "evening_snack": [
        [{"name": "Greek Yogurt with Honey", "qty": "150g", "cal": 180, "p": 13, "c": 18, "f": 5}],
        [{"name": "Dates", "qty": "3 pieces (30g)", "cal": 83, "p": 0.5, "c": 22.5, "f": 0.1},
         {"name": "Almonds", "qty": "10g", "cal": 58, "p": 2.1, "c": 2.2, "f": 5}],
    ],
    "dinner": [
        [{"name": "Grilled Lamb Kebab", "qty": "120g", "cal": 230, "p": 22, "c": 3, "f": 14},
         {"name": "Roasted Vegetables with Olive Oil", "qty": "200g", "cal": 130, "p": 3, "c": 15, "f": 7},
         {"name": "Whole Wheat Pita", "qty": "1 piece", "cal": 130, "p": 5, "c": 24, "f": 1.5}],
        [{"name": "Baked Salmon", "qty": "150g", "cal": 312, "p": 30, "c": 0, "f": 19.5},
         {"name": "Lentil Soup", "qty": "200ml", "cal": 116, "p": 9, "c": 20, "f": 0.4},
         {"name": "Mixed Green Salad", "qty": "100g", "cal": 20, "p": 1.5, "c": 3, "f": 0.3}],
    ],
}


CUISINE_TEMPLATES = {
    "indian": {
        "vegetarian": INDIAN_VEGETARIAN_TEMPLATES,
        "non_vegetarian": INDIAN_NON_VEG_TEMPLATES,
        "vegan": INDIAN_VEGETARIAN_TEMPLATES,  # filter dairy
        "eggetarian": INDIAN_NON_VEG_TEMPLATES,
    },
    "western": {
        "vegetarian": WESTERN_TEMPLATES,
        "non_vegetarian": WESTERN_TEMPLATES,
        "vegan": WESTERN_TEMPLATES,
        "eggetarian": WESTERN_TEMPLATES,
    },
    "mediterranean": {
        "vegetarian": MEDITERRANEAN_TEMPLATES,
        "non_vegetarian": MEDITERRANEAN_TEMPLATES,
        "vegan": MEDITERRANEAN_TEMPLATES,
        "eggetarian": MEDITERRANEAN_TEMPLATES,
    },
    "mixed": {
        "vegetarian": INDIAN_VEGETARIAN_TEMPLATES,
        "non_vegetarian": INDIAN_NON_VEG_TEMPLATES,
        "vegan": INDIAN_VEGETARIAN_TEMPLATES,
        "eggetarian": INDIAN_NON_VEG_TEMPLATES,
    },
}


CONDITION_NOTES = {
    "diabetic": [
        "Avoid high-GI foods like white rice, white bread, and sugary items",
        "Include bitter gourd (karela), fenugreek (methi), and cinnamon",
        "Eat small, frequent meals to maintain stable blood sugar",
        "Prefer complex carbs: brown rice, whole wheat, millets",
        "Include fiber-rich foods with every meal",
    ],
    "high_cholesterol": [
        "Limit saturated fats - avoid ghee, butter, full-fat dairy",
        "Include omega-3 rich foods: flax seeds, walnuts, fatty fish",
        "Increase soluble fiber intake: oats, beans, fruits",
        "Use olive oil or mustard oil for cooking",
        "Avoid processed and fried foods",
    ],
    "anemia": [
        "Include iron-rich foods: spinach, beetroot, pomegranate, dates, jaggery",
        "Pair iron foods with vitamin C sources for better absorption",
        "Avoid tea/coffee with meals (inhibits iron absorption)",
        "Include B12 sources: eggs, dairy, fortified foods",
        "Consider cooking in iron vessels",
    ],
    "thyroid": [
        "Include selenium-rich foods: Brazil nuts, sunflower seeds",
        "Ensure adequate iodine: iodized salt, seafood",
        "Limit goitrogens when raw: broccoli, cabbage, soy (cooking reduces effect)",
        "Include zinc-rich foods: pumpkin seeds, chickpeas",
        "Maintain consistent meal timing",
    ],
    "hypertension": [
        "Limit sodium intake to under 2300mg/day (ideally 1500mg)",
        "Increase potassium: bananas, sweet potatoes, spinach",
        "Follow DASH diet principles",
        "Limit caffeine and alcohol",
        "Include garlic, beetroot, and leafy greens",
    ],
    "kidney_disease": [
        "Monitor protein intake as advised by nephrologist",
        "Limit potassium, phosphorus, and sodium",
        "Avoid processed foods and canned items",
        "Monitor fluid intake as recommended",
        "Choose fresh fruits and vegetables in moderation",
    ],
    "pcod": [
        "Focus on low-GI, anti-inflammatory foods",
        "Include omega-3 fatty acids and fiber",
        "Limit dairy and refined carbs",
        "Include chromium-rich foods: broccoli, green beans",
        "Maintain consistent meal timing to regulate hormones",
    ],
}

CONDITION_SUPPLEMENTS = {
    "diabetic": ["Chromium Picolinate", "Alpha-Lipoic Acid", "Berberine (consult doctor)"],
    "high_cholesterol": ["Omega-3 Fish Oil", "Plant Sterols", "Psyllium Husk"],
    "anemia": ["Iron Bisglycinate", "Vitamin C", "Vitamin B12", "Folic Acid"],
    "thyroid": ["Selenium", "Zinc", "Vitamin D3"],
    "hypertension": ["Magnesium", "CoQ10", "Potassium (if approved by doctor)"],
    "pcod": ["Inositol", "Vitamin D3", "Omega-3", "Zinc"],
}

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _pick_meal(templates: dict, meal_type: str, seed_offset: int = 0) -> list[dict]:
    """Pick a meal from templates for the given meal type."""
    if meal_type not in templates:
        return []
    options = templates[meal_type]
    if not options:
        return []
    idx = (seed_offset) % len(options)
    return options[idx]


def _scale_meal_items(items: list[dict], scale_factor: float) -> list[dict]:
    """Scale meal item quantities by a factor to match target calories."""
    scaled = []
    for item in items:
        scaled.append({
            "name": item["name"],
            "quantity": item["qty"],
            "calories": round(item["cal"] * scale_factor, 1),
            "protein_g": round(item["p"] * scale_factor, 1),
            "carbs_g": round(item["c"] * scale_factor, 1),
            "fat_g": round(item["f"] * scale_factor, 1),
        })
    return scaled


def _format_meal(items: list[dict], meal_type: str, time: str) -> dict:
    """Format a meal with totals."""
    total_cal = sum(i["calories"] for i in items)
    total_p = sum(i["protein_g"] for i in items)
    total_c = sum(i["carbs_g"] for i in items)
    total_f = sum(i["fat_g"] for i in items)
    return {
        "meal_type": meal_type,
        "time": time,
        "items": items,
        "total_calories": round(total_cal, 1),
        "total_protein_g": round(total_p, 1),
        "total_carbs_g": round(total_c, 1),
        "total_fat_g": round(total_f, 1),
    }


MEAL_TIMES = {
    "early_morning": "6:30 AM",
    "breakfast": "8:00 AM",
    "mid_morning": "10:30 AM",
    "lunch": "1:00 PM",
    "evening_snack": "4:30 PM",
    "dinner": "7:30 PM",
    "bedtime": "9:30 PM",
}

MEAL_CALORIE_DISTRIBUTION = {
    "early_morning": 0.03,
    "breakfast": 0.25,
    "mid_morning": 0.08,
    "lunch": 0.30,
    "evening_snack": 0.09,
    "dinner": 0.22,
    "bedtime": 0.03,
}


def generate_template_diet_plan(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    dietary_preference: str,
    cuisine_preference: str,
    conditions: list[str],
    target_calories: Optional[int] = None,
    num_days: int = 7,
) -> dict:
    """
    Generate a complete diet plan using templates.
    Falls back to this when LLM is unavailable.
    """
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    macros = calculate_macros(tdee, goal, weight_kg)
    hydration = calculate_hydration(weight_kg, activity_level)

    if target_calories:
        cal_target = target_calories
    else:
        cal_target = macros["calories"]

    # Select cuisine templates
    cuisine = cuisine_preference if cuisine_preference in CUISINE_TEMPLATES else "indian"
    pref = dietary_preference if dietary_preference in CUISINE_TEMPLATES[cuisine] else "non_vegetarian"
    templates = CUISINE_TEMPLATES[cuisine][pref]

    daily_plans = []
    for day_idx in range(min(num_days, 7)):
        day_meals = []
        day_total_cal = 0
        day_total_p = 0
        day_total_c = 0
        day_total_f = 0

        for meal_type, time in MEAL_TIMES.items():
            raw_items = _pick_meal(templates, meal_type, seed_offset=day_idx)
            if not raw_items:
                continue

            # Calculate scale factor based on calorie distribution
            target_meal_cal = cal_target * MEAL_CALORIE_DISTRIBUTION.get(meal_type, 0.1)
            raw_cal = sum(i["cal"] for i in raw_items)
            scale = target_meal_cal / raw_cal if raw_cal > 0 else 1.0
            scale = max(0.5, min(scale, 2.0))  # clamp scaling

            items = _scale_meal_items(raw_items, scale)
            meal = _format_meal(items, meal_type, time)
            day_meals.append(meal)

            day_total_cal += meal["total_calories"]
            day_total_p += meal["total_protein_g"]
            day_total_c += meal["total_carbs_g"]
            day_total_f += meal["total_fat_g"]

        daily_plans.append({
            "day": DAY_NAMES[day_idx],
            "meals": day_meals,
            "total_calories": round(day_total_cal, 0),
            "total_protein_g": round(day_total_p, 1),
            "total_carbs_g": round(day_total_c, 1),
            "total_fat_g": round(day_total_f, 1),
            "water_ml": hydration,
        })

    # Collect notes and supplements
    notes = [
        f"Target daily calories: {cal_target} kcal",
        f"Protein target: {macros['protein_g']}g | Carbs target: {macros['carbs_g']}g | Fat target: {macros['fat_g']}g",
        "Drink water throughout the day, especially before meals",
        "Adjust portions based on hunger and energy levels",
    ]
    supplements = ["Multivitamin (daily)", "Vitamin D3 (if levels low)"]

    for condition in conditions:
        cond_lower = condition.lower().replace(" ", "_")
        if cond_lower in CONDITION_NOTES:
            notes.extend(CONDITION_NOTES[cond_lower])
        if cond_lower in CONDITION_SUPPLEMENTS:
            supplements.extend(CONDITION_SUPPLEMENTS[cond_lower])

    return {
        "plan_name": f"{goal.replace('_', ' ').title()} - {cuisine_preference.title()} {dietary_preference.replace('_', ' ').title()}",
        "goal": goal,
        "target_calories": cal_target,
        "target_macros": macros,
        "dietary_preference": dietary_preference,
        "cuisine_preference": cuisine_preference,
        "daily_plans": daily_plans,
        "notes": notes,
        "supplements": list(set(supplements)),
    }


async def generate_llm_diet_plan(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    dietary_preference: str,
    cuisine_preference: str,
    conditions: list[str],
    allergies: list[str],
    target_calories: Optional[int] = None,
) -> Optional[dict]:
    """
    Call LLM service for a personalized diet plan.
    Returns None if LLM is unavailable (offline-first approach).
    """
    settings = get_settings()

    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    macros = calculate_macros(tdee, goal, weight_kg)

    cal_target = target_calories or macros["calories"]

    prompt = f"""Generate a detailed 7-day diet plan with the following specifications:
- Age: {age}, Gender: {gender}, Weight: {weight_kg}kg, Height: {height_cm}cm
- Activity Level: {activity_level}
- Goal: {goal}
- Daily Calories: {cal_target} kcal
- Macros: Protein {macros['protein_g']}g, Carbs {macros['carbs_g']}g, Fat {macros['fat_g']}g
- Dietary Preference: {dietary_preference}
- Cuisine: {cuisine_preference}
- Medical Conditions: {', '.join(conditions) if conditions else 'None'}
- Allergies: {', '.join(allergies) if allergies else 'None'}

Return a JSON object with the following structure for each day:
- day: day name
- meals: array of meals, each with meal_type, time, items (name, quantity, calories, protein_g, carbs_g, fat_g)
Include 5-7 meals per day: early_morning, breakfast, mid_morning, lunch, evening_snack, dinner, bedtime(optional).
"""

    try:
        async with httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{settings.LLM_SERVICE_URL}/generate",
                json={
                    "prompt": prompt,
                    "system_prompt": "You are a certified nutritionist. Generate practical, culturally appropriate diet plans. Return valid JSON only.",
                    "temperature": 0.4,
                    "max_tokens": 4096,
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("text")
    except Exception as e:
        logger.warning(f"LLM service unavailable, falling back to template: {e}")

    return None


def generate_single_meal_plan(
    target_calories: int,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    dietary_preference: str,
    cuisine_preference: str,
    meal_count: int,
    allergies: list[str],
    conditions: list[str],
) -> dict:
    """Generate a single day's meal plan matching target macros."""
    cuisine = cuisine_preference if cuisine_preference in CUISINE_TEMPLATES else "indian"
    pref = dietary_preference if dietary_preference in CUISINE_TEMPLATES[cuisine] else "non_vegetarian"
    templates = CUISINE_TEMPLATES[cuisine][pref]

    meal_types_by_count = {
        3: ["breakfast", "lunch", "dinner"],
        4: ["breakfast", "mid_morning", "lunch", "dinner"],
        5: ["breakfast", "mid_morning", "lunch", "evening_snack", "dinner"],
        6: ["early_morning", "breakfast", "mid_morning", "lunch", "evening_snack", "dinner"],
        7: list(MEAL_TIMES.keys()),
    }
    meal_types = meal_types_by_count.get(meal_count, meal_types_by_count[5])

    # Distribute calories across meals
    total_dist = sum(MEAL_CALORIE_DISTRIBUTION.get(mt, 0.1) for mt in meal_types)

    meals = []
    total_cal = 0
    total_p = 0
    total_c = 0
    total_f = 0

    for i, meal_type in enumerate(meal_types):
        raw_items = _pick_meal(templates, meal_type, seed_offset=random.randint(0, 10))
        if not raw_items:
            continue

        dist = MEAL_CALORIE_DISTRIBUTION.get(meal_type, 0.1) / total_dist
        target_meal_cal = target_calories * dist
        raw_cal = sum(item["cal"] for item in raw_items)
        scale = target_meal_cal / raw_cal if raw_cal > 0 else 1.0
        scale = max(0.5, min(scale, 2.0))

        items = _scale_meal_items(raw_items, scale)
        meal = _format_meal(items, meal_type, MEAL_TIMES.get(meal_type, ""))
        meals.append(meal)

        total_cal += meal["total_calories"]
        total_p += meal["total_protein_g"]
        total_c += meal["total_carbs_g"]
        total_f += meal["total_fat_g"]

    notes = [
        f"Target: {target_calories} kcal | Actual: {round(total_cal)} kcal",
        "Adjust portions slightly to match exact macro targets",
    ]

    for condition in conditions:
        cond_lower = condition.lower().replace(" ", "_")
        if cond_lower in CONDITION_NOTES:
            notes.extend(CONDITION_NOTES[cond_lower][:2])

    return {
        "meals": meals,
        "total_calories": round(total_cal, 1),
        "total_protein_g": round(total_p, 1),
        "total_carbs_g": round(total_c, 1),
        "total_fat_g": round(total_f, 1),
        "notes": notes,
    }
