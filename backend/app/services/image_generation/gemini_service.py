import base64
import logging
from typing import Tuple
import requests
import subprocess
import os

from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_access_token() -> str:
    # 1. Prefer manually provided token from settings (for development/CI/specific envs)
    if settings.VERTEX_ACCESS_TOKEN:
        return settings.VERTEX_ACCESS_TOKEN

    # 2. Try google-auth library
    try:
        import google.auth
        from google.auth.transport.requests import Request
        credentials, _ = google.auth.default()
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        logger.warning(f"Failed to get google-auth token, fallback to gcloud CLI: {e}")
        # 3. Fallback to gcloud CLI
        try:
            result = subprocess.run(["gcloud", "auth", "application-default", "print-access-token"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except Exception as ge:
            logger.error(f"Failed to get access token via gcloud: {ge}")
            return ""

def _get_project_id() -> str:
    # Use setting if provided, otherwise you might want to auto-detect, but here we prioritize the config.
    return settings.VERTEX_PROJECT_ID or "project-2013f55b-2888-4590-9b5"

def generate_image(prompt: str) -> Tuple[bytes, str]:
    """
    Generate an image using the Imagen 3.0 Vertex AI API.
    Returns a tuple of (image_bytes, enhanced_prompt).
    """
    project_id = _get_project_id()
    access_token = _get_access_token()
    location = settings.VERTEX_LOCATION or "us-central1"
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/publishers/google/models/gemini-2.5-flash-image:generateContent"
    
    # Simple prompt enhancement: we just append some high-quality style instructions
    enhanced_prompt = f"{prompt.strip()}, high quality, highly detailed, masterpieces, vibrant colors, 4k"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": enhanced_prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(
            url, 
            json=payload, 
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}"
            }, 
            timeout=30
        )
        if not response.ok:
            logger.error(f"Imagen HTTP Error: {response.status_code} - {response.text}")
            response.raise_for_status()
            
        data = response.json()
        
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError(f"No candidates returned from API. Data: {data}")
            
        parts = candidates[0].get("content", {}).get("parts", [])
        b64_data = None
        for part in parts:
            if "inlineData" in part:
                b64_data = part["inlineData"].get("data")
                break
                
        if not b64_data:
            raise ValueError(f"No image data returned from the API. Prediction parts: {parts}")
            
        image_bytes = base64.b64decode(str(b64_data))
        return image_bytes, enhanced_prompt

    except Exception as exc:
        logger.error(f"Failed to generate image via Imagen API: {exc}")
        raise
