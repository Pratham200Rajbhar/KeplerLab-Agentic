import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()

from app.services.presentation.pptx_extractor import extract_slides_from_pptx
from app.services.presentation.slide_narrator import generate_narration_scripts

async def main():
    pptx_path = "/disk1/KeplerLab_Agentic/4. IaaS.pptx"
    
    print(f"Reading {pptx_path}...")
    with open(pptx_path, "rb") as f:
        file_bytes = f.read()
        
    print("Extracting slides from PPTX...")
    extracted = await extract_slides_from_pptx(file_bytes, "4. IaaS.pptx")
    print(f"Extracted {len(extracted)} slides.")
    
    test_limit = min(3, len(extracted))
    print(f"Testing vision pipeline on the first {test_limit} slides...")
    
    slide_data = []
    image_paths = []
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(test_limit):
            slide = extracted[i]
            img_path = os.path.join(temp_dir, f"slide_{slide.index:03d}.png")
            with open(img_path, "wb") as f:
                f.write(slide.image_bytes)
            
            slide_dict = {
                "title": slide.title,
                "bullets": slide.bullets
            }
            slide_data.append(slide_dict)
            image_paths.append(img_path)
            
        print("Invoking Vertex AI Vision Narration...")
        results = await generate_narration_scripts(
            slides=slide_data,
            image_paths=image_paths,
            presentation_title="IaaS Explanation",
            narration_language="English",
            narration_style="teacher",
            narration_notes="Explain the infrastructure concepts simply for beginners based on the diagrams.",
            use_vision=True
        )
        
        for idx, script in enumerate(results):
            print(f"\n======== SLIDE {idx + 1} NARRATION SCRIPT ========")
            print(script)
            print("==================================================\n")
            
if __name__ == "__main__":
    asyncio.run(main())
