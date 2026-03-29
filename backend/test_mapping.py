
import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.getcwd())

from app.services.skills.tool_mapper import map_step_to_tool

def test_mapping():
    test_cases = [
        ("Parse source material", True, "rag"),
        ("Read through the documents", True, "rag"),
        ("Analyze the uploaded notes", True, "rag"),
        ("Search the web for news", False, "web_search"),
        ("Summarize the findings", True, "llm"),
        ("Extract from context", True, "rag"),
        ("Deep research into topic", False, "research"),
        ("Generate a line chart", False, "python_auto"),
    ]

    print(f"{'Instruction':<30} | {'Has Mat':<7} | {'Expected':<12} | {'Actual':<12} | {'Result'}")
    print("-" * 80)
    
    passes = 0
    for instr, has_mat, expected in test_cases:
        actual = map_step_to_tool(instr, has_materials=has_mat)
        status = "✅" if actual == expected else "❌"
        if status == "✅": passes += 1
        print(f"{instr:<30} | {str(has_mat):<7} | {expected:<12} | {actual:<12} | {status}")

    print("-" * 80)
    print(f"Passed {passes}/{len(test_cases)}")
    
    if passes == len(test_cases):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    test_mapping()
