import httpx
import base64
from app.config import settings

class SarvamSTT:
    """
    Sarvam AI Speech-to-Text service wrapper.
    Uses async httpx to avoid blocking the event loop.
    """
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.stt_url = "https://api.sarvam.ai/speech-to-text"
        
    async def transcribe(self, wav_bytes: bytes) -> dict:
        """
        Transcribes WAV audio bytes to text using Sarvam AI saaras:v3 model.
        Returns dict with transcript and language code.
        """
        if not self.api_key or self.api_key == "your_sarvam_api_key":
            print("WARNING: Sarvam STT called but no API key configured. Returning stub.")
            return {"transcript": "Hello, there is a pothole in T Nagar.", "language_code": "hi-IN", "confidence": 0.9}

        headers = {
            "api-subscription-key": self.api_key
        }
        
        files = {
            'file': ('audio.wav', wav_bytes, 'audio/wav')
        }
        data = {
            'model': settings.SARVAM_STT_MODEL,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.stt_url, 
                    headers=headers, 
                    files=files, 
                    data=data
                )
                response.raise_for_status()
                res_json = response.json()
            
            transcript = res_json.get("transcript", "")
            lang = res_json.get("language_code", "en-IN")
            
            print(f"STT Result: lang={lang}, text='{transcript[:80]}'")
            
            return {
                "transcript": transcript,
                "language_code": lang,
                "confidence": 0.95
            }
        except Exception as e:
            print(f"Sarvam STT Error: {e}")
            return {"transcript": "", "language_code": "en-IN", "confidence": 0.0}

stt_service = SarvamSTT()
