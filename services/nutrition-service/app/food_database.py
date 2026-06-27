"""
Local food database with nutritional information per 100g serving.
Covers proteins, carbs, fats, vegetables, fruits, dairy, grains, and Indian foods.
"""

from typing import Optional


# Each entry: {name, calories, protein_g, carbs_g, fat_g, fiber_g, category, tags}
FOOD_DATABASE: list[dict] = [
    # === PROTEINS - Poultry & Meat ===
    {"name": "Chicken Breast (cooked)", "calories": 165, "protein_g": 31.0, "carbs_g": 0.0, "fat_g": 3.6, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "high_protein"]},
    {"name": "Chicken Thigh (cooked)", "calories": 209, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 10.9, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian"]},
    {"name": "Turkey Breast (cooked)", "calories": 135, "protein_g": 30.0, "carbs_g": 0.0, "fat_g": 1.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "high_protein", "lean"]},
    {"name": "Lamb (lean, cooked)", "calories": 258, "protein_g": 25.5, "carbs_g": 0.0, "fat_g": 16.5, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian"]},
    {"name": "Goat Meat (cooked)", "calories": 143, "protein_g": 27.1, "carbs_g": 0.0, "fat_g": 3.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "lean"]},
    {"name": "Lean Beef (cooked)", "calories": 250, "protein_g": 26.0, "carbs_g": 0.0, "fat_g": 15.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian"]},

    # === PROTEINS - Seafood ===
    {"name": "Salmon (cooked)", "calories": 208, "protein_g": 20.0, "carbs_g": 0.0, "fat_g": 13.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "omega3", "fish"]},
    {"name": "Tuna (cooked)", "calories": 132, "protein_g": 29.0, "carbs_g": 0.0, "fat_g": 1.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "lean", "fish"]},
    {"name": "Shrimp (cooked)", "calories": 99, "protein_g": 24.0, "carbs_g": 0.2, "fat_g": 0.3, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "lean", "shellfish"]},
    {"name": "Mackerel (cooked)", "calories": 262, "protein_g": 24.0, "carbs_g": 0.0, "fat_g": 18.0, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "omega3", "fish"]},
    {"name": "Sardines (canned)", "calories": 208, "protein_g": 25.0, "carbs_g": 0.0, "fat_g": 11.5, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "omega3", "fish"]},
    {"name": "Rohu Fish (cooked)", "calories": 97, "protein_g": 17.0, "carbs_g": 0.0, "fat_g": 3.2, "fiber_g": 0, "category": "protein", "tags": ["non_vegetarian", "fish", "indian"]},

    # === PROTEINS - Eggs ===
    {"name": "Whole Egg (boiled)", "calories": 155, "protein_g": 13.0, "carbs_g": 1.1, "fat_g": 11.0, "fiber_g": 0, "category": "protein", "tags": ["eggetarian", "non_vegetarian"]},
    {"name": "Egg Whites", "calories": 52, "protein_g": 11.0, "carbs_g": 0.7, "fat_g": 0.2, "fiber_g": 0, "category": "protein", "tags": ["eggetarian", "non_vegetarian", "lean"]},

    # === PROTEINS - Plant-Based ===
    {"name": "Tofu (firm)", "calories": 144, "protein_g": 17.3, "carbs_g": 2.8, "fat_g": 8.7, "fiber_g": 0.3, "category": "protein", "tags": ["vegetarian", "vegan"]},
    {"name": "Tempeh", "calories": 192, "protein_g": 20.3, "carbs_g": 7.6, "fat_g": 11.4, "fiber_g": 1.4, "category": "protein", "tags": ["vegetarian", "vegan"]},
    {"name": "Paneer", "calories": 265, "protein_g": 18.3, "carbs_g": 1.2, "fat_g": 20.8, "fiber_g": 0, "category": "protein", "tags": ["vegetarian", "indian"]},
    {"name": "Soy Chunks (dry)", "calories": 345, "protein_g": 52.0, "carbs_g": 33.0, "fat_g": 0.5, "fiber_g": 13.0, "category": "protein", "tags": ["vegetarian", "vegan", "indian", "high_protein"]},

    # === LEGUMES & PULSES ===
    {"name": "Chickpeas (cooked)", "calories": 164, "protein_g": 8.9, "carbs_g": 27.4, "fat_g": 2.6, "fiber_g": 7.6, "category": "legume", "tags": ["vegetarian", "vegan", "high_fiber"]},
    {"name": "Lentils / Masoor Dal (cooked)", "calories": 116, "protein_g": 9.0, "carbs_g": 20.1, "fat_g": 0.4, "fiber_g": 7.9, "category": "legume", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Moong Dal (cooked)", "calories": 105, "protein_g": 7.0, "carbs_g": 19.0, "fat_g": 0.4, "fiber_g": 7.6, "category": "legume", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Toor Dal (cooked)", "calories": 118, "protein_g": 7.7, "carbs_g": 21.0, "fat_g": 0.4, "fiber_g": 5.0, "category": "legume", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Kidney Beans / Rajma (cooked)", "calories": 127, "protein_g": 8.7, "carbs_g": 22.8, "fat_g": 0.5, "fiber_g": 6.4, "category": "legume", "tags": ["vegetarian", "vegan", "indian", "high_fiber"]},
    {"name": "Black Beans (cooked)", "calories": 132, "protein_g": 8.9, "carbs_g": 23.7, "fat_g": 0.5, "fiber_g": 8.7, "category": "legume", "tags": ["vegetarian", "vegan", "high_fiber"]},
    {"name": "Chana Dal (cooked)", "calories": 124, "protein_g": 8.2, "carbs_g": 22.0, "fat_g": 0.6, "fiber_g": 5.8, "category": "legume", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Urad Dal (cooked)", "calories": 105, "protein_g": 7.5, "carbs_g": 18.3, "fat_g": 0.4, "fiber_g": 4.2, "category": "legume", "tags": ["vegetarian", "vegan", "indian"]},

    # === GRAINS & CEREALS ===
    {"name": "White Rice (cooked)", "calories": 130, "protein_g": 2.7, "carbs_g": 28.2, "fat_g": 0.3, "fiber_g": 0.4, "category": "grain", "tags": ["vegetarian", "vegan", "gluten_free"]},
    {"name": "Brown Rice (cooked)", "calories": 123, "protein_g": 2.7, "carbs_g": 25.6, "fat_g": 1.0, "fiber_g": 1.8, "category": "grain", "tags": ["vegetarian", "vegan", "gluten_free", "whole_grain"]},
    {"name": "Quinoa (cooked)", "calories": 120, "protein_g": 4.4, "carbs_g": 21.3, "fat_g": 1.9, "fiber_g": 2.8, "category": "grain", "tags": ["vegetarian", "vegan", "gluten_free", "whole_grain"]},
    {"name": "Oats (dry)", "calories": 389, "protein_g": 16.9, "carbs_g": 66.3, "fat_g": 6.9, "fiber_g": 10.6, "category": "grain", "tags": ["vegetarian", "vegan", "whole_grain"]},
    {"name": "Wheat Flour (whole)", "calories": 340, "protein_g": 13.2, "carbs_g": 72.6, "fat_g": 1.9, "fiber_g": 10.7, "category": "grain", "tags": ["vegetarian", "vegan", "whole_grain"]},
    {"name": "Roti / Chapati", "calories": 240, "protein_g": 8.0, "carbs_g": 50.0, "fat_g": 1.0, "fiber_g": 4.0, "category": "grain", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Multigrain Bread", "calories": 265, "protein_g": 13.4, "carbs_g": 43.3, "fat_g": 4.2, "fiber_g": 7.4, "category": "grain", "tags": ["vegetarian", "whole_grain"]},
    {"name": "White Bread", "calories": 265, "protein_g": 9.0, "carbs_g": 49.0, "fat_g": 3.2, "fiber_g": 2.7, "category": "grain", "tags": ["vegetarian"]},
    {"name": "Pasta (cooked)", "calories": 131, "protein_g": 5.0, "carbs_g": 25.0, "fat_g": 1.1, "fiber_g": 1.8, "category": "grain", "tags": ["vegetarian"]},
    {"name": "Whole Wheat Pasta (cooked)", "calories": 124, "protein_g": 5.3, "carbs_g": 26.5, "fat_g": 0.5, "fiber_g": 3.9, "category": "grain", "tags": ["vegetarian", "whole_grain"]},
    {"name": "Poha (flattened rice, dry)", "calories": 350, "protein_g": 6.6, "carbs_g": 77.3, "fat_g": 1.2, "fiber_g": 1.0, "category": "grain", "tags": ["vegetarian", "vegan", "indian", "gluten_free"]},
    {"name": "Ragi / Finger Millet (dry)", "calories": 328, "protein_g": 7.3, "carbs_g": 72.0, "fat_g": 1.3, "fiber_g": 11.5, "category": "grain", "tags": ["vegetarian", "vegan", "indian", "gluten_free", "whole_grain"]},
    {"name": "Bajra / Pearl Millet (dry)", "calories": 361, "protein_g": 11.6, "carbs_g": 67.0, "fat_g": 5.0, "fiber_g": 11.3, "category": "grain", "tags": ["vegetarian", "vegan", "indian", "gluten_free", "whole_grain"]},
    {"name": "Jowar / Sorghum (dry)", "calories": 339, "protein_g": 10.4, "carbs_g": 72.6, "fat_g": 1.9, "fiber_g": 9.7, "category": "grain", "tags": ["vegetarian", "vegan", "indian", "gluten_free", "whole_grain"]},
    {"name": "Sweet Potato (cooked)", "calories": 90, "protein_g": 2.0, "carbs_g": 20.7, "fat_g": 0.1, "fiber_g": 3.3, "category": "grain", "tags": ["vegetarian", "vegan", "gluten_free"]},
    {"name": "Potato (cooked)", "calories": 87, "protein_g": 1.9, "carbs_g": 20.1, "fat_g": 0.1, "fiber_g": 1.8, "category": "grain", "tags": ["vegetarian", "vegan", "gluten_free"]},

    # === DAIRY ===
    {"name": "Whole Milk", "calories": 61, "protein_g": 3.2, "carbs_g": 4.8, "fat_g": 3.3, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian"]},
    {"name": "Skim Milk", "calories": 34, "protein_g": 3.4, "carbs_g": 5.0, "fat_g": 0.1, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "low_fat"]},
    {"name": "Greek Yogurt (plain)", "calories": 97, "protein_g": 9.0, "carbs_g": 3.6, "fat_g": 5.0, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "probiotic"]},
    {"name": "Curd / Dahi (plain)", "calories": 60, "protein_g": 3.1, "carbs_g": 4.7, "fat_g": 3.1, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "indian", "probiotic"]},
    {"name": "Buttermilk / Chaas", "calories": 40, "protein_g": 3.3, "carbs_g": 4.8, "fat_g": 0.9, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "indian", "probiotic", "low_fat"]},
    {"name": "Cottage Cheese (low fat)", "calories": 72, "protein_g": 12.4, "carbs_g": 2.7, "fat_g": 1.0, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "high_protein", "low_fat"]},
    {"name": "Cheddar Cheese", "calories": 403, "protein_g": 25.0, "carbs_g": 1.3, "fat_g": 33.0, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian"]},
    {"name": "Mozzarella Cheese", "calories": 280, "protein_g": 28.0, "carbs_g": 3.1, "fat_g": 17.1, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian"]},
    {"name": "Whey Protein Powder", "calories": 400, "protein_g": 80.0, "carbs_g": 10.0, "fat_g": 5.0, "fiber_g": 0, "category": "dairy", "tags": ["vegetarian", "supplement", "high_protein"]},

    # === VEGETABLES ===
    {"name": "Spinach (raw)", "calories": 23, "protein_g": 2.9, "carbs_g": 3.6, "fat_g": 0.4, "fiber_g": 2.2, "category": "vegetable", "tags": ["vegetarian", "vegan", "iron_rich"]},
    {"name": "Broccoli (cooked)", "calories": 35, "protein_g": 2.4, "carbs_g": 7.2, "fat_g": 0.4, "fiber_g": 3.3, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Cauliflower (cooked)", "calories": 23, "protein_g": 1.8, "carbs_g": 4.1, "fat_g": 0.5, "fiber_g": 2.3, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Bell Pepper (raw)", "calories": 31, "protein_g": 1.0, "carbs_g": 6.0, "fat_g": 0.3, "fiber_g": 2.1, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Cucumber", "calories": 15, "protein_g": 0.7, "carbs_g": 3.6, "fat_g": 0.1, "fiber_g": 0.5, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Tomato", "calories": 18, "protein_g": 0.9, "carbs_g": 3.9, "fat_g": 0.2, "fiber_g": 1.2, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Carrot", "calories": 41, "protein_g": 0.9, "carbs_g": 9.6, "fat_g": 0.2, "fiber_g": 2.8, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Onion", "calories": 40, "protein_g": 1.1, "carbs_g": 9.3, "fat_g": 0.1, "fiber_g": 1.7, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Cabbage", "calories": 25, "protein_g": 1.3, "carbs_g": 5.8, "fat_g": 0.1, "fiber_g": 2.5, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Beetroot", "calories": 43, "protein_g": 1.6, "carbs_g": 9.6, "fat_g": 0.2, "fiber_g": 2.8, "category": "vegetable", "tags": ["vegetarian", "vegan", "iron_rich"]},
    {"name": "Bottle Gourd / Lauki", "calories": 14, "protein_g": 0.6, "carbs_g": 3.4, "fat_g": 0.0, "fiber_g": 0.5, "category": "vegetable", "tags": ["vegetarian", "vegan", "indian", "low_calorie"]},
    {"name": "Bitter Gourd / Karela", "calories": 17, "protein_g": 1.0, "carbs_g": 3.7, "fat_g": 0.2, "fiber_g": 2.8, "category": "vegetable", "tags": ["vegetarian", "vegan", "indian", "diabetic_friendly"]},
    {"name": "Okra / Bhindi", "calories": 33, "protein_g": 1.9, "carbs_g": 7.5, "fat_g": 0.2, "fiber_g": 3.2, "category": "vegetable", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Drumstick / Moringa", "calories": 37, "protein_g": 2.1, "carbs_g": 8.3, "fat_g": 0.2, "fiber_g": 2.0, "category": "vegetable", "tags": ["vegetarian", "vegan", "indian", "iron_rich"]},
    {"name": "Mushroom", "calories": 22, "protein_g": 3.1, "carbs_g": 3.3, "fat_g": 0.3, "fiber_g": 1.0, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Zucchini", "calories": 17, "protein_g": 1.2, "carbs_g": 3.1, "fat_g": 0.3, "fiber_g": 1.0, "category": "vegetable", "tags": ["vegetarian", "vegan", "low_calorie"]},
    {"name": "Asparagus", "calories": 20, "protein_g": 2.2, "carbs_g": 3.9, "fat_g": 0.1, "fiber_g": 2.1, "category": "vegetable", "tags": ["vegetarian", "vegan"]},
    {"name": "Green Beans", "calories": 31, "protein_g": 1.8, "carbs_g": 7.0, "fat_g": 0.1, "fiber_g": 3.4, "category": "vegetable", "tags": ["vegetarian", "vegan"]},

    # === FRUITS ===
    {"name": "Banana", "calories": 89, "protein_g": 1.1, "carbs_g": 22.8, "fat_g": 0.3, "fiber_g": 2.6, "category": "fruit", "tags": ["vegetarian", "vegan"]},
    {"name": "Apple", "calories": 52, "protein_g": 0.3, "carbs_g": 13.8, "fat_g": 0.2, "fiber_g": 2.4, "category": "fruit", "tags": ["vegetarian", "vegan"]},
    {"name": "Orange", "calories": 47, "protein_g": 0.9, "carbs_g": 11.8, "fat_g": 0.1, "fiber_g": 2.4, "category": "fruit", "tags": ["vegetarian", "vegan", "vitamin_c"]},
    {"name": "Mango", "calories": 60, "protein_g": 0.8, "carbs_g": 15.0, "fat_g": 0.4, "fiber_g": 1.6, "category": "fruit", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Papaya", "calories": 43, "protein_g": 0.5, "carbs_g": 10.8, "fat_g": 0.3, "fiber_g": 1.7, "category": "fruit", "tags": ["vegetarian", "vegan"]},
    {"name": "Guava", "calories": 68, "protein_g": 2.6, "carbs_g": 14.3, "fat_g": 1.0, "fiber_g": 5.4, "category": "fruit", "tags": ["vegetarian", "vegan", "indian", "vitamin_c"]},
    {"name": "Watermelon", "calories": 30, "protein_g": 0.6, "carbs_g": 7.6, "fat_g": 0.2, "fiber_g": 0.4, "category": "fruit", "tags": ["vegetarian", "vegan", "low_calorie"]},
    {"name": "Pomegranate", "calories": 83, "protein_g": 1.7, "carbs_g": 18.7, "fat_g": 1.2, "fiber_g": 4.0, "category": "fruit", "tags": ["vegetarian", "vegan", "indian", "iron_rich"]},
    {"name": "Blueberries", "calories": 57, "protein_g": 0.7, "carbs_g": 14.5, "fat_g": 0.3, "fiber_g": 2.4, "category": "fruit", "tags": ["vegetarian", "vegan", "antioxidant"]},
    {"name": "Strawberries", "calories": 32, "protein_g": 0.7, "carbs_g": 7.7, "fat_g": 0.3, "fiber_g": 2.0, "category": "fruit", "tags": ["vegetarian", "vegan", "vitamin_c"]},
    {"name": "Grapes", "calories": 69, "protein_g": 0.7, "carbs_g": 18.1, "fat_g": 0.2, "fiber_g": 0.9, "category": "fruit", "tags": ["vegetarian", "vegan"]},
    {"name": "Pineapple", "calories": 50, "protein_g": 0.5, "carbs_g": 13.1, "fat_g": 0.1, "fiber_g": 1.4, "category": "fruit", "tags": ["vegetarian", "vegan"]},
    {"name": "Avocado", "calories": 160, "protein_g": 2.0, "carbs_g": 8.5, "fat_g": 14.7, "fiber_g": 6.7, "category": "fruit", "tags": ["vegetarian", "vegan", "healthy_fat"]},
    {"name": "Dates (dried)", "calories": 277, "protein_g": 1.8, "carbs_g": 75.0, "fat_g": 0.2, "fiber_g": 6.7, "category": "fruit", "tags": ["vegetarian", "vegan", "iron_rich"]},

    # === NUTS & SEEDS ===
    {"name": "Almonds", "calories": 579, "protein_g": 21.2, "carbs_g": 21.7, "fat_g": 49.9, "fiber_g": 12.5, "category": "nut", "tags": ["vegetarian", "vegan", "healthy_fat"]},
    {"name": "Walnuts", "calories": 654, "protein_g": 15.2, "carbs_g": 13.7, "fat_g": 65.2, "fiber_g": 6.7, "category": "nut", "tags": ["vegetarian", "vegan", "omega3", "healthy_fat"]},
    {"name": "Cashews", "calories": 553, "protein_g": 18.2, "carbs_g": 30.2, "fat_g": 43.9, "fiber_g": 3.3, "category": "nut", "tags": ["vegetarian", "vegan"]},
    {"name": "Peanuts", "calories": 567, "protein_g": 25.8, "carbs_g": 16.1, "fat_g": 49.2, "fiber_g": 8.5, "category": "nut", "tags": ["vegetarian", "vegan", "high_protein"]},
    {"name": "Peanut Butter", "calories": 588, "protein_g": 25.1, "carbs_g": 20.0, "fat_g": 50.4, "fiber_g": 6.0, "category": "nut", "tags": ["vegetarian", "vegan"]},
    {"name": "Chia Seeds", "calories": 486, "protein_g": 16.5, "carbs_g": 42.1, "fat_g": 30.7, "fiber_g": 34.4, "category": "seed", "tags": ["vegetarian", "vegan", "omega3", "high_fiber"]},
    {"name": "Flax Seeds", "calories": 534, "protein_g": 18.3, "carbs_g": 28.9, "fat_g": 42.2, "fiber_g": 27.3, "category": "seed", "tags": ["vegetarian", "vegan", "omega3", "high_fiber"]},
    {"name": "Sunflower Seeds", "calories": 584, "protein_g": 20.8, "carbs_g": 20.0, "fat_g": 51.5, "fiber_g": 8.6, "category": "seed", "tags": ["vegetarian", "vegan"]},
    {"name": "Pumpkin Seeds", "calories": 559, "protein_g": 30.2, "carbs_g": 10.7, "fat_g": 49.1, "fiber_g": 6.0, "category": "seed", "tags": ["vegetarian", "vegan", "high_protein"]},

    # === OILS & FATS ===
    {"name": "Olive Oil", "calories": 884, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "fiber_g": 0, "category": "fat", "tags": ["vegetarian", "vegan", "healthy_fat", "mediterranean"]},
    {"name": "Coconut Oil", "calories": 862, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "fiber_g": 0, "category": "fat", "tags": ["vegetarian", "vegan"]},
    {"name": "Ghee", "calories": 900, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 100.0, "fiber_g": 0, "category": "fat", "tags": ["vegetarian", "indian"]},
    {"name": "Butter", "calories": 717, "protein_g": 0.9, "carbs_g": 0.1, "fat_g": 81.1, "fiber_g": 0, "category": "fat", "tags": ["vegetarian"]},

    # === INDIAN PREPARED FOODS ===
    {"name": "Idli (1 piece ~40g)", "calories": 39, "protein_g": 2.0, "carbs_g": 8.0, "fat_g": 0.1, "fiber_g": 0.5, "category": "prepared", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Dosa (plain)", "calories": 168, "protein_g": 3.9, "carbs_g": 25.0, "fat_g": 5.9, "fiber_g": 0.7, "category": "prepared", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Upma", "calories": 153, "protein_g": 4.6, "carbs_g": 25.7, "fat_g": 3.9, "fiber_g": 1.4, "category": "prepared", "tags": ["vegetarian", "indian"]},
    {"name": "Poha (prepared)", "calories": 160, "protein_g": 3.5, "carbs_g": 30.0, "fat_g": 3.0, "fiber_g": 1.2, "category": "prepared", "tags": ["vegetarian", "indian"]},
    {"name": "Sambar", "calories": 65, "protein_g": 3.2, "carbs_g": 10.0, "fat_g": 1.5, "fiber_g": 2.0, "category": "prepared", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Rasam", "calories": 32, "protein_g": 1.5, "carbs_g": 5.5, "fat_g": 0.8, "fiber_g": 0.8, "category": "prepared", "tags": ["vegetarian", "vegan", "indian", "low_calorie"]},
    {"name": "Dal Tadka", "calories": 120, "protein_g": 6.5, "carbs_g": 16.0, "fat_g": 3.5, "fiber_g": 4.0, "category": "prepared", "tags": ["vegetarian", "indian"]},
    {"name": "Palak Paneer", "calories": 160, "protein_g": 8.0, "carbs_g": 6.0, "fat_g": 12.0, "fiber_g": 2.0, "category": "prepared", "tags": ["vegetarian", "indian"]},
    {"name": "Chole / Chana Masala", "calories": 160, "protein_g": 7.5, "carbs_g": 22.0, "fat_g": 5.0, "fiber_g": 5.0, "category": "prepared", "tags": ["vegetarian", "vegan", "indian"]},
    {"name": "Chicken Curry", "calories": 150, "protein_g": 15.0, "carbs_g": 5.0, "fat_g": 8.0, "fiber_g": 0.5, "category": "prepared", "tags": ["non_vegetarian", "indian"]},
    {"name": "Fish Curry", "calories": 120, "protein_g": 14.0, "carbs_g": 4.0, "fat_g": 5.5, "fiber_g": 0.3, "category": "prepared", "tags": ["non_vegetarian", "indian", "fish"]},

    # === BEVERAGES & MISC ===
    {"name": "Green Tea (unsweetened)", "calories": 1, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0, "category": "beverage", "tags": ["vegetarian", "vegan", "low_calorie"]},
    {"name": "Black Coffee", "calories": 2, "protein_g": 0.3, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0, "category": "beverage", "tags": ["vegetarian", "vegan", "low_calorie"]},
    {"name": "Coconut Water", "calories": 19, "protein_g": 0.7, "carbs_g": 3.7, "fat_g": 0.2, "fiber_g": 1.1, "category": "beverage", "tags": ["vegetarian", "vegan"]},
    {"name": "Honey", "calories": 304, "protein_g": 0.3, "carbs_g": 82.4, "fat_g": 0.0, "fiber_g": 0.2, "category": "sweetener", "tags": ["vegetarian"]},
    {"name": "Jaggery / Gur", "calories": 383, "protein_g": 0.4, "carbs_g": 98.0, "fat_g": 0.1, "fiber_g": 0, "category": "sweetener", "tags": ["vegetarian", "vegan", "indian", "iron_rich"]},
    {"name": "Dark Chocolate (70%+)", "calories": 598, "protein_g": 7.8, "carbs_g": 45.9, "fat_g": 42.6, "fiber_g": 10.9, "category": "snack", "tags": ["vegetarian", "antioxidant"]},
]


def search_foods(
    query: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[list[str]] = None,
    max_calories: Optional[float] = None,
    min_protein: Optional[float] = None,
) -> list[dict]:
    """Search the food database with filters."""
    results = FOOD_DATABASE

    if query:
        q = query.lower()
        results = [f for f in results if q in f["name"].lower()]

    if category:
        results = [f for f in results if f["category"] == category]

    if tags:
        for tag in tags:
            results = [f for f in results if tag in f["tags"]]

    if max_calories is not None:
        results = [f for f in results if f["calories"] <= max_calories]

    if min_protein is not None:
        results = [f for f in results if f["protein_g"] >= min_protein]

    return results


def get_foods_by_preference(dietary_preference: str) -> list[dict]:
    """Get foods matching a dietary preference."""
    if dietary_preference == "vegan":
        return [f for f in FOOD_DATABASE if "vegan" in f["tags"]]
    elif dietary_preference == "vegetarian":
        return [f for f in FOOD_DATABASE if "vegetarian" in f["tags"]]
    elif dietary_preference == "eggetarian":
        return [f for f in FOOD_DATABASE if "vegetarian" in f["tags"] or "eggetarian" in f["tags"]]
    else:  # non_vegetarian - all foods
        return FOOD_DATABASE


def get_foods_by_category(category: str) -> list[dict]:
    """Get all foods in a category."""
    return [f for f in FOOD_DATABASE if f["category"] == category]
