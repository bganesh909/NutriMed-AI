# NutriMed AI -- API Documentation

**Base URL:** `http://localhost:8000/api/v1`

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI)

## Authentication

All endpoints except `/auth/register`, `/auth/login`, and `/health` require a JWT Bearer token.

Include the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens expire after 30 minutes. Use the refresh endpoint to obtain a new access token.

---

## Auth

### POST /auth/register

Register a new user account.

**Request Body:**

```json
{
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "password": "Test@1234"
}
```

**Response (201):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Status Codes:**

| Code | Description              |
|------|--------------------------|
| 201  | User created             |
| 409  | Email already registered |
| 422  | Validation error         |

---

### POST /auth/login

Authenticate and receive tokens.

**Request Body:**

```json
{
  "email": "rahul@example.com",
  "password": "Test@1234"
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Status Codes:**

| Code | Description         |
|------|---------------------|
| 200  | Success             |
| 401  | Invalid credentials |
| 422  | Validation error    |

---

### POST /auth/refresh

Refresh an expired access token.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Status Codes:**

| Code | Description                    |
|------|--------------------------------|
| 200  | Success                        |
| 401  | Invalid or expired refresh token |

---

## Users

### GET /users/me

Get the authenticated user's profile.

**Response (200):**

```json
{
  "id": "664a1b2c3d4e5f6a7b8c9d0e",
  "name": "Rahul Sharma",
  "email": "rahul@example.com",
  "age": 28,
  "gender": "male",
  "weight": 75.0,
  "height": 175.0,
  "activity_level": "moderately_active",
  "goals": ["muscle_gain"],
  "role": "user",
  "created_at": "2026-06-01T10:00:00Z",
  "updated_at": "2026-06-15T14:30:00Z"
}
```

---

### PUT /users/me

Update the authenticated user's profile.

**Request Body (all fields optional):**

```json
{
  "name": "Rahul S.",
  "age": 29,
  "weight": 74.5,
  "height": 175.0,
  "gender": "male",
  "activity_level": "very_active",
  "goals": ["muscle_gain", "health_improvement"]
}
```

**Response (200):** Updated user profile (same schema as GET /users/me).

**Status Codes:**

| Code | Description        |
|------|--------------------|
| 200  | Updated            |
| 400  | No fields provided |
| 401  | Unauthorized       |

---

### POST /users/me/medical-profile

Create or update the user's medical profile.

**Request Body:**

```json
{
  "blood_type": "B+",
  "allergies": ["peanuts"],
  "chronic_conditions": ["type_2_diabetes"],
  "medications": ["metformin_500mg"],
  "surgeries": [],
  "family_history": ["hypertension"],
  "dietary_restrictions": ["vegetarian"],
  "notes": "Active lifestyle, family history of diabetes"
}
```

**Response (200):**

```json
{
  "id": "664b...",
  "user_id": "664a...",
  "blood_type": "B+",
  "allergies": ["peanuts"],
  "chronic_conditions": ["type_2_diabetes"],
  "medications": ["metformin_500mg"],
  "surgeries": [],
  "family_history": ["hypertension"],
  "dietary_restrictions": ["vegetarian"],
  "notes": "Active lifestyle, family history of diabetes",
  "updated_at": "2026-06-15T14:30:00Z"
}
```

---

### GET /users/me/medical-profile

Retrieve the user's medical profile.

**Response (200):** Same schema as POST response above.

**Status Codes:**

| Code | Description         |
|------|---------------------|
| 200  | Success             |
| 404  | Profile not found   |

---

## Reports

### POST /reports/upload

Upload a lab report file (PDF/image).

**Request:** `multipart/form-data`

| Field       | Type   | Required | Description                                          |
|-------------|--------|----------|------------------------------------------------------|
| file        | File   | Yes      | PDF or image file                                    |
| report_type | String | Yes      | One of: CBC, LIPID, LFT, KFT, THYROID, VITAMIN, DIABETES |

**Response (201):**

```json
{
  "id": "664c...",
  "user_id": "664a...",
  "report_type": "CBC",
  "original_filename": "blood_test.pdf",
  "status": "uploaded",
  "uploaded_at": "2026-06-15T10:00:00Z",
  "processed_at": null
}
```

---

### GET /reports/

List all reports for the authenticated user.

**Response (200):** Array of report objects (sorted by upload date, newest first).

---

### GET /reports/{report_id}

Get a specific report.

**Response (200):** Single report object.

**Status Codes:**

| Code | Description     |
|------|-----------------|
| 200  | Success         |
| 404  | Not found       |

---

### POST /reports/{report_id}/analyze

Trigger OCR + AI analysis pipeline for a report.

**Response (200):**

```json
{
  "report_id": "664c...",
  "status": "processing",
  "message": "Analysis task dispatched"
}
```

**Status Codes:**

| Code | Description                        |
|------|------------------------------------|
| 200  | Analysis started                   |
| 404  | Report not found                   |
| 409  | Already being processed            |
| 503  | Celery worker not available        |

---

### GET /reports/{report_id}/analysis

Get the analysis results for a processed report.

**Response (200):**

```json
{
  "report_id": "664c...",
  "status": "completed",
  "biomarkers": {
    "hemoglobin": 14.5,
    "vitamin_d": 22.0,
    "ldl": 120.0
  },
  "deficiencies": ["Vitamin D insufficiency"],
  "risk_factors": ["Borderline high LDL"],
  "dietary_suggestions": ["Increase vitamin D rich foods"],
  "supplement_suggestions": ["Vitamin D3 2000 IU daily"],
  "warnings": []
}
```

---

## Nutrition

### POST /nutrition/calculate

Calculate BMR, TDEE, BMI, and macro targets.

**Request Body (all fields optional, defaults from user profile):**

```json
{
  "weight_kg": 75,
  "height_cm": 175,
  "age": 30,
  "gender": "male",
  "activity_level": "moderate",
  "goal": "maintenance",
  "waist_cm": 84,
  "hip_cm": 96,
  "neck_cm": 38
}
```

**Response (200):**

```json
{
  "bmr": 1698.8,
  "tdee": 2633.1,
  "bmi": 24.5,
  "bmi_category": "normal",
  "body_fat_estimate": 18.5,
  "target_calories": 2633.1,
  "macros": {
    "protein_g": 197.5,
    "carbs_g": 263.3,
    "fat_g": 87.8
  }
}
```

---

### GET /nutrition/calculate

Calculate nutrition using the stored user profile (no request body needed).

**Response (200):** Same schema as POST.

---

### POST /nutrition/generate-diet

Generate an AI-powered 7-day meal plan.

**Request Body:**

```json
{
  "goal": "weight_loss",
  "dietary_restrictions": ["vegetarian"],
  "allergies": ["peanuts"]
}
```

**Response (201):**

```json
{
  "id": "664d...",
  "user_id": "664a...",
  "goal": "weight_loss",
  "calories": 2133.1,
  "macros": {
    "protein_g": 213.3,
    "carbs_g": 160.0,
    "fat_g": 71.1
  },
  "meal_plan": [
    {
      "day": "Monday",
      "meals": [
        {
          "name": "Breakfast",
          "time": "8:00 AM",
          "foods": [
            {
              "name": "Oatmeal with banana",
              "quantity": "1 cup",
              "calories": 250,
              "protein_g": 8,
              "carbs_g": 45,
              "fat_g": 5
            }
          ]
        }
      ]
    }
  ],
  "nutrition_calc": { "..." : "..." }
}
```

**Status Codes:**

| Code | Description            |
|------|------------------------|
| 201  | Plan generated         |
| 503  | Ollama not available   |

---

## Fitness

### POST /fitness/generate-workout

Generate an AI-powered workout plan.

**Request Body:**

```json
{
  "goal": "muscle_gain",
  "difficulty": "intermediate",
  "days_per_week": 4,
  "conditions": ["lower_back_pain"],
  "use_biomarkers": true
}
```

**Response (201):**

```json
{
  "id": "664e...",
  "user_id": "664a...",
  "goal": "muscle_gain",
  "difficulty": "intermediate",
  "days_per_week": 4,
  "weekly_split": [
    {
      "day": 1,
      "focus": "Upper Body Push",
      "exercises": [
        {
          "name": "Bench Press",
          "sets": 4,
          "reps": "8-10",
          "rest_seconds": 90
        }
      ]
    }
  ]
}
```

---

### GET /fitness/workout-plans

List all workout plans for the user.

---

### GET /fitness/workout-plans/{plan_id}

Get a specific workout plan.

---

## Recommendations

### POST /recommendations/generate

Generate combined health recommendations based on latest biomarkers.

**Request Body:**

```json
{
  "report_id": "664c..."
}
```

**Response (201):** Full recommendation document with dietary, supplement, exercise, and lifestyle suggestions.

---

### GET /recommendations/

List all recommendations for the user.

---

### GET /recommendations/latest

Get the most recent recommendation.

---

## Progress

### POST /progress/

Log a progress entry.

**Request Body:**

```json
{
  "date": "2026-06-15",
  "weight": 74.5,
  "body_fat_pct": 18.0,
  "measurements": {
    "waist": 82.0,
    "chest": 100.0,
    "arms": 36.0,
    "thighs": 56.0
  },
  "biomarker_snapshot": {
    "hemoglobin": 14.8,
    "vitamin_d": 28.0
  },
  "notes": "Feeling good, energy levels up"
}
```

**Response (201):**

```json
{
  "id": "664f...",
  "user_id": "664a...",
  "date": "2026-06-15",
  "weight": 74.5,
  "body_fat_pct": 18.0,
  "measurements": {"waist": 82.0, "chest": 100.0, "arms": 36.0, "thighs": 56.0},
  "biomarker_snapshot": {"hemoglobin": 14.8, "vitamin_d": 28.0},
  "notes": "Feeling good, energy levels up",
  "created_at": "2026-06-15T08:00:00Z"
}
```

---

### GET /progress/

Get progress history with trends.

**Query Parameters:**

| Param | Type | Default | Description       |
|-------|------|---------|-------------------|
| limit | int  | 50      | Max entries (1-200) |
| skip  | int  | 0       | Offset            |

**Response (200):**

```json
{
  "entries": [ "..." ],
  "total": 25,
  "trends": {
    "weight_change": -2.5
  }
}
```

---

### GET /progress/{entry_id}

Get a specific progress entry.

---

## PDF

### GET /pdf/reports/{report_id}/pdf

Download a generated PDF report with full analysis, diet plan, workout plan, and supplement recommendations.

**Response:** `application/pdf` file stream.

---

### GET /pdf/report/{report_id}

Download the original uploaded report file (decrypted).

**Response:** `application/pdf` file stream.

---

## Health Check

### GET /health

**Response (200):**

```json
{
  "status": "ok",
  "app": "NutriMed AI"
}
```
