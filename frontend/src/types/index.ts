export type UserRole = "user" | "admin";

/** Response of GET /users/me. */
export interface User {
  id: string;
  email: string;
  name: string;
  age?: number | null;
  gender?: "male" | "female" | "other" | null;
  height?: number | null;
  weight?: number | null;
  /** Values of the backend ActivityLevel enum (see ACTIVITY_LEVELS). */
  activity_level?: string | null;
  /** The API stores a list; the UI collects and shows the first. */
  goals?: string[];
  role?: UserRole;
  avatar_url?: string;
  created_at?: string;
  updated_at?: string;
}

/** Response of GET /users/me/medical-profile. */
export interface MedicalProfile {
  id: string;
  user_id: string;
  blood_type: string | null;
  dietary_preference: string | null;
  allergies: string[];
  chronic_conditions: string[];
  medications: string[];
  surgeries: string[];
  family_history: string[];
  dietary_restrictions: string[];
  notes: string;
  updated_at?: string;
}

/** Pipeline order: uploaded → processing → ocr_completed → extracted → analyzed → completed. */
export type ReportStatus =
  | "uploaded"
  | "processing"
  | "ocr_completed"
  | "extracted"
  | "analyzed"
  | "completed"
  | "failed";

export interface Report {
  id: string;
  user_id: string;
  report_type: string;
  original_filename: string;
  status: ReportStatus;
  uploaded_at?: string;
  processed_at?: string;
}

/** One row of the rule engine's marker_details map. */
export interface MarkerDetail {
  value: number;
  unit: string;
  status: "low" | "high" | "normal" | "unknown";
  range: string | null;
}

export interface SupplementSuggestion {
  name: string;
  dosage?: string;
  timing?: string;
  notes?: string;
}

/** Response of GET /reports/{id}/analysis. */
export interface ReportAnalysis {
  report_id: string;
  status: ReportStatus;
  biomarkers: Record<string, MarkerDetail> | null;
  deficiencies: string[];
  risk_factors: string[];
  dietary_suggestions: string[];
  supplement_suggestions: SupplementSuggestion[];
  warnings: string[];
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
  /** These come from the curated exercise database, never from the model. */
  muscle_group?: string;
  equipment?: string;
  instructions?: string;
  alternatives?: string[];
}

export interface WorkoutDay {
  day: string;
  focus: string;
  exercises: Exercise[];
  duration: string;
  warm_up?: string;
  cool_down?: string;
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

// ---------------------------------------------------------------------------
// Suggestions
// ---------------------------------------------------------------------------

/** Where a piece of advice came from. */
export type SuggestionSource = "labs" | "goal" | "reported";

export interface SuggestionItem {
  label: string;
  /** One or more reasons; several findings can point at the same action. */
  why: string[];
  source: SuggestionSource;
  examples?: string[];
  detail?: string;
}

export interface Suggestions {
  goal: string;
  based_on: "labs" | "profile" | "labs+profile";
  nutrition: {
    emphasise: SuggestionItem[];
    limit: SuggestionItem[];
    daily_target_calories: number;
  };
  training: {
    focus: SuggestionItem[];
    intensity_capped: boolean;
    cardio_emphasised: boolean;
  };
  /** Profile gaps worth asking the user to fill in. */
  missing_info: string[];
  available_on_request: string[];
}

export interface SuggestionRequest {
  goal?: string;
  report_id?: string;
  conditions?: string[];
  allergies?: string[];
  dietary_preference?: string;
  fitness_level?: string;
  age?: number;
  gender?: string;
  weight?: number;
  height?: number;
  activity_level?: string;
}

/** Goals the API understands, with display labels. */
export const GOALS: { value: string; label: string; description: string }[] = [
  { value: "fat_loss", label: "Fat loss / weight loss", description: "Lose body fat while keeping muscle" },
  { value: "muscle_gain", label: "Muscle gain", description: "Build muscle with a small surplus" },
  { value: "weight_gain", label: "Weight gain", description: "Put on weight with a larger surplus" },
  { value: "recomposition", label: "Body recomposition", description: "Lose fat and gain muscle at once" },
  { value: "endurance", label: "Stamina / endurance", description: "Improve aerobic capacity" },
  { value: "strength", label: "Strength", description: "Get stronger on the main lifts" },
  { value: "maintenance", label: "General fitness", description: "Stay healthy and maintain" },
];


/**
 * Diet preferences the API's food catalogue can filter by
 * (backend DietaryPreference in app/schemas/medical_profile.py).
 */
export const DIET_PREFERENCES: { value: string; label: string }[] = [
  { value: "non_vegetarian", label: "No restriction (includes meat & fish)" },
  { value: "eggetarian", label: "Eggetarian (vegetarian + eggs)" },
  { value: "vegetarian", label: "Vegetarian" },
  { value: "vegan", label: "Vegan" },
];

/** Activity levels of the backend ActivityLevel enum (app/models/user.py). */
export const ACTIVITY_LEVELS: { value: string; label: string }[] = [
  { value: "sedentary", label: "Sedentary (little or no exercise)" },
  { value: "lightly_active", label: "Lightly active (1–3 days/week)" },
  { value: "moderately_active", label: "Moderately active (3–5 days/week)" },
  { value: "very_active", label: "Very active (6–7 days/week)" },
  { value: "extra_active", label: "Extra active (physical job + training)" },
];

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface AppNotification {
  id: string;
  type: string;
  title: string;
  message: string;
  read: boolean;
  report_id?: string;
  created_at: string;
}

export interface NotificationList {
  items: AppNotification[];
  unread_count: number;
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export interface AdminStats {
  users: number;
  new_users_7d: number;
  reports: number;
  reports_7d: number;
  reports_by_status: Record<string, number>;
  diet_plans: number;
  workout_plans: number;
  progress_entries: number;
}

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  created_at?: string;
  report_count: number;
}
