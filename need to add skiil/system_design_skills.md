# 🧠 System Design — Agent Skills

---

## 1. High-Level Flow

User → /skills command  
→ Skill Resolver  
→ Markdown Parser  
→ Skill Compiler  
→ Skill Executor  
→ Tools  
→ Output + Artifacts  

---

## 2. Architecture Components

### Skill Resolver
- selects notebook or global skill

### Markdown Parser
- converts .md → JSON

### Skill Compiler
- expands vague steps using LLM

### Skill Executor
- runs step-by-step execution loop

### Tool Mapper
- maps step → tool

---

## 3. Execution Engine

for step in plan:
  tool = map(step)
  result = execute(tool)
  store(result)

---

## 4. Tool System

### Core Tools
- rag → retrieval
- llm → reasoning
- python_auto → execution
- web → external

### Extended Tools
- package installer
- validation
- memory store

---

## 5. Sandbox

- docker execution preferred
- no network
- resource limits
- safe file system

---

## 6. Data Flow

Markdown → JSON → Plan → Execution → Result  

---

## 7. Scaling

- async execution
- job queue for long skills
- caching results

---

## 8. Observability

- logs per step
- execution trace
- error tracking