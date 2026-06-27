#!/bin/bash
set -e

# ===========================================
# NutriMed AI - MongoDB Seed Script
# ===========================================
# Seeds the database with initial data for development.
# Usage: ./seed-db.sh [MONGO_HOST] [MONGO_PORT]

MONGO_HOST="${1:-localhost}"
MONGO_PORT="${2:-27017}"
MONGO_USER="admin"
MONGO_PASS="nutrimed_secret"
DB_NAME="nutrimed"

MONGO_URI="mongodb://${MONGO_USER}:${MONGO_PASS}@${MONGO_HOST}:${MONGO_PORT}/${DB_NAME}?authSource=admin"

echo "============================================"
echo "  NutriMed AI - Database Seeding"
echo "============================================"
echo "Host: ${MONGO_HOST}:${MONGO_PORT}"
echo "Database: ${DB_NAME}"
echo ""

mongosh "${MONGO_URI}" --quiet <<'MONGOSCRIPT'

// Drop existing collections for a clean seed
db.users.drop();
db.food_items.drop();
db.exercises.drop();
db.health_conditions.drop();

// --- Users (demo accounts) ---
db.users.insertMany([
  {
    email: "demo@nutrimed.ai",
    full_name: "Demo User",
    hashed_password: "$2b$12$LJ3m4ys3Lk0TSwHlvPBVAOIYlyMBGdJpqVQyEFhNJr5u8Kf2kX0eK",
    role: "patient",
    is_active: true,
    profile: {
      age: 30,
      gender: "male",
      height_cm: 175,
      weight_kg: 78,
      activity_level: "moderate",
      dietary_preferences: ["balanced"],
      allergies: [],
      health_goals: ["weight_management", "general_health"]
    },
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    email: "doctor@nutrimed.ai",
    full_name: "Dr. Sarah Chen",
    hashed_password: "$2b$12$LJ3m4ys3Lk0TSwHlvPBVAOIYlyMBGdJpqVQyEFhNJr5u8Kf2kX0eK",
    role: "doctor",
    is_active: true,
    profile: {
      specialization: "Clinical Nutrition",
      license_number: "NUT-2024-001"
    },
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    email: "admin@nutrimed.ai",
    full_name: "System Admin",
    hashed_password: "$2b$12$LJ3m4ys3Lk0TSwHlvPBVAOIYlyMBGdJpqVQyEFhNJr5u8Kf2kX0eK",
    role: "admin",
    is_active: true,
    profile: {},
    created_at: new Date(),
    updated_at: new Date()
  }
]);
print("Inserted 3 users (password for all: 'Demo@123')");

// --- Common Food Items ---
db.food_items.insertMany([
  {
    name: "Brown Rice (cooked)",
    category: "grains",
    serving_size: "1 cup (195g)",
    nutrients: {
      calories: 216,
      protein_g: 5.0,
      carbs_g: 44.8,
      fat_g: 1.8,
      fiber_g: 3.5,
      sugar_g: 0.7,
      sodium_mg: 10,
      potassium_mg: 154,
      iron_mg: 1.0,
      calcium_mg: 20,
      vitamin_b6_mg: 0.3
    },
    glycemic_index: 68,
    tags: ["whole_grain", "gluten_free", "high_fiber"]
  },
  {
    name: "Chicken Breast (grilled)",
    category: "protein",
    serving_size: "100g",
    nutrients: {
      calories: 165,
      protein_g: 31.0,
      carbs_g: 0,
      fat_g: 3.6,
      fiber_g: 0,
      sugar_g: 0,
      sodium_mg: 74,
      potassium_mg: 256,
      iron_mg: 1.0,
      calcium_mg: 15,
      vitamin_b6_mg: 0.6
    },
    glycemic_index: 0,
    tags: ["high_protein", "low_fat", "lean_meat"]
  },
  {
    name: "Banana",
    category: "fruit",
    serving_size: "1 medium (118g)",
    nutrients: {
      calories: 105,
      protein_g: 1.3,
      carbs_g: 27.0,
      fat_g: 0.4,
      fiber_g: 3.1,
      sugar_g: 14.4,
      sodium_mg: 1,
      potassium_mg: 422,
      iron_mg: 0.3,
      calcium_mg: 6,
      vitamin_b6_mg: 0.4
    },
    glycemic_index: 51,
    tags: ["fruit", "high_potassium", "quick_energy"]
  },
  {
    name: "Spinach (raw)",
    category: "vegetable",
    serving_size: "1 cup (30g)",
    nutrients: {
      calories: 7,
      protein_g: 0.9,
      carbs_g: 1.1,
      fat_g: 0.1,
      fiber_g: 0.7,
      sugar_g: 0.1,
      sodium_mg: 24,
      potassium_mg: 167,
      iron_mg: 0.8,
      calcium_mg: 30,
      vitamin_b6_mg: 0.1
    },
    glycemic_index: 15,
    tags: ["leafy_green", "low_calorie", "iron_rich"]
  },
  {
    name: "Greek Yogurt (plain, non-fat)",
    category: "dairy",
    serving_size: "1 cup (245g)",
    nutrients: {
      calories: 100,
      protein_g: 17.0,
      carbs_g: 6.0,
      fat_g: 0.7,
      fiber_g: 0,
      sugar_g: 6.0,
      sodium_mg: 61,
      potassium_mg: 240,
      iron_mg: 0.1,
      calcium_mg: 187,
      vitamin_b6_mg: 0.1
    },
    glycemic_index: 11,
    tags: ["high_protein", "probiotic", "calcium_rich"]
  }
]);
print("Inserted 5 food items");

// --- Exercises ---
db.exercises.insertMany([
  {
    name: "Walking (brisk)",
    category: "cardio",
    met_value: 4.3,
    calories_per_min_per_kg: 0.072,
    description: "Brisk walking at 5.5 km/h on a flat surface",
    difficulty: "beginner",
    muscle_groups: ["quadriceps", "hamstrings", "calves", "glutes"],
    suitable_for: ["weight_loss", "heart_health", "general_fitness"]
  },
  {
    name: "Running (moderate)",
    category: "cardio",
    met_value: 8.0,
    calories_per_min_per_kg: 0.133,
    description: "Running at 8 km/h on a flat surface",
    difficulty: "intermediate",
    muscle_groups: ["quadriceps", "hamstrings", "calves", "glutes", "core"],
    suitable_for: ["weight_loss", "endurance", "heart_health"]
  },
  {
    name: "Push-ups",
    category: "strength",
    met_value: 3.8,
    calories_per_min_per_kg: 0.063,
    description: "Standard push-ups with proper form",
    difficulty: "beginner",
    muscle_groups: ["chest", "triceps", "shoulders", "core"],
    suitable_for: ["muscle_building", "upper_body_strength"]
  },
  {
    name: "Yoga (Hatha)",
    category: "flexibility",
    met_value: 2.5,
    calories_per_min_per_kg: 0.042,
    description: "Gentle yoga focusing on basic poses and breathing",
    difficulty: "beginner",
    muscle_groups: ["full_body"],
    suitable_for: ["flexibility", "stress_relief", "balance"]
  },
  {
    name: "Cycling (moderate)",
    category: "cardio",
    met_value: 6.8,
    calories_per_min_per_kg: 0.113,
    description: "Cycling at 16-19 km/h on a flat surface",
    difficulty: "intermediate",
    muscle_groups: ["quadriceps", "hamstrings", "calves", "glutes"],
    suitable_for: ["weight_loss", "endurance", "heart_health", "low_impact"]
  }
]);
print("Inserted 5 exercises");

// --- Health Conditions ---
db.health_conditions.insertMany([
  {
    name: "Type 2 Diabetes",
    code: "E11",
    dietary_guidelines: {
      avoid: ["refined_sugar", "white_bread", "sugary_drinks", "processed_foods"],
      prefer: ["whole_grains", "lean_protein", "leafy_greens", "nuts", "legumes"],
      max_daily_sugar_g: 25,
      max_glycemic_index: 55,
      meal_frequency: "5-6 small meals per day"
    },
    exercise_guidelines: {
      recommended: ["walking", "swimming", "cycling", "resistance_training"],
      min_weekly_minutes: 150,
      intensity: "moderate",
      precautions: ["Monitor blood sugar before and after exercise", "Carry fast-acting glucose"]
    }
  },
  {
    name: "Hypertension",
    code: "I10",
    dietary_guidelines: {
      avoid: ["high_sodium_foods", "processed_meats", "canned_soups", "pickles"],
      prefer: ["fruits", "vegetables", "whole_grains", "lean_protein", "low_fat_dairy"],
      max_daily_sodium_mg: 1500,
      meal_frequency: "Regular meals with controlled portions"
    },
    exercise_guidelines: {
      recommended: ["walking", "swimming", "cycling", "yoga"],
      avoid: ["heavy_weightlifting", "isometric_exercises"],
      min_weekly_minutes: 150,
      intensity: "moderate",
      precautions: ["Avoid holding breath during exercise", "Warm up gradually"]
    }
  },
  {
    name: "Celiac Disease",
    code: "K90.0",
    dietary_guidelines: {
      avoid: ["wheat", "barley", "rye", "malt", "brewer_yeast"],
      prefer: ["rice", "quinoa", "corn", "potatoes", "gluten_free_oats"],
      strict_avoidance: true,
      meal_frequency: "Regular balanced meals"
    },
    exercise_guidelines: {
      recommended: ["any_exercise_as_tolerated"],
      min_weekly_minutes: 150,
      intensity: "moderate",
      precautions: ["Ensure adequate nutrition before intense exercise"]
    }
  }
]);
print("Inserted 3 health conditions");

// --- Create indexes ---
db.users.createIndex({ email: 1 }, { unique: true });
db.users.createIndex({ role: 1 });
db.food_items.createIndex({ name: "text", category: "text", tags: "text" });
db.food_items.createIndex({ category: 1 });
db.exercises.createIndex({ name: "text", category: "text" });
db.exercises.createIndex({ category: 1, difficulty: 1 });
db.health_conditions.createIndex({ name: 1 }, { unique: true });
db.health_conditions.createIndex({ code: 1 }, { unique: true });
print("Created indexes");

print("");
print("============================================");
print("  Database seeding complete!");
print("  Users: " + db.users.countDocuments());
print("  Food Items: " + db.food_items.countDocuments());
print("  Exercises: " + db.exercises.countDocuments());
print("  Health Conditions: " + db.health_conditions.countDocuments());
print("============================================");

MONGOSCRIPT

echo ""
echo "Seeding completed successfully."
