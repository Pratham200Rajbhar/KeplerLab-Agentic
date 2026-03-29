# AI Learning Studio - Frontend Specification

## 1. Scope
Define frontend implementation details for AI Learning Studio in the current Next.js app.

Feature goals:
- New top-level route: /learning
- Plan creation workflow
- Left day-list navigation with lock states
- Main session panel with stage progression
- Progress/streak visualization

## 2. Integration Points in Existing Frontend
Current app patterns to follow:
- App router pages under frontend/src/app
- API wrappers under frontend/src/lib/api
- Global state with Zustand stores in frontend/src/stores
- Existing authenticated workflow handled by middleware/auth store

## 3. Route and Navigation

### 3.1 New Route
Add:
- frontend/src/app/learning/page.jsx

Behavior:
- Requires authenticated session (middleware already enforces)
- Loads user paths and active path on entry

### 3.2 Navigation Entry
Add AI Learning Studio item in main navigation (existing sidebar/navigation component path used by workspace flow).

Expected behavior:
- Click navigates to /learning
- Visual active state when path starts with /learning

## 4. Component Architecture

### 4.1 Top-Level Layout
Learning page should render:
- ProgressHeader
- DayListPanel
- SessionPanel
- CreatePlanModal (when no active path or create action)

### 4.2 Proposed Component Files
- frontend/src/components/learning/LearningDashboard.jsx
- frontend/src/components/learning/ProgressHeader.jsx
- frontend/src/components/learning/DayListPanel.jsx
- frontend/src/components/learning/SessionPanel.jsx
- frontend/src/components/learning/CreatePlanModal.jsx
- frontend/src/components/learning/stages/LessonStage.jsx
- frontend/src/components/learning/stages/InteractionStage.jsx
- frontend/src/components/learning/stages/TaskStage.jsx
- frontend/src/components/learning/stages/QuizStage.jsx
- frontend/src/components/learning/stages/GameStage.jsx
- frontend/src/components/learning/ReviewPanel.jsx

## 5. State Management

### 5.1 New Store
Create:
- frontend/src/stores/useLearningStore.js

### 5.2 Suggested Store Shape
```js
{
  paths: [],
  activePath: null,
  days: [],
  activeDay: null,
  session: null,
  dayContent: null,
  progress: null,
  reviewRecommendations: [],
  loading: {
    paths: false,
    createPath: false,
    openDay: false,
    submitStage: false,
    completeDay: false,
  },
  error: null,

  // actions
  loadPaths,
  createPath,
  selectPath,
  loadDays,
  openDay,
  submitInteraction,
  submitTask,
  submitQuiz,
  submitGame,
  completeDay,
  loadProgress,
  loadReview,
  reset
}
```

### 5.3 Interaction Rules
- Do not allow selecting locked day.
- Do not show future stages before session stage reached.
- Disable submit button while stage request in progress.
- Update local state optimistically only when safe; otherwise use server truth.

## 6. API Client Module
Create:
- frontend/src/lib/api/learning.js

Functions:
- createLearningPath(payload)
- listLearningPaths(params)
- getLearningPath(pathId)
- listLearningDays(pathId)
- openLearningDay(dayId, forceRegenerate)
- submitLearningInteraction(dayId, payload)
- submitLearningTask(dayId, payload)
- submitLearningQuiz(dayId, payload)
- submitLearningGame(dayId, payload)
- completeLearningDay(dayId)
- getLearningProgress(pathId)
- getLearningReview(pathId)

Implementation pattern:
- Reuse existing api config wrapper for auth header and error handling.

## 7. UX States and Behavior

### 7.1 Empty States
- No learning paths yet: show create plan CTA.
- Path exists but no day opened: prompt user to select current unlocked day.

### 7.2 Loading States
- Path list skeleton
- Day panel skeleton
- Session stage skeleton for lazy generation

### 7.3 Error States
- Path/day load failures with retry button
- Stage submit failure with non-destructive retry
- Locked day selection warning

### 7.4 Completion States
- Day complete animation/message
- Next day unlock visual update
- Progress and streak refresh

## 8. Stage Component Contracts

### 8.1 LessonStage
Inputs:
- lesson payload
- onContinue callback

### 8.2 InteractionStage
Inputs:
- interaction questions
- onSubmit callback
Outputs:
- answers payload

### 8.3 TaskStage
Inputs:
- task instructions and criteria
- onSubmit callback
Outputs:
- freeform submission string/object

### 8.4 QuizStage
Inputs:
- quiz questions and pass score
- onSubmit callback
Outputs:
- selected options payload

### 8.5 GameStage
Inputs:
- game rounds
- onSubmit callback
Outputs:
- moves/challenge answers payload

## 9. Accessibility and Responsiveness
- Keyboard navigable day list and stage actions.
- ARIA labels for lock/completed indicators.
- Mobile behavior:
  - day list collapses into drawer or horizontal selector
  - stage content remains readable without overflow

## 10. Analytics Events (Frontend)
Emit at least:
- learning_path_create_clicked
- learning_path_created
- learning_day_opened
- learning_stage_submitted
- learning_stage_failed
- learning_day_completed
- learning_review_opened

Include context fields:
- path_id
- day_id
- stage
- duration_ms

## 11. Suggested Delivery Order
1. Route + basic dashboard shell
2. Store + API client
3. Path creation + day list
4. Day open + lesson stage
5. Interaction/task/quiz/game stages
6. Completion + progress refresh
7. Review mode and polishing
