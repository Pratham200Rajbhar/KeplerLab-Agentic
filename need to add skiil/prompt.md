You are a senior AI backend engineer tasked with implementing a production-grade Markdown-based Agent Skills system.

Your goal is to build a system where users can create, store, and execute skills as Markdown files that define AI workflows.

System Requirements:

1. Skills System:

* Skills are stored as Markdown (.md) in database
* Support global and notebook-level skills
* Skills are triggered via /skills {name}

2. Markdown Parsing:

* Parse sections: Input, Steps, Output, Rules
* Convert Markdown → structured JSON
* Validate structure

3. Skill Execution Engine:

* Resolve skill (notebook → global fallback)
* Compile steps using LLM into optimized plan
* Execute steps sequentially
* Map steps to tools:

  * rag → retrieval
  * llm → reasoning
  * python_auto → execution
  * web_search → external data

4. Tool System:

* Implement modular tools
* Add dynamic tool capability:

  * install Python packages safely
  * execute new capabilities
* Ensure all tools return structured output

5. Sandbox:

* Execute Python in isolated environment
* Restrict unsafe operations
* Limit CPU, memory, execution time
* Store generated artifacts

6. Features:

* variable support ({user_input})
* conditional logic (IF/ELSE)
* step retry mechanism
* execution logs
* artifact generation

7. API:

* CRUD skills
* run skill endpoint
* list skills

8. Observability:

* log each step execution
* track errors
* provide execution trace

9. Frontend Support:

* Markdown editor
* run skill button
* logs + artifact viewer

10. Ensure:

* modular architecture
* production-grade reliability
* secure execution
* scalable design

Output:

* backend implementation
* skill engine modules
* parser
* executor
* tool integration
* example skills
