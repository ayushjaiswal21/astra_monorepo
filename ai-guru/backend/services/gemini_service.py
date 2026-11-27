import google.generativeai as genai
import sys
import os
import asyncio
import httpx # Async HTTP client; used instead of requests so mock calls don't block the event loop
import json # Import json for handling mock responses

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils
import config
from tracing import trace_llm_call

# Initialize models only if not in mock mode and API key is available
text_model = None
vision_model = None
if not config.USE_MOCK and config.GEMINI_API_KEY:
    genai.configure(api_key=config.GEMINI_API_KEY)
    text_model = genai.GenerativeModel('gemini-pro')
    vision_model = genai.GenerativeModel('gemini-pro-vision')

@trace_llm_call(call_type="chat")
async def generate_text_response(text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context=""):
    gemini_api_base_url = os.getenv('GEMINI_API_BASE_URL')
    if gemini_api_base_url or config.USE_MOCK or text_model is None:
        # Use mock server
        try:
            if gemini_api_base_url:
                async with httpx.AsyncClient() as client:
                    mock_response = await client.post(gemini_api_base_url, json={"message": text})
                    mock_response.raise_for_status()
                    return mock_response.json().get("response", "mocked AI reply")
            # No mock server provided; return static mock
            return "mocked AI reply"
        except httpx.HTTPError as e:
            print(f"Error connecting to mock Gemini API: {e}. Falling back to default mock response.")
            return "mocked AI reply"
    else:
        system_prompt = _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context)
        full_prompt = system_prompt + text.strip()
        response = text_model.generate_content(full_prompt)
        return response.text if response.text else "Sorry, I couldn't generate a response."

# Chunk size/delay for simulated typing (mock mode, or splitting any already-
# complete text). Not used for real Gemini streaming - that yields the SDK's
# own chunks as they arrive.
_SIM_CHUNK_WORDS = 4
_SIM_CHUNK_DELAY_S = 0.05


async def generate_text_response_stream(text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context=""):
    """Async generator yielding text chunks for /chat/stream.

    Real Gemini streaming (verified against the installed google-generativeai
    0.3.0: GenerativeModel.generate_content(..., stream=True) is supported and
    returns an iterable of chunks) is used whenever a real model is configured.
    In mock mode (no API key / USE_MOCK / local mock server), there's no
    token-by-token generation to stream, so the complete mock reply is instead
    chunked word-by-word with a tiny delay to produce the same visible typing
    effect client-side.
    """
    gemini_api_base_url = os.getenv('GEMINI_API_BASE_URL')
    if gemini_api_base_url or config.USE_MOCK or text_model is None:
        full_text = await generate_text_response(
            text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context
        )
        words = full_text.split(' ')
        for i in range(0, len(words), _SIM_CHUNK_WORDS):
            chunk = ' '.join(words[i:i + _SIM_CHUNK_WORDS])
            if i + _SIM_CHUNK_WORDS < len(words):
                chunk += ' '
            yield chunk
            await asyncio.sleep(_SIM_CHUNK_DELAY_S)
    else:
        system_prompt = _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context)
        full_prompt = system_prompt + text.strip()
        response = text_model.generate_content(full_prompt, stream=True)
        got_any = False
        for chunk in response:
            if chunk.text:
                got_any = True
                yield chunk.text
            await asyncio.sleep(0)  # yield control back to the event loop between chunks
        if not got_any:
            yield "Sorry, I couldn't generate a response."


@trace_llm_call(call_type="vision")
async def generate_image_response(pil_image, text, detected_lang, language_name, should_display):
    gemini_api_base_url = os.getenv('GEMINI_API_BASE_URL')
    if gemini_api_base_url or config.USE_MOCK or vision_model is None:
        # Use mock server
        try:
            # For image, we might just return a generic mock response
            if gemini_api_base_url:
                async with httpx.AsyncClient() as client:
                    mock_response = await client.post(gemini_api_base_url, json={"message": text, "image_present": True})
                    mock_response.raise_for_status()
                    return mock_response.json().get("response", "mocked image reply")
            return "mocked image reply"
        except httpx.HTTPError as e:
            print(f"Error connecting to mock Gemini API for image: {e}. Falling back to default mock response.")
            return "mocked image reply"
    else:
        vision_system_prompt = _build_vision_system_prompt(text, detected_lang, language_name, should_display)
        response = vision_model.generate_content([vision_system_prompt, pil_image])
        return response.text

# What each learned-preference value actually means to the model, instead
# of passing the raw stored string (e.g. "concise") unexplained and hoping
# Gemini infers the right behavior from the word alone.
_FORMAT_INSTRUCTIONS = {
    'concise': 'Keep responses short and to the point - a few sentences, no filler.',
    'detailed': 'Give thorough, in-depth responses that fully explore the topic.',
    'bullet_points': 'Structure the response as scannable bullet points where possible.',
    'paragraph': 'Write in flowing prose paragraphs rather than lists.',
    'neutral': 'Use whatever length and structure best fits the question.',
}
_FORMALITY_INSTRUCTIONS = {
    'formal': 'Use professional, formal language - no slang or casual phrasing.',
    'casual': 'Use a warm, casual, conversational tone, like talking to a friend.',
    'neutral': 'Use a friendly but professional tone.',
}


def _language_instruction(text, detected_lang, language_name, should_display):
    """Single source of truth for the language-handling instruction, so the
    three near-duplicate branches that used to each hardcode this don't
    drift out of sync. Mixed-language (e.g. Hinglish) detection still takes
    priority exactly as before; only the surrounding prompt text is shared."""
    if should_display and detected_lang != 'en':
        return f"Current user input language: {language_name} ({detected_lang}). Respond in {language_name}."
    mixed_lang = utils.detect_mixed_indian_language(text)
    if mixed_lang:
        return (f"Detected mixed language input (e.g., Hinglish): {mixed_lang}. "
                "Respond in a similar mixed language style if appropriate, or default to English.")
    return "Respond in English unless the user's message itself suggests otherwise."


def _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display, rag_context=""):
    learned_format_pref = learned_prefs.get('preferred_format', 'neutral')
    learned_formality = learned_prefs.get('formality_level', 'neutral')
    learned_topics = learned_prefs.get('topics_of_interest', [])

    format_instruction = _FORMAT_INSTRUCTIONS.get(learned_format_pref, _FORMAT_INSTRUCTIONS['neutral'])
    formality_instruction = _FORMALITY_INSTRUCTIONS.get(learned_formality, _FORMALITY_INSTRUCTIONS['neutral'])
    language_instruction = _language_instruction(text, detected_lang, language_name, should_display)

    rag_block = ""
    if rag_context:
        rag_block = f"""
RETRIEVED CONTEXT (from previously indexed documents):
{rag_context}

Use the retrieved context above to ground factual claims when it's relevant to the question.
If it doesn't cover what's being asked, say you're answering from general knowledge instead
of forcing the retrieved context to fit.
"""

    return f"""You are an AI assistant specializing in career guidance and learning. Your primary goal is to provide helpful, accurate, and encouraging advice to users seeking to advance their careers or learn new skills.

Do not invent specific facts you were not given - no made-up company names, salary figures, course titles, certification names, or statistics. If you don't have a specific fact, speak in general terms or say you're not certain, rather than fabricating a precise-sounding detail.

{language_instruction}

User's recent conversation context:
{recent_context}

Response format preference: {format_instruction}
Tone/formality preference: {formality_instruction}
User's topics of interest: {', '.join(learned_topics) if learned_topics else 'general'}
{rag_block}
Based on the above context and preferences, provide a comprehensive and personalized response to the user's query.
"""

def _build_vision_system_prompt(text, detected_lang, language_name, should_display):
    language_instruction = _language_instruction(text, detected_lang, language_name, should_display)
    return f"""You are an AI assistant specializing in analyzing images and providing career guidance and learning advice based on them.

{language_instruction}

Do not invent specific facts about what's in the image beyond what you can actually observe.

Analyze the image and the user's question: "{text}". Provide a helpful and accurate response.
"""
