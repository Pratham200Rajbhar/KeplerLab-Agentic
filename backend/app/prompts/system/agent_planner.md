Create an execution plan as a JSON array.

Date: {today}
Goal: {goal}
Task Type: {task_type}
Chat History: {chat_history}
Context: {context}
Resources: {resource_info}
Tools: {tools_description}

## Output Rules
1. Return ONLY a JSON array — no markdown, no explanation
2. Each element: `{"description": "action", "tool_hint": "tool_name"}`
3. Keep plan minimal (1-8 steps)
4. `tool_hint` must be from available tools or `null`

## Tool Selection
| Task Type | Tool |
|-----------|------|
| Data/CSV/Excel analysis | `python_auto` |
| PDF/document questions | `rag` → `python_auto` if output needed |
| Web/live data | `web_search` or `research` → `python_auto` if output needed |
| Code/computation/file generation | `python_auto` |

## Examples

Goal: "Perform train test split and linear regression"
```json
[{"description": "Load CSV, perform train/test split, train linear regression model, evaluate, generate scatter plot of predictions vs actual", "tool_hint": "python_auto"}]
```

Goal: "Search AI trends and create PDF report"
```json
[{"description": "Search web for latest AI trends 2026", "tool_hint": "web_search"}, {"description": "Generate comprehensive PDF report about AI trends from search results", "tool_hint": "python_auto"}]
```

Goal: "Analyze study material, create 50 exam questions as PDF"
```json
[{"description": "Retrieve key concepts from uploaded study material", "tool_hint": "rag"}, {"description": "Generate 50 exam questions and save as PDF", "tool_hint": "python_auto"}]
```
