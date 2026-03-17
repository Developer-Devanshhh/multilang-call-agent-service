import httpx
import base64
from app.config import settings

class SarvamTTS:
    """
    Sarvam AI Text-to-Speech service wrapper.
    Uses Bulbul v2 (legacy) or v3 (latest).
    """
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.url = "https://api.sarvam.ai/text-to-speech"
        
    async def synthesize(self, text: str, target_language: str = "hi-IN") -> bytes:
        """
        Converts text to speech using Sarvam AI TTS.
        Returns raw audio bytes (base64-decoded WAV from Sarvam).
        """
        if not self.api_key or self.api_key == "your_sarvam_api_key":
            print("WARNING: Sarvam TTS called but no API key configured.")
            return b'\x00' * 3200

        # Normalize language code to xx-IN format
        if "-" not in target_language:
            if target_language == "en":
                target_language = "en-IN"
            else:
                target_language = f"{target_language}-IN"

        # Truncate text to 1500 chars (bulbul v2 limit)
        if len(text) > 1500:
            text = text[:1500]

        # Use bulbul:v3 strictly as per latest API format
        payload = {
            "inputs": [text],
            "target_language_code": target_language,
            "speaker": "shubh",
            "pace": 1.0,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model": "bulbul:v3"
        }
        
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                
                if response.status_code == 400:
                    error_detail = response.text
                    print(f"TTS 400 error: {error_detail}")

                response.raise_for_status()
                res_json = response.json()
            
            if res_json.get("audios") and len(res_json["audios"]) > 0:
                b64_audio = res_json["audios"][0]
                audio_bytes = base64.b64decode(b64_audio)
                print(f"TTS: Generated {len(audio_bytes)} bytes of audio for '{text[:50]}...'")
                return audio_bytes
            
            print("TTS: No audio in response")
            return b''
        except Exception as e:
            print(f"Sarvam TTS Error: {e}")
            return b''

tts_service = SarvamTTS()
