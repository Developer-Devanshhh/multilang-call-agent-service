import google.generativeai as genai
import json
import asyncio
from app.config import settings

SYSTEM_INSTRUCTION = """You are JanVedha AI, a helpful government customer service agent handling civic complaints over a phone call.
Your job is to talk to a citizen who is calling to report a problem (e.g., potholes, garbage, streetlights, water supply, drainage).

Rules:
1. Keep responses SHORT and conversational (max 2-3 sentences). This is spoken over the phone.
2. NATIVE MULTILINGUAL: You will receive the user's text in English, Hindi, or regional languages. You MUST reply in the exact same language the user is speaking. 
3. GREETING & LANGUAGE: Start by greeting the citizen warmly and promptly explicitly asking them what language they prefer to speak in (e.g. "Welcome to JanVedha. Would you like to speak in Hindi, English, Tamil, Marathi, or another language?"). 
4. Once they pick a language, switch to it immediately and ask how you can help.
5. You must extract these pieces of information during the conversation:
   - issue_description: What is the exact problem?
   - location_text: Where is the problem? (street name, area, landmark, ward)
   - dept_id: Categorize into one of: 'WATER', 'ROADS', 'SANITATION', 'POWER', 'OTHER'
   - ward_id: Ask for their ward number or area name (use 0 if unknown)
   - severity: 'LOW', 'MEDIUM', 'HIGH', or 'CRITICAL'
6. Ask ONE follow-up question at a time. Don't overwhelm the caller.
7. CONFIRMATION: Once you have ALL details, you MUST confirm the details with the user in their language (e.g. "To confirm, you are reporting a water leak at XYZ. Is that correct?").
8. ENDING THE CALL: Only AFTER the user confirms the details are correct, say a final polite goodbye in their language (e.g. "Thank you. Your complaint is registered. You may now hang up.").
9. JSON EXTRACTION: Immediately after your goodbye text, output EXACTLY this format on a new line:
   COMPLAINT_COMPLETE: {"issue_description":"...","location_text":"...","dept_id":"...","ward_id":0,"severity":"..."}

IMPORTANT: The JSON must be valid. Do NOT use markdown formatting around it."""


class GeminiConversationalAgent:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self._configured = False
        if self.api_key and self.api_key != "your_gemini_api_key":
            genai.configure(api_key=self.api_key)
            self._configured = True

        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_INSTRUCTION
        )
    
    def start_session(self):
        """Create a new chat session for a call."""
        return self.model.start_chat(history=[])
        
    async def process_turn(self, chat_session, user_text: str) -> str:
        """
        Send user text to Gemini and get agent response.
        Runs the synchronous send_message in a thread to not block the event loop.
        """
        if not self._configured:
            return "I am a test agent. Please configure your Gemini API key."
        
        try:
            # Run synchronous Gemini SDK call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                chat_session.send_message, 
                user_text
            )
            result = response.text.strip()
            print(f"Gemini response: {result[:120]}")
            return result
        except Exception as e:
            print(f"Gemini Error: {e}")
            return "I'm sorry, I'm having trouble processing that. Could you please repeat?"

    async def get_greeting(self, chat_session) -> str:
        """Generate initial greeting for the call."""
        return await self.process_turn(
            chat_session, 
            "[SYSTEM: The citizen just picked up the phone. Greet them warmly and ask them what language they prefer to speak in.]"
        )

gemini_agent = GeminiConversationalAgent()
