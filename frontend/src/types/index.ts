export interface User {
  id: string;
  email: string;
  name: string;
  age: number;
  gender: "male" | "female" | "other";
  height: number;
  weight: number;
  goal: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface MedicalProfile {
  id: string;
  user_id: string;
  blood_type: string;
  allergies: string[];
  chronic_conditions: string[];
  medications: string[];
  dietary_preferences: string;
  activity_level: "sedentary" | "light" | "moderate" | "active" | "very_active";
  notes: string;
}

export interface Report {
  id: string;
  user_id: string;
  file_name: string;
  file_url: string;
  report_type: string;
  status: "uploaded" | "processing" | "analyzed" | "error";
  uploaded_at: string;
  analyzed_at?: string;
  summary?: string;
}

export interface Biomarker {
  id: string;
  report_id: string;
  name: string;
  value: number;
  unit: string;
  reference_min: number;
  reference_max: number;
  status: "Normal" | "Low" | "High" | "Critical";
  category: string;
}

export interface Recommendation {
  id: string;
  user_id: string;
  type: "diet" | "exercise" | "supplement" | "lifestyle";
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
  created_at: string;
}

export interface FoodItem {
  name: string;
  quantity: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  fiber: number;
}

export interface Meal {
  name: string;
  time: string;
  foods: FoodItem[];
  total_calories: number;
  total_protein: number;
  total_carbs: number;
  total_fat: number;
}

export interface DietPlan {
  id: string;
  user_id: string;
  preference: string;
  goal: string;
  daily_calories: number;
  daily_protein: number;
  daily_carbs: number;
  daily_fat: number;
  days: {
    day: string;
    meals: Meal[];
  }[];
  created_at: string;
}

export interface Exercise {
  name: string;
  sets: number;
  reps: string;
  rest: string;
  notes?: string;
}

export interface WorkoutDay {
  day: string;
  focus: string;
  exercises: Exercise[];
  duration: string;
}

export interface WorkoutPlan {
  id: string;
  user_id: string;
  goal: string;
  difficulty: string;
  days: WorkoutDay[];
  notes: string;
  created_at: string;
}

export interface ProgressLog {
  id: string;
  user_id: string;
  date: string;
  weight?: number;
  body_fat?: number;
  waist?: number;
  chest?: number;
  arms?: number;
  notes?: string;
  created_at: string;
}

export interface NutritionCalc {
  bmr: number;
  tdee: number;
  recommended_calories: number;
  recommended_protein: number;
  recommended_carbs: number;
  recommended_fat: number;
  recommended_fiber: number;
}
