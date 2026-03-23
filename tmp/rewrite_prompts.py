import os
import re
from pathlib import Path

PROMPTS_DIR = "/disk1/KeplerLab_Agentic/backend/app/prompts"

def extract_variables(text):
    # Find all {var_name}
    return sorted(list(set(re.findall(r'\{([A-Za-z0-9_]+)\}', text))))

def rewrite_prompt(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Do not parse anything if it has no variables, but wait, some files might just be rules.
    variables = extract_variables(content)
    
    # Try to extract Task description
    task_match = re.search(r'Task:\s*(.*)', content)
    task_desc = task_match.group(1).strip() if task_match else ""
    
    filename = os.path.basename(filepath)
    
    if "shared" in filepath:
        # For shared rules, make them very soft or just empty.
        new_content = "Please be natural, helpful, and answer like ChatGPT or Claude without strict restrictions or fixed formatting."
        if variables:
            inputs = "\n".join([f"- {v}: {{{v}}}" for v in variables])
            new_content += f"\n\nContext:\n{inputs}"
        
        with open(filepath, 'w') as f:
            f.write(new_content)
        return

    # Build the new clean prompt
    new_content = "You are a helpful, advanced AI assistant (like ChatGPT or Claude). "
    new_content += "Respond naturally and remove unnecessary restrictions, rules, or fixed outputs.\n\n"
    
    if task_desc:
        new_content += f"Your objective: {task_desc}\n\n"
    elif filename in ["agent_system.md", "base_system.md", "chat_base.md"]:
        new_content += "Your objective: Act as a versatile, capable conversational agent.\n\n"
    else:
        new_content += f"Your objective: Process the prompt and context appropriately to fulfill the user's intent.\n\n"
        
    if variables:
        # Re-add inputs clearly
        inputs = "\n".join([f"- {v.title().replace('_', ' ')}: {{{v}}}" for v in variables])
        new_content += f"Information and Context:\n{inputs}\n"
        
    with open(filepath, 'w') as f:
        f.write(new_content.strip())
        f.write("\n")

def main():
    path = Path(PROMPTS_DIR)
    paths = list(path.rglob("*.md"))
    for p in paths:
        rewrite_prompt(str(p))
        print(f"Rewrote: {p}")

if __name__ == "__main__":
    main()
