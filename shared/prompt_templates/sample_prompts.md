# NutriMed AI -- Sample Prompts and Expected Outputs

This document shows the actual prompts sent to the LLM for each task, along with representative expected outputs. These serve as reference for testing, evaluation, and prompt tuning.

---

## 1. Lab Report Analysis

### Prompt

```
You are a medical lab report analyst. Analyze the following biomarker data and provide interpretation.

Patient Profile:
- Age: 28, Gender: male
- Weight: 75 kg, Height: 175 cm
- Activity Level: moderately_active
- Known Conditions: none

Biomarker Data:
{
  "hemoglobin": 15.2,
  "vitamin_d": 18.5,
  "vitamin_b12": 185,
  "ldl": 118,
  "hdl": 52,
  "triglycerides": 130,
  "fasting_sugar": 88,
  "hba1c": 5.1,
  "tsh": 2.4,
  "iron": 110,
  "calcium": 9.6,
  "creatinine": 1.0,
  "ferritin": 85
}

Reference Ranges:
- Hemoglobin: 13.0-17.0 g/dL
- Vitamin D: 30-100 ng/mL
- Vitamin B12: 200-900 pg/mL
- LDL: <100 mg/dL (optimal), <130 mg/dL (near optimal)
- HDL: >40 mg/dL (male)
- Triglycerides: <150 mg/dL
- Fasting Sugar: 70-100 mg/dL
- HbA1c: 4.0-5.7%
- TSH: 0.4-4.0 mIU/L
- Iron: 65-175 mcg/dL
- Calcium: 8.5-10.5 mg/dL
- Creatinine: 0.7-1.3 mg/dL
- Ferritin: 20-500 ng/mL

Provide your analysis in the following JSON format:
{
    "summary": "Brief overall health summary",
    "findings": [...],
    "risk_factors": [...],
    "priority_actions": [...],
    "follow_up": "..."
}
```

### Expected Output

```json
{
  "summary": "Overall health is good with normal CBC, kidney, liver, thyroid, and blood sugar markers. Two areas of concern: Vitamin D deficiency (18.5 ng/mL) and Vitamin B12 deficiency (185 pg/mL). LDL cholesterol is near-optimal but above ideal levels.",
  "findings": [
    {
      "biomarker": "vitamin_d",
      "value": 18.5,
      "status": "low",
      "interpretation": "Vitamin D level is significantly below the normal range (30-100 ng/mL), indicating deficiency. This can affect bone health, immune function, and mood.",
      "recommendation": "Supplement with Vitamin D3 (cholecalciferol) 2000-4000 IU daily. Increase sun exposure (15-20 minutes daily). Include fatty fish, egg yolks, and fortified foods."
    },
    {
      "biomarker": "vitamin_b12",
      "value": 185,
      "status": "low",
      "interpretation": "Vitamin B12 is below the normal range (200-900 pg/mL). This can cause fatigue, weakness, and neurological symptoms.",
      "recommendation": "Supplement with methylcobalamin 1000 mcg daily. Include B12-rich foods: eggs, dairy, fortified cereals. Retest in 3 months."
    },
    {
      "biomarker": "ldl",
      "value": 118,
      "status": "borderline",
      "interpretation": "LDL is in the near-optimal range (100-129 mg/dL) but above the ideal target of <100 mg/dL.",
      "recommendation": "Increase soluble fiber intake (oats, beans, fruits). Reduce saturated fat. Regular exercise helps raise HDL and lower LDL."
    },
    {
      "biomarker": "hemoglobin",
      "value": 15.2,
      "status": "normal",
      "interpretation": "Hemoglobin is within normal range for adult males (13.0-17.0 g/dL).",
      "recommendation": "No action needed. Continue balanced diet."
    }
  ],
  "risk_factors": [
    "Vitamin D deficiency increases risk of osteoporosis, weakened immunity, and mood disorders",
    "B12 deficiency can lead to megaloblastic anemia and peripheral neuropathy if untreated",
    "Borderline LDL with family history of diabetes warrants monitoring"
  ],
  "priority_actions": [
    "Start Vitamin D3 supplementation immediately (2000-4000 IU/day)",
    "Start Vitamin B12 supplementation (1000 mcg methylcobalamin daily)",
    "Dietary modifications to reduce LDL: increase fiber, reduce saturated fats",
    "Retest Vitamin D and B12 levels in 3 months"
  ],
  "follow_up": "Retest Vitamin D, Vitamin B12, and lipid panel in 3 months to assess response to supplementation and dietary changes."
}
```

---

## 2. Diet Plan Generation

### Prompt

```
Create a detailed 7-day meal plan for a 32-year-old female weighing 62kg, 160cm tall, activity level: light.
Goal: fat_loss. Daily calories: 1550 kcal.
Macros: protein 155g, carbs 116.3g, fat 51.7g.
Dietary restrictions: vegetarian.
Allergies: peanuts.

For each day provide breakfast, mid-morning snack, lunch, evening snack, and dinner with specific food items, quantities, and approximate calories. Return the result as valid JSON.
```

### Expected Output

```json
[
  {
    "day": "Monday",
    "meals": [
      {
        "name": "Breakfast",
        "time": "8:00 AM",
        "foods": [
          {"name": "Moong dal chilla (2 pieces)", "quantity": "150g", "calories": 180, "protein_g": 12, "carbs_g": 20, "fat_g": 5},
          {"name": "Greek yogurt (low fat)", "quantity": "100g", "calories": 60, "protein_g": 10, "carbs_g": 4, "fat_g": 0},
          {"name": "Green tea", "quantity": "1 cup", "calories": 2, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
        ]
      },
      {
        "name": "Mid-Morning Snack",
        "time": "10:30 AM",
        "foods": [
          {"name": "Paneer cubes (grilled)", "quantity": "50g", "calories": 130, "protein_g": 9, "carbs_g": 1, "fat_g": 10},
          {"name": "Cucumber slices", "quantity": "100g", "calories": 15, "protein_g": 1, "carbs_g": 3, "fat_g": 0}
        ]
      },
      {
        "name": "Lunch",
        "time": "1:00 PM",
        "foods": [
          {"name": "Brown rice", "quantity": "100g cooked", "calories": 110, "protein_g": 3, "carbs_g": 23, "fat_g": 1},
          {"name": "Rajma curry", "quantity": "150g", "calories": 180, "protein_g": 12, "carbs_g": 25, "fat_g": 4},
          {"name": "Mixed vegetable raita", "quantity": "100g", "calories": 50, "protein_g": 3, "carbs_g": 5, "fat_g": 2},
          {"name": "Green salad", "quantity": "100g", "calories": 20, "protein_g": 1, "carbs_g": 4, "fat_g": 0}
        ]
      },
      {
        "name": "Evening Snack",
        "time": "4:30 PM",
        "foods": [
          {"name": "Roasted chana (chickpeas)", "quantity": "30g", "calories": 110, "protein_g": 7, "carbs_g": 18, "fat_g": 2},
          {"name": "Apple", "quantity": "1 medium", "calories": 95, "protein_g": 0, "carbs_g": 25, "fat_g": 0}
        ]
      },
      {
        "name": "Dinner",
        "time": "7:30 PM",
        "foods": [
          {"name": "Tofu stir-fry", "quantity": "150g", "calories": 180, "protein_g": 15, "carbs_g": 8, "fat_g": 10},
          {"name": "Multigrain roti", "quantity": "1 piece", "calories": 90, "protein_g": 3, "carbs_g": 15, "fat_g": 2},
          {"name": "Palak (spinach) soup", "quantity": "200ml", "calories": 60, "protein_g": 4, "carbs_g": 6, "fat_g": 2}
        ]
      }
    ]
  }
]
```

---

## 3. Workout Plan Generation

### Prompt

```
You are a certified personal trainer. Generate a structured weekly workout plan.

Client Profile:
- Age: 28, Gender: male
- Weight: 75 kg, Height: 175 cm
- Current Activity Level: moderately_active
- Fitness Level: intermediate
- Primary Goal: muscle_gain
- Medical Conditions: none
- Injuries/Limitations: none
- Available Equipment: full gym
- Training Days Per Week: 4
- Session Duration: 60 minutes

Biomarker Considerations:
- All biomarkers normal
- Vitamin D slightly low (24 ng/mL) -- outdoor training can help

Generate a weekly workout plan in JSON format.
```

### Expected Output

```json
{
  "plan_name": "Hypertrophy Focus - 4-Day Upper/Lower Split",
  "goal": "muscle_gain",
  "duration_weeks": 8,
  "days_per_week": 4,
  "weekly_split": [
    {
      "day": 1,
      "day_name": "Monday",
      "focus": "Upper Body - Push Emphasis",
      "exercises": [
        {"name": "Barbell Bench Press", "muscle_group": "Chest", "sets": 4, "reps": "8-10", "rest_seconds": 90, "tempo": "2-0-2-0", "notes": "Keep shoulder blades retracted, slight arch in lower back"},
        {"name": "Overhead Press", "muscle_group": "Shoulders", "sets": 3, "reps": "8-10", "rest_seconds": 90, "tempo": "2-0-2-0", "notes": "Brace core throughout the movement"},
        {"name": "Incline Dumbbell Press", "muscle_group": "Upper Chest", "sets": 3, "reps": "10-12", "rest_seconds": 75, "tempo": "2-1-2-0", "notes": "30-degree incline"},
        {"name": "Lateral Raises", "muscle_group": "Side Delts", "sets": 3, "reps": "12-15", "rest_seconds": 60, "tempo": "2-1-2-0", "notes": "Control the negative, slight lean forward"},
        {"name": "Tricep Dips", "muscle_group": "Triceps", "sets": 3, "reps": "10-12", "rest_seconds": 60, "tempo": "2-0-2-0", "notes": "Upright torso to target triceps"},
        {"name": "Cable Tricep Pushdown", "muscle_group": "Triceps", "sets": 3, "reps": "12-15", "rest_seconds": 45, "tempo": "2-1-2-0", "notes": "Squeeze at bottom"}
      ],
      "warmup": [
        {"name": "Arm circles and band pull-aparts", "duration": "3 minutes"},
        {"name": "Light bench press (50% working weight)", "duration": "2 sets of 10"}
      ],
      "cooldown": [
        {"name": "Chest doorway stretch", "duration": "30 seconds each side"},
        {"name": "Overhead tricep stretch", "duration": "30 seconds each arm"}
      ],
      "estimated_duration_minutes": 60,
      "estimated_calories_burned": 350
    },
    {
      "day": 2,
      "day_name": "Tuesday",
      "focus": "Lower Body - Quad/Glute Emphasis",
      "exercises": [
        {"name": "Barbell Back Squat", "muscle_group": "Quads/Glutes", "sets": 4, "reps": "6-8", "rest_seconds": 120, "tempo": "3-1-1-0", "notes": "Break parallel, drive through heels"},
        {"name": "Romanian Deadlift", "muscle_group": "Hamstrings/Glutes", "sets": 3, "reps": "8-10", "rest_seconds": 90, "tempo": "3-1-1-0", "notes": "Hinge at hips, slight knee bend"},
        {"name": "Leg Press", "muscle_group": "Quads", "sets": 3, "reps": "10-12", "rest_seconds": 90, "tempo": "2-0-2-0", "notes": "Medium foot placement"},
        {"name": "Walking Lunges", "muscle_group": "Quads/Glutes", "sets": 3, "reps": "12 each leg", "rest_seconds": 60, "tempo": "2-0-2-0", "notes": "Long stride for glute emphasis"},
        {"name": "Calf Raises (Standing)", "muscle_group": "Calves", "sets": 4, "reps": "15-20", "rest_seconds": 45, "tempo": "2-2-2-0", "notes": "Full stretch at bottom, pause at top"}
      ],
      "warmup": [
        {"name": "Bodyweight squats", "duration": "2 sets of 15"},
        {"name": "Hip circles and leg swings", "duration": "3 minutes"}
      ],
      "cooldown": [
        {"name": "Quad stretch (standing)", "duration": "30 seconds each leg"},
        {"name": "Hamstring stretch (seated)", "duration": "30 seconds each leg"},
        {"name": "Hip flexor stretch", "duration": "30 seconds each side"}
      ],
      "estimated_duration_minutes": 60,
      "estimated_calories_burned": 400
    }
  ],
  "progression": {
    "week_1_4": "Focus on form and progressive overload. Increase weight by 2.5-5 lbs when all sets hit the upper rep range. Keep RPE at 7-8.",
    "week_5_8": "Intensification phase. Add 1 set to compound lifts. Introduce drop sets on isolation exercises. Target RPE 8-9."
  },
  "recovery": {
    "sleep": "Target 7-9 hours per night. Sleep quality directly impacts muscle recovery and growth hormone release.",
    "rest_days": "Light walking (20-30 minutes outdoors to help with Vitamin D), foam rolling, and mobility work.",
    "deload": "Week 4: reduce all weights by 40%, maintain volume. This allows joints and CNS to recover."
  },
  "precautions": [
    "Ensure adequate warm-up before heavy compound lifts",
    "Stay hydrated -- target 3+ liters daily given activity level",
    "Consider outdoor training when possible to improve Vitamin D levels"
  ],
  "notes": [
    "Protein intake should be 1.8-2.2g per kg bodyweight (135-165g daily)",
    "Post-workout nutrition: 30-40g protein within 1 hour of training",
    "Progressive overload is the primary driver of hypertrophy -- track all weights and reps"
  ]
}
```

---

## 4. Supplement Recommendation

### Prompt

```
You are a clinical nutritionist specializing in evidence-based supplementation.

Patient Profile:
- Age: 32, Gender: female
- Weight: 62 kg
- Medical Conditions: subclinical hypothyroidism
- Current Medications: none
- Current Supplements: none
- Health Goal: fat_loss
- Dietary Preference: vegetarian

Biomarker Data:
{
  "hemoglobin": 10.8,
  "vitamin_d": 14.0,
  "vitamin_b12": 165,
  "iron": 38,
  "ferritin": 12,
  "folate": 2.5,
  "tsh": 3.2,
  "calcium": 8.8
}

Provide supplement recommendations in JSON format.
```

### Expected Output

```json
{
  "overall_assessment": "The patient presents with multiple nutritional deficiencies commonly seen in vegetarian women: iron deficiency anemia (low hemoglobin, iron, ferritin), severe Vitamin D deficiency, Vitamin B12 deficiency (expected in vegetarians), low folate, and borderline low calcium. These deficiencies are likely contributing to fatigue and may be impairing thyroid function. Addressing these deficiencies is critical before focusing on fat loss.",
  "recommendations": [
    {
      "supplement": "Iron (Ferrous Bisglycinate)",
      "form": "Ferrous bisglycinate chelate (gentle on stomach)",
      "dosage": "25-30 mg elemental iron daily",
      "timing": "Take on empty stomach with Vitamin C (morning, 30 min before breakfast)",
      "duration": "3-6 months, then retest ferritin and hemoglobin",
      "reason": "Hemoglobin 10.8 g/dL, iron 38 mcg/dL, and ferritin 12 ng/mL all indicate iron deficiency anemia. Ferrous bisglycinate has superior absorption and fewer GI side effects.",
      "evidence_level": "strong",
      "interactions": ["Do not take with calcium, zinc, or tea/coffee (space by 2 hours)", "May reduce absorption of thyroid medications if started later"],
      "contraindications": ["Hemochromatosis", "Iron overload disorders"],
      "food_alternatives": ["Spinach, lentils, chickpeas, fortified cereals, pumpkin seeds, dried apricots. Pair with Vitamin C sources for better absorption."]
    },
    {
      "supplement": "Vitamin D3 (Cholecalciferol)",
      "form": "Cholecalciferol (D3) -- oil-based softgel or liquid drops",
      "dosage": "4000 IU (100 mcg) daily for 8 weeks, then 2000 IU maintenance",
      "timing": "With largest meal containing fat (lunch or dinner)",
      "duration": "8 weeks loading, then ongoing maintenance. Retest at 3 months.",
      "reason": "Vitamin D at 14 ng/mL indicates severe deficiency (<20 ng/mL). This affects calcium absorption, bone health, immunity, mood, and thyroid function.",
      "evidence_level": "strong",
      "interactions": ["Enhances calcium absorption (beneficial)", "Space from iron supplement by 2 hours"],
      "contraindications": ["Hypercalcemia", "Granulomatous diseases"],
      "food_alternatives": ["Fortified milk/plant milk, mushrooms exposed to sunlight, egg yolks. 15-20 minutes of midday sun exposure."]
    },
    {
      "supplement": "Vitamin B12 (Methylcobalamin)",
      "form": "Methylcobalamin sublingual tablets",
      "dosage": "1000 mcg daily",
      "timing": "Morning, sublingual (under tongue for better absorption)",
      "duration": "Ongoing for vegetarians. Retest at 3 months.",
      "reason": "B12 at 165 pg/mL is below normal (200-900 pg/mL). Vegetarians are at high risk of B12 deficiency as it is primarily found in animal products. Low B12 can cause fatigue, neurological symptoms, and macrocytic anemia.",
      "evidence_level": "strong",
      "interactions": ["No significant interactions"],
      "contraindications": ["Leber's hereditary optic neuropathy (rare)"],
      "food_alternatives": ["Fortified nutritional yeast, fortified plant milks, fortified cereals. Natural vegetarian sources are insufficient."]
    },
    {
      "supplement": "Folic Acid (5-MTHF preferred)",
      "form": "L-methylfolate (5-MTHF) -- active form",
      "dosage": "400-800 mcg daily",
      "timing": "Morning with breakfast",
      "duration": "3 months, then reassess with diet",
      "reason": "Folate at 2.5 ng/mL is below normal (3.0-17.0 ng/mL). Low folate combined with low B12 can cause megaloblastic anemia. L-methylfolate is preferred as it bypasses MTHFR polymorphism issues.",
      "evidence_level": "strong",
      "interactions": ["Works synergistically with B12", "High-dose folic acid can mask B12 deficiency -- always supplement B12 alongside"],
      "contraindications": [],
      "food_alternatives": ["Dark leafy greens (spinach, methi), lentils, chickpeas, asparagus, broccoli, fortified cereals"]
    },
    {
      "supplement": "Calcium Citrate",
      "form": "Calcium citrate (better absorbed than carbonate, especially with low stomach acid)",
      "dosage": "500 mg daily (split into 2 doses of 250 mg)",
      "timing": "With meals, separate from iron by at least 2 hours",
      "duration": "Ongoing, especially with Vitamin D supplementation",
      "reason": "Calcium at 8.8 mg/dL is borderline low (normal 8.5-10.5). Combined with severe Vitamin D deficiency, calcium absorption is further impaired. Important for bone health, especially for women.",
      "evidence_level": "moderate",
      "interactions": ["Reduces iron absorption (space by 2+ hours)", "Take with Vitamin D for enhanced absorption"],
      "contraindications": ["Hypercalcemia", "Kidney stones (use with caution)"],
      "food_alternatives": ["Dairy products, fortified plant milks, tofu (calcium-set), sesame seeds (til), ragi, green leafy vegetables"]
    }
  ],
  "avoid": [
    {
      "supplement": "Biotin (high dose)",
      "reason": "High-dose biotin (>5000 mcg) can interfere with thyroid lab tests (TSH), leading to falsely normal or abnormal readings. Given subclinical hypothyroidism, avoid until thyroid status is stable."
    },
    {
      "supplement": "Kelp / Iodine supplements",
      "reason": "Excessive iodine can worsen thyroid dysfunction in subclinical hypothyroidism. Get iodine from iodized salt only."
    }
  ],
  "stack_notes": "Morning routine: B12 sublingual (empty stomach) -> Iron + Vitamin C (30 min before breakfast) -> Folic acid with breakfast. Lunch/Dinner: Vitamin D3 with largest meal -> Calcium citrate with a different meal (2+ hours from iron). Never take iron and calcium together.",
  "review_timeline": "Retest CBC (hemoglobin, ferritin), Vitamin D, Vitamin B12, folate, calcium, and TSH in 3 months. If hemoglobin has not improved, consider IV iron infusion referral.",
  "disclaimer": "These recommendations are for informational purposes and are based on the provided biomarker data. They do not constitute medical advice. Please consult with a healthcare provider before starting any supplementation, especially with existing thyroid conditions."
}
```
