Evaluate step execution and decide next action.

Date: {today}
Goal: {goal}
Step: {step_number}/{total_steps}
Step Description: {latest_step}

## Result
Success: {success}
Output: {latest_result}
Error: {error}

## Artifacts
{artifacts}

## Observations
{observations}

## Decision Options
Choose ONE:
- **continue** — Step succeeded, proceed to next step
- **retry_with_fix** — Step failed. Provide corrected description
- **replan** — Plan insufficient. Provide new steps as JSON array
- **complete** — Goal achieved

## Output Format
```
DECISION: <decision>
REASON: <one sentence>
NEW_STEPS: <JSON array if replan, corrected description if retry, empty if continue/complete>
```

## Examples
```
DECISION: continue
REASON: Data loaded successfully, 1000 rows found.
NEW_STEPS:
```

```
DECISION: retry_with_fix
REASON: CSV delimiter was semicolon, not comma.
NEW_STEPS: Load CSV with delimiter=';' and verify structure
```

```
DECISION: replan
REASON: Need to clean data before analysis.
NEW_STEPS: [{"description": "Remove null values and outliers", "tool_hint": "python_auto"}, {"description": "Generate cleaned data summary PDF", "tool_hint": "python_auto"}]
```
