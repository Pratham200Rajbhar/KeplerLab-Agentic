# AI Learning Studio - Database Design

## 1. Design Goals
- Keep learning data isolated and user-owned.
- Support strict day unlock progression.
- Support adaptive learning via weak-topic profile and attempts.
- Keep generated day content persisted for lazy-generation cache.

## 2. Proposed Prisma Enums

```prisma
enum LearningPathStatus {
  active
  paused
  completed
  archived
}

enum LearningDayStatus {
  pending
  in_progress
  completed
}

enum LearningSessionStage {
  LESSON
  INTERACTION
  TASK
  QUIZ
  GAME
  COMPLETE
}

enum LearningAttemptType {
  interaction
  task
  quiz
  game
}
```

## 3. Proposed Prisma Models

```prisma
model LearningPath {
  id            String             @id @default(uuid()) @db.Uuid
  userId        String             @map("user_id") @db.Uuid
  title         String             @db.VarChar(255)
  topic         String             @db.VarChar(255)
  durationDays  Int                @map("duration_days")
  level         String             @db.VarChar(30)
  goalType      String             @map("goal_type") @db.VarChar(50)
  status        LearningPathStatus @default(active)
  createdAt     DateTime           @default(now()) @map("created_at")
  updatedAt     DateTime           @default(now()) @updatedAt @map("updated_at")

  user          User               @relation(fields: [userId], references: [id], onDelete: Cascade)
  days          LearningDay[]
  progress      LearningProgress[]
  weakTopics    LearningWeakTopic[]

  @@index([userId])
  @@index([userId, status])
  @@index([createdAt])
  @@map("learning_paths")
}

model LearningDay {
  id              String           @id @default(uuid()) @db.Uuid
  pathId          String           @map("path_id") @db.Uuid
  dayNumber       Int              @map("day_number")
  title           String           @db.VarChar(255)
  description     String?          @db.Text
  status          LearningDayStatus @default(pending)
  isUnlocked      Boolean          @default(false) @map("is_unlocked")
  generatedContent Json?           @map("generated_content")
  generatedAt     DateTime?        @map("generated_at")
  createdAt       DateTime         @default(now()) @map("created_at")
  updatedAt       DateTime         @default(now()) @updatedAt @map("updated_at")

  path            LearningPath     @relation(fields: [pathId], references: [id], onDelete: Cascade)
  sessionStates   LearningSessionState[]
  attempts        LearningAttempt[]

  @@unique([pathId, dayNumber])
  @@index([pathId])
  @@index([pathId, status])
  @@index([pathId, isUnlocked])
  @@map("learning_days")
}

model LearningProgress {
  id                   String    @id @default(uuid()) @db.Uuid
  userId               String    @map("user_id") @db.Uuid
  pathId               String    @map("path_id") @db.Uuid
  currentDay           Int       @default(1) @map("current_day")
  completionPercentage Float     @default(0) @map("completion_percentage")
  streak               Int       @default(0)
  quizAccuracy         Float?    @map("quiz_accuracy")
  lastActive           DateTime? @map("last_active")
  createdAt            DateTime  @default(now()) @map("created_at")
  updatedAt            DateTime  @default(now()) @updatedAt @map("updated_at")

  user                 User         @relation(fields: [userId], references: [id], onDelete: Cascade)
  path                 LearningPath @relation(fields: [pathId], references: [id], onDelete: Cascade)

  @@unique([userId, pathId])
  @@index([userId])
  @@index([pathId])
  @@map("learning_progress")
}

model LearningSessionState {
  id             String              @id @default(uuid()) @db.Uuid
  userId         String              @map("user_id") @db.Uuid
  pathId         String              @map("path_id") @db.Uuid
  dayId          String              @map("day_id") @db.Uuid
  stage          LearningSessionStage @default(LESSON)
  stageIndex     Int                 @default(1) @map("stage_index")
  canCompleteDay Boolean             @default(false) @map("can_complete_day")
  stateData      Json?               @map("state_data")
  createdAt      DateTime            @default(now()) @map("created_at")
  updatedAt      DateTime            @default(now()) @updatedAt @map("updated_at")

  user           User           @relation(fields: [userId], references: [id], onDelete: Cascade)
  path           LearningPath   @relation(fields: [pathId], references: [id], onDelete: Cascade)
  day            LearningDay    @relation(fields: [dayId], references: [id], onDelete: Cascade)

  @@unique([userId, dayId])
  @@index([userId, pathId])
  @@map("learning_session_states")
}

model LearningAttempt {
  id           String             @id @default(uuid()) @db.Uuid
  userId       String             @map("user_id") @db.Uuid
  pathId       String             @map("path_id") @db.Uuid
  dayId        String             @map("day_id") @db.Uuid
  stage        LearningSessionStage
  attemptType  LearningAttemptType @map("attempt_type")
  inputData    Json?              @map("input_data")
  resultData   Json?              @map("result_data")
  score        Float?
  passed       Boolean            @default(false)
  createdAt    DateTime           @default(now()) @map("created_at")

  user         User         @relation(fields: [userId], references: [id], onDelete: Cascade)
  path         LearningPath @relation(fields: [pathId], references: [id], onDelete: Cascade)
  day          LearningDay  @relation(fields: [dayId], references: [id], onDelete: Cascade)

  @@index([userId, pathId])
  @@index([dayId, stage])
  @@index([createdAt])
  @@map("learning_attempts")
}

model LearningWeakTopic {
  id             String    @id @default(uuid()) @db.Uuid
  userId         String    @map("user_id") @db.Uuid
  pathId         String    @map("path_id") @db.Uuid
  topic          String    @db.VarChar(255)
  confidence     Float     @default(0.5)
  mistakeCount   Int       @default(0) @map("mistake_count")
  lastObservedAt DateTime? @map("last_observed_at")
  createdAt      DateTime  @default(now()) @map("created_at")
  updatedAt      DateTime  @default(now()) @updatedAt @map("updated_at")

  user           User         @relation(fields: [userId], references: [id], onDelete: Cascade)
  path           LearningPath @relation(fields: [pathId], references: [id], onDelete: Cascade)

  @@unique([userId, pathId, topic])
  @@index([userId, pathId])
  @@index([pathId, confidence])
  @@map("learning_weak_topics")
}
```

## 4. Relation Additions To Existing Models
Add relation lists to existing `User` model in backend/prisma/schema.prisma:
- learningPaths LearningPath[]
- learningProgress LearningProgress[]
- learningSessionStates LearningSessionState[]
- learningAttempts LearningAttempt[]
- learningWeakTopics LearningWeakTopic[]

No relation to Notebook is required for v1 since this system is intentionally separate.

## 5. Data Integrity Rules
- Exactly one unlocked day minimum for active path until completed.
- dayNumber unique within each path.
- Session state unique by (userId, dayId).
- Progress unique by (userId, pathId).
- Weak topic unique by (userId, pathId, topic).

## 6. Transactional Requirements
Must run in transaction:
- Path create + all day rows + initial progress row.
- Day completion + next day unlock + progress update.
- Stage submit + attempt persistence + session transition.

## 7. Migration Steps
1. Add new enums and models to backend/prisma/schema.prisma.
2. Generate migration SQL (or push in controlled environment per current workflow).
3. Run prisma generate.
4. Validate created indexes and constraints.
5. Backfill not required for v1 (new feature).

## 8. Query Patterns

### Frequent reads
- List paths by user and status
- List days by path ordered by day_number
- Read progress by (userId, pathId)
- Read session state by (userId, dayId)

### Frequent writes
- Insert attempts during stage submissions
- Update session state on stage transitions
- Update weak topics after quiz/interactions
- Update progress and path/day status on completion

## 9. Storage Notes for Generated Content
- Keep day-level generated JSON in `learning_days.generated_content`.
- Keep volatile runtime in `learning_session_states.state_data`.
- Keep attempt-level raw payloads in `learning_attempts.input_data/result_data`.

## 10. Retention and Cleanup
- Keep attempts for analytics and adaptive learning (default no hard delete).
- Optionally archive old completed paths in future by status=archived.
- Do not purge weak-topic data for active paths.

## 11. Future Extensions
- XP and rewards ledger table
- Capstone submission table (artifact references, rubric scores)
- Personalized teacher profile table
