# NutriMed AI -- API Documentation

**Base URL:** `http://localhost:8000/api/v1`

**Interactive docs:** `http://localhost:8000/docs` (Swagger UI)

## Authentication

All endpoints except `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/forgot-password`, `/auth/reset-password` and `/health` require a JWT Bearer token.

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

### POST /auth/forgot-password

Email a single-use password-reset link (valid for `PASSWORD_RESET_EXPIRY_MINUTES`, default 30). The response is the same whether or not the email is registered, so the endpoint cannot be used to discover accounts. Without `SMTP_HOST` no email is sent; with `DEBUG=true` it is written to the API log instead.

**Request Body:** `{"email": "user@example.com"}`

**Response (200):** `{"message": "If an account exists for that email, a reset link has been sent."}`

---

### POST /auth/reset-password

Set a new password using the token from the reset link. The token works once, and every session issued before the reset is signed out.

**Request Body:** `{"token": "<from the link>", "password": "NewPassword123"}`

| Code | Description                          |
|------|--------------------------------------|
| 200  | Password updated                     |
| 400  | Token invalid, expired or already used |
| 422  | Password shorter than 8 characters   |

---

### POST /auth/change-password

Change the signed-in user's password. Every other session is signed out; the response carries fresh tokens for this one (same shape as `/auth/login`).

**Request Body:** `{"current_password": "...", "new_password": "..."}`

| Code | Description                               |
|------|-------------------------------------------|
| 200  | Changed; new token pair returned          |
| 400  | New password is the same as the current one |
| 403  | Current password is incorrect             |

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
  "dietary_preference": "vegetarian",
  "allergies": ["peanuts"],
  "chronic_conditions": ["type_2_diabetes"],
  "medications": ["metformin_500mg"],
  "surgeries": [],
  "family_history": ["hypertension"],
  "dietary_restrictions": ["low_sodium"],
  "notes": "Active lifestyle, family history of diabetes"
}
```

**Response (200):**

```json
{
  "id": "664b...",
  "user_id": "664a...",
  "blood_type": "B+",
  "dietary_preference": "vegetarian",
  "allergies": ["peanuts"],
  "chronic_conditions": ["type_2_diabetes"],
  "medications": ["metformin_500mg"],
  "surgeries": [],
  "family_history": ["hypertension"],
  "dietary_restrictions": ["low_sodium"],
  "notes": "Active lifestyle, family history of diabetes",
  "updated_at": "2026-06-15T14:30:00Z"
}
```

---

`dietary_preference` is one of `non_vegetarian`, `eggetarian`, `vegetarian`, `vegan` (the food catalogue's filters); report-based plans use it.

### GET /users/me/medical-profile

Retrieve the user's medical profile. **404** if the user has not created one yet.

**Response (200):** Same schema as POST response above.

**Status Codes:**

| Code | Description         |
|------|---------------------|
| 200  | Success             |
| 404  | Profile not found   |

---

### DELETE /users/me

Permanently delete the account and all of its data: reports (and their encrypted files), biomarkers, analyses, recommendations, suggestions, plans, progress, medical profile and notifications. Audit logs are kept until they expire (`AUDIT_LOG_RETENTION_DAYS`).

**Request Body:** `{"password": "..."}`

| Code | Description        |
|------|--------------------|
| 204  | Deleted            |
| 403  | Incorrect password |

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

### DELETE /reports/{report_id}

Delete a report, its encrypted upload and everything derived from it (biomarkers, analysis, recommendations, suggestions and report-built plans). **Response:** 204.

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

Get the analysis results for a processed report. Until the report is
`completed` only `report_id` and `status` are returned.

`biomarkers` maps each marker to its value, unit, status (`low`, `high`,
`normal` or `unknown`) and reference range, recomputed on every request with
the current rules. Blood counts and hemoglobin are shown on the scale the lab
printed them in (e.g. `7.1 ×10³/µL`, `2.5 lakhs/µL`, `112 g/L`) and judged on
one canonical scale; for WBC, platelets and RBC the lab's own printed range is
used when present (`"source": "lab"`). A count whose scale cannot be worked
out has `"status": "unknown"`, `"range": null` and a `note`.

**Response (200):**

```json
{
  "report_id": "664c...",
  "status": "completed",
  "biomarkers": {
    "hemoglobin": {"value": 11.2, "unit": "g/dL", "status": "low", "range": "13.0-17.0", "source": "standard"},
    "wbc": {"value": 7.1, "unit": "×10³/µL", "status": "normal", "range": "4-11", "source": "lab"},
    "platelets": {"value": 7.0, "unit": "", "status": "unknown", "range": null,
                  "note": "unit unclear; compare with the range printed on your report"},
    "vitamin_d": {"value": 22.0, "unit": "ng/mL", "status": "low", "range": "30-100"}
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

> If the model does not answer within `LLM_TIMEOUT_SECONDS` (default 300) or its plan fails verification, a deterministic template plan that respects the same preferences is returned instead, and the outcome is recorded in `generation_metrics` (see `/health/ready`).

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

### GET /nutrition/diet-plans

The user's saved diet plans, newest first, in the same shape `generate-diet` returns. Query: `limit` (1–100, default 20).

---

## Fitness

### POST /fitness/generate-workout

Generate an AI-powered workout plan.

> If the model does not answer within `LLM_TIMEOUT_SECONDS` (default 300) or its plan fails verification, a deterministic template plan that respects the same preferences is returned instead, and the outcome is recorded in `generation_metrics` (see `/health/ready`).

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

### GET /fitness/plans

Saved workout plans, newest first, as stored (including warm-ups, instructions and alternatives, which `/fitness/workout-plans` trims). Plans whose generation failed are skipped. Query: `limit` (1–100, default 20).

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

## Notifications

Written by the report pipeline (e.g. "Report Analysis Complete"), each with the `report_id` it is about.

### GET /notifications/

**Response (200):** `{"items": [{"id", "type", "title", "message", "read", "report_id", "created_at"}], "unread_count": 2}`. Query: `limit` (1–100, default 30).

### POST /notifications/{notification_id}/read

Mark one notification read. **Response:** 204.

### POST /notifications/read-all

Mark all of the user's notifications read. **Response:** 204.

---

## Admin

Admin role only (403 otherwise). Exposes account metadata and counts, never report contents.

### GET /admin/stats

Counts of users, reports (total, last 7 days, by status), plans and progress entries.

### GET /admin/users

Users, newest first, with their report counts. Query: `q` (name or email contains), `limit` (default 100).

### PATCH /admin/users/{user_id}/role

**Request Body:** `{"role": "user" | "admin"}`. Admins cannot change their own role (400).

### DELETE /admin/users/{user_id}

Delete a user and all their data, as `DELETE /users/me` does. Admins cannot delete themselves here (400). **Response:** 204.

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
