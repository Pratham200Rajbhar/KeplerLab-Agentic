import asyncio
import os
import sys

# Add backend dir to python path to allow importing app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.llm_service.llm import get_llm
from langchain_core.messages import HumanMessage

async def main():
    # Force use of Google provider for vision
    llm = get_llm(mode="creative", max_tokens=100, provider="GOOGLE")
    print(f"Testing Vision LLM with provider: {llm.__class__.__name__}")
    
    # Tiny 1x1 transparent PNG
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAACklEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
    mime = "image/png"
    
    print("\n--- TEST 1: Langchain Dictionary Syntax ---")
    message_dict = HumanMessage(content=[
        {
            "type": "text",
            "text": "What is this? Reply strictly with 1 word.",
        },
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{b64}"},
        },
    ])
    try:
        resp = await llm.ainvoke([message_dict])
        print("✅ SUCCESS (dictionary syntax):", resp.content)
    except Exception as e:
        print("❌ ERROR (dictionary syntax):", type(e).__name__, "-", str(e))
        
    print("\n--- TEST 2: Langchain String Syntax ---")
    message_str = HumanMessage(content=[
        {
            "type": "text",
            "text": "What is this? Reply strictly with 1 word.",
        },
        {
            "type": "image_url",
            "image_url": f"data:{mime};base64,{b64}",
        },
    ])
    try:
        resp = await llm.ainvoke([message_str])
        print("✅ SUCCESS (string syntax):", resp.content)
    except Exception as e:
        print("❌ ERROR (string syntax):", type(e).__name__, "-", str(e))

if __name__ == "__main__":
    asyncio.run(main())
