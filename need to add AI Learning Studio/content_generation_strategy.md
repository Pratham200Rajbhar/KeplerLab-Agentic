# AI Learning Studio - Content Generation Strategy

## 1. Purpose
Define how curriculum and daily session content are generated, validated, and adapted while keeping output structured and reliable.

## 2. Generation Layers

### Layer 1: Curriculum Generation
Input:
- topic
- duration_days
- level
- goal_type

Output:
- ordered day skeletons (title, objective, expected outcomes, difficulty step)
- final day marked as capstone project

### Layer 2: Day Session Generation
Input:
- day skeleton
- prior progress summary
- weak-topic profile

Output JSON shape:
- lesson
- interaction
- task
- quiz
- game
- metadata (difficulty, estimated_minutes, objectives)

### Layer 3: Adaptive Reinforcement
Input:
- weak topics and confidence
- recent mistakes
- pass/fail patterns

Output:
- reinforced explanations
- targeted quiz distractor design
- additional mini-drills

## 3. Prompt Design Rules
- Require strict JSON output with schema validation.
- Include explicit pedagogy constraints for each stage.
- Keep stage outputs concise enough for single-session execution.
- Use deterministic tone settings for consistency.
- Disallow references to uploaded files or external user materials.

## 4. Prompt Families

### 4.1 Curriculum Prompt
Responsibilities:
- Build full day-by-day learning arc
- Progress difficulty gradually
- Align with selected goal type

### 4.2 Day Generation Prompt
Responsibilities:
- Generate all stage content for a specific day
- Ensure each stage maps to day objective
- Include quiz pass threshold and answer key

### 4.3 Interaction Evaluation Prompt
Responsibilities:
- Assess freeform user responses
- Return rubric score + concept coverage
- Return actionable feedback and retry hints

### 4.4 Quiz Generation Prompt
Responsibilities:
- Produce balanced MCQs
- Include rationale for each correct answer
- Include misconception-aware distractors

### 4.5 Game Generation Prompt
Responsibilities:
- Produce short interactive challenge rounds
- Keep game mechanics simple and deterministic
- Ensure educational objective remains central

### 4.6 Adaptive Reinforcement Prompt
Responsibilities:
- Transform weak-topic profile into targeted reinforcement
- Increase explanation depth for weak concepts
- Reduce repetition for strong concepts

## 5. Quality Controls

### 5.1 Schema Validation
- Validate all generated outputs against strict schema before persistence.
- Reject and retry if required fields missing.

### 5.2 Safety and Consistency Checks
- No hallucinated references to uploaded docs.
- No contradictory answer keys.
- No stage missing from required pipeline.

### 5.3 Retry Strategy
- Retry with lower temperature and tightened instructions on parse failures.
- Maximum retry count configurable (suggest 2).

## 6. Determinism vs Creativity
- Curriculum/day structure generation: low temperature.
- Explanations and examples: moderate creativity allowed.
- Quiz answers/keys: deterministic and strict.

## 7. Adaptive Scoring Strategy
Track per topic:
- confidence (0.0-1.0)
- mistakes count
- recency of mistakes

Update rules (example):
- Correct high-confidence answers increase confidence by +0.05 (cap 1.0)
- Incorrect answers decrease by -0.1 (floor 0.0)
- Recent repeated mistakes add reinforcement priority weight

## 8. Fallback Behavior
If generation fails:
- Return graceful message and retry action to UI
- Preserve existing session state
- Do not unlock or advance stages on failure

## 9. Evaluation Loop
Offline and beta evaluation should score:
- pedagogical coherence
- objective alignment
- difficulty progression quality
- answer-key correctness
- user satisfaction feedback

## 10. Prompt Versioning
- Store prompt version string with generated day metadata.
- Allow future A/B testing by prompt version.
- Keep migration path if schema evolves.

## 11. Recommended MVP Constraints
- Keep lesson length bounded (e.g., 3-5 sections).
- Keep interaction questions to 2-4 prompts.
- Keep quiz to 5-8 MCQs.
- Keep game to 2-4 rounds.
- Keep total session target duration to 20-35 minutes.
