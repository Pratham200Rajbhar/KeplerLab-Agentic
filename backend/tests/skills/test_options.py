from app.services.skills.markdown_parser import parse_skill_markdown

markdown = """# Skill: Options Test
## Input
difficulty: {difficulty} [Easy, Medium, Hard]
style: {style} [Academic, Casual, Professional] (textarea)
no_options: {no_options}
topic: {user_input} (search_box)

## Steps
1. Think
## Output
- Result
## Rules
- none
"""

parsed = parse_skill_markdown(markdown)
for var in parsed.inputs:
    print(f"Name: {var.name}")
    print(f"Options: {var.options}")
    print(f"Type: {var.input_type}")
    print("---")
