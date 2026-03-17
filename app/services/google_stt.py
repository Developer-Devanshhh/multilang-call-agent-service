import os
from google.cloud import speech
from app.config import settings

class GoogleCloudSTT:
    """
    Google Cloud Speech-to-Text wrapper.
    Requires GOOGLE_APPLICATION_CREDENTIALS to be set in .env
    """
    def __init__(self):
        # We need to make sure the library uses the credentials file if provided
        if settings.GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(settings.GOOGLE_APPLICATION_CREDENTIALS):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
            
        try:
            self.client = speech.SpeechAsyncClient()
        except Exception as e:
            print(f"Failed to initialize Google Speech API: {e}")
            self.client = None

    async def transcribe(self, wav_bytes: bytes) -> dict:
        """
        Transcribes WAV audio bytes to text using Google STT.
        Returns dict with transcript and language code.
        """
        if not self.client:
            print("WARNING: Google STT client not initialized. Check credentials.")
            # Return empty text to avoid infinite AI loops
            return {"transcript": "", "language_code": "en-IN", "confidence": 0.0}
            
        try:
            audio = speech.RecognitionAudio(content=wav_bytes)
            
            # 8kHz is standard for telephony/demo output
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=8000,
                language_code="hi-IN", # Recognize Hindi + English code-mixing
                alternative_language_codes=["en-IN", "ta-IN", "te-IN"],
                model="telephony",     # Optimized for phone calls
                use_enhanced=True
            )

            # Note: recognize() is blocking on the sync client, but here we use the async client's recognize 
            response = await self.client.recognize(config=config, audio=audio)
            
            if not response.results:
                return {"transcript": "", "language_code": "en-IN", "confidence": 0.0}

            # Get the best transcript
            best_alternative = response.results[0].alternatives[0]
            transcript = best_alternative.transcript
            confidence = best_alternative.confidence
            
            # Google STT returns the language code that was matched if alternative_language_codes is used
            lang = response.results[0].language_code if response.results[0].language_code else "en-IN"
            
            print(f"[Google STT] [{lang}] {transcript} (conf: {confidence})")
            
            return {
                "transcript": transcript,
                "language_code": lang,
                "confidence": confidence
            }
        except Exception as e:
            print(f"Google STT Error: {e}")
            return {"transcript": "", "language_code": "en-IN", "confidence": 0.0}

stt_service = GoogleCloudSTT()
