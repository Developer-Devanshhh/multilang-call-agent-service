import audioop
import io
import wave
import base64
import os

def decode_twilio_audio(b64_payload: str) -> bytes:
    """Twilio/Telnyx: base64 μ-law -> raw PCM 16-bit 8kHz"""
    mulaw_bytes = base64.b64decode(b64_payload)
    pcm_bytes = audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit samples
    return pcm_bytes

def decode_exotel_audio(b64_payload: str) -> bytes:
    """Exotel: already PCM, just base64 decode"""
    return base64.b64decode(b64_payload)

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 8000) -> bytes:
    """Wrap raw PCM in WAV header for Sarvam STT"""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()

def encode_for_twilio(pcm_bytes: bytes) -> str:
    """PCM -> μ-law -> base64 for sending back to Twilio"""
    mulaw = audioop.lin2ulaw(pcm_bytes, 2)
    return base64.b64encode(mulaw).decode()

def encode_for_exotel(pcm_bytes: bytes) -> str:
    """PCM -> base64 for Exotel playback"""
    return base64.b64encode(pcm_bytes).decode()

def webm_to_pcm(webm_bytes: bytes) -> bytes:
    """Decode browser WebM audio to PCM 16-bit 8kHz mono"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(io.BytesIO(webm_bytes), format="webm")
        audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)
        return audio.raw_data
    except ImportError:
        # Fallback if ffmpeg/pydub is an issue, but we require it for demo
        print("Warning: pydub or ffmpeg not installed. Returning raw bytes.")
        return webm_bytes
