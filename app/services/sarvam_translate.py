import httpx
from app.config import settings

class SarvamTranslate:
    """
    Sarvam AI Translation service wrapper.
    Uses async httpx to avoid blocking the event loop.
    """
    def __init__(self):
        self.api_key = settings.SARVAM_API_KEY
        self.url = "https://api.sarvam.ai/translate"
        
    async def translate(self, text: str, source_language: str, target_language: str) -> str:
        """
        Translates text between two Indian languages or Indian/English.
        """
        if not text or not text.strip():
            return text
            
        if not self.api_key or self.api_key == "your_sarvam_api_key":
            print("WARNING: Sarvam Translate called but no API key configured.")
            return text

        # Skip translation if source == target
        src = source_language.split("-")[0]
        tgt = target_language.split("-")[0]
        if src == tgt:
            return text
            
        # Normalize language codes to xx-IN format
        if "-" not in source_language:
            source_language = "en-IN" if source_language == "en" else f"{source_language}-IN"
        if "-" not in target_language:
            target_language = "en-IN" if target_language == "en" else f"{target_language}-IN"
            
        payload = {
            "input": text,
            "source_language_code": source_language,
            "target_language_code": target_language,
            "speaker_gender": "Female",
            "mode": "formal",
            "model": settings.SARVAM_TRANSLATE_MODEL,
        }
        
        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(self.url, json=payload, headers=headers)
                response.raise_for_status()
                res_json = response.json()
            
            translated = res_json.get("translated_text", text)
            print(f"Translate [{source_language}->{target_language}]: '{text[:40]}' -> '{translated[:40]}'")
            return translated
        except Exception as e:
            print(f"Sarvam Translate Error: {e}")
            return text

translate_service = SarvamTranslate()
