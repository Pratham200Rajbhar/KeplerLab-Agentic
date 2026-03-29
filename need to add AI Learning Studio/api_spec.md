# AI Learning Studio - API Specification (v1)

## 1. Conventions
- Base URL: existing backend API host
- Prefix: /learning
- Auth: existing bearer auth via get_current_user dependency
- Content type: application/json
- Time format: ISO-8601 UTC

Error envelope:
{
  "detail": "Human-readable error message"
}

## 2. Enums

### PathLevel
- beginner
- intermediate
- advanced

### GoalType
- exam_prep
- career_switch
- project_build
- concept_mastery

### PathStatus
- active
- paused
- completed
- archived

### DayStatus
- pending
- in_progress
- completed

### SessionStage
- LESSON
- INTERACTION
- TASK
- QUIZ
- GAME
- COMPLETE

## 3. Endpoints

### 3.1 Create Learning Path
POST /learning/paths

Request:
{
  "topic": "Machine Learning",
  "duration_days": 30,
  "level": "beginner",
  "goal_type": "career_switch",
  "title": "ML in 30 Days"
}

Response 201:
{
  "id": "uuid",
  "title": "ML in 30 Days",
  "topic": "Machine Learning",
  "duration_days": 30,
  "level": "beginner",
  "goal_type": "career_switch",
  "status": "active",
  "created_at": "2026-03-29T12:00:00Z"
}

Validation:
- duration_days must be within configured bounds (default 7-90)
- topic and title non-empty with max length constraints

### 3.2 List Learning Paths
GET /learning/paths?status=active

Response 200:
{
  "paths": [
    {
      "id": "uuid",
      "title": "ML in 30 Days",
      "duration_days": 30,
      "level": "beginner",
      "goal_type": "career_switch",
      "status": "active",
      "completion_percentage": 13.3,
      "current_day": 4,
      "streak": 3,
      "updated_at": "2026-03-29T12:00:00Z"
    }
  ]
}

### 3.3 Get Path Detail
GET /learning/paths/{path_id}

Response 200:
{
  "id": "uuid",
  "title": "ML in 30 Days",
  "topic": "Machine Learning",
  "duration_days": 30,
  "level": "beginner",
  "goal_type": "career_switch",
  "status": "active",
  "created_at": "2026-03-01T10:00:00Z",
  "updated_at": "2026-03-29T12:00:00Z"
}

### 3.4 List Days in Path
GET /learning/paths/{path_id}/days

Response 200:
{
  "days": [
    {
      "id": "uuid-day-1",
      "day_number": 1,
      "title": "Introduction to ML",
      "description": "Core concepts and terminology",
      "status": "completed",
      "is_unlocked": true,
      "has_generated_content": true
    },
    {
      "id": "uuid-day-2",
      "day_number": 2,
      "title": "Data and Features",
      "description": "Dataset basics and preprocessing",
      "status": "in_progress",
      "is_unlocked": true,
      "has_generated_content": true
    },
    {
      "id": "uuid-day-3",
      "day_number": 3,
      "title": "Linear Models",
      "description": "Regression and classification",
      "status": "pending",
      "is_unlocked": false,
      "has_generated_content": false
    }
  ]
}

### 3.5 Open Day (lazy generation)
POST /learning/days/{day_id}/open

Request:
{
  "force_regenerate": false
}

Response 200:
{
  "day": {
    "id": "uuid-day-2",
    "day_number": 2,
    "title": "Data and Features",
    "status": "in_progress"
  },
  "session": {
    "stage": "LESSON",
    "stage_index": 1,
    "total_stages": 6,
    "can_complete_day": false
  },
  "content": {
    "lesson": {
      "title": "Data Fundamentals",
      "sections": [
        {
          "heading": "What is a feature?",
          "text": "..."
        }
      ]
    },
    "interaction": {
      "questions": [
        {
          "id": "q1",
          "prompt": "Why do we normalize features?",
          "expected_concepts": ["scale", "stability"]
        }
      ]
    },
    "task": {
      "title": "Inspect a dataset",
      "instructions": ["..."],
      "completion_criteria": ["..."]
    },
    "quiz": {
      "questions": [
        {
          "id": "mcq1",
          "stem": "Which method handles missing values?",
          "options": ["A", "B", "C", "D"],
          "correct_option": "B"
        }
      ],
      "pass_score": 0.7
    },
    "game": {
      "type": "concept_match",
      "rounds": [
        {
          "id": "g1",
          "prompt": "Match concept to definition"
        }
      ]
    }
  }
}

Errors:
- 403/404 when day is locked or user does not own path/day

### 3.6 Submit Interaction Stage
POST /learning/days/{day_id}/interaction

Request:
{
  "answers": [
    {
      "question_id": "q1",
      "response": "Normalization prevents one feature from dominating"
    }
  ]
}

Response 200:
{
  "stage": "INTERACTION",
  "passed": true,
  "feedback": "Good explanation of scale sensitivity.",
  "next_stage": "TASK",
  "session": {
    "stage": "TASK",
    "stage_index": 3,
    "total_stages": 6
  }
}

### 3.7 Submit Task Stage
POST /learning/days/{day_id}/task

Request:
{
  "submission": "I analyzed missing values and feature distributions..."
}

Response 200:
{
  "stage": "TASK",
  "passed": true,
  "feedback": "Task completed with all criteria satisfied.",
  "next_stage": "QUIZ",
  "session": {
    "stage": "QUIZ",
    "stage_index": 4,
    "total_stages": 6
  }
}

### 3.8 Submit Quiz Stage
POST /learning/days/{day_id}/quiz

Request:
{
  "answers": [
    {"question_id": "mcq1", "selected_option": "B"}
  ]
}

Response 200:
{
  "stage": "QUIZ",
  "passed": true,
  "score": 0.8,
  "accuracy": 0.8,
  "feedback": "You answered 4/5 correctly.",
  "weak_topics": ["feature scaling"],
  "next_stage": "GAME",
  "session": {
    "stage": "GAME",
    "stage_index": 5,
    "total_stages": 6
  }
}

### 3.9 Submit Game Stage
POST /learning/days/{day_id}/game

Request:
{
  "moves": [
    {"round_id": "g1", "answer": "..."}
  ]
}

Response 200:
{
  "stage": "GAME",
  "passed": true,
  "xp_awarded": 30,
  "feedback": "Challenge complete.",
  "next_stage": "COMPLETE",
  "session": {
    "stage": "COMPLETE",
    "stage_index": 6,
    "total_stages": 6,
    "can_complete_day": true
  }
}

### 3.10 Complete Day
POST /learning/days/{day_id}/complete

Request:
{}

Response 200:
{
  "day_id": "uuid-day-2",
  "status": "completed",
  "unlocked_next_day_id": "uuid-day-3",
  "progress": {
    "current_day": 3,
    "completion_percentage": 6.67,
    "streak": 4,
    "last_active": "2026-03-29T12:30:00Z"
  }
}

### 3.11 Get Path Progress
GET /learning/paths/{path_id}/progress

Response 200:
{
  "path_id": "uuid",
  "current_day": 3,
  "completion_percentage": 6.67,
  "streak": 4,
  "quiz_accuracy": 0.78,
  "last_active": "2026-03-29T12:30:00Z",
  "weak_topics": [
    {"topic": "feature scaling", "confidence": 0.42}
  ]
}

### 3.12 Review Recommendations
GET /learning/paths/{path_id}/review

Response 200:
{
  "path_id": "uuid",
  "recommendations": [
    {
      "topic": "feature scaling",
      "reason": "Low quiz confidence",
      "suggested_actions": ["mini_lesson", "practice_quiz"]
    }
  ]
}

## 4. Optional Endpoints (Post-MVP)
- PATCH /learning/paths/{path_id} (edit title/goal)
- POST /learning/paths/{path_id}/pause
- POST /learning/paths/{path_id}/resume
- GET /learning/paths/{path_id}/analytics

## 5. Security Rules
- Every endpoint must enforce ownership by userId.
- IDs from other users should return not found behavior.
- Locked day operations should fail with 403 or domain-specific 409.

## 6. Idempotency and Retries
Recommended for stage submission and complete endpoints:
- Accept Idempotency-Key header
- Persist key hash per user/day/action for safe retries

## 7. Versioning
- Initial version: v1 under existing API namespace.
- Future incompatible changes should use v2 route group.
