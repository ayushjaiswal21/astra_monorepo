import google.generativeai as genai
import utils

text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

def generate_text_response(text, recent_context, learned_prefs, detected_lang, language_name, should_display):
    system_prompt = _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display)
    full_prompt = system_prompt + text.strip()
    response = text_model.generate_content(full_prompt)
    return response.text if response.text else "Sorry, I couldn't generate a response."

def generate_image_response(pil_image, text, detected_lang, language_name, should_display):
    vision_system_prompt = _build_vision_system_prompt(text, detected_lang, language_name, should_display)
    response = vision_model.generate_content([vision_system_prompt, pil_image])
    return response.text

def _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display):
    learned_format_pref = learned_prefs.get('preferred_format', 'neutral')
    learned_formality = learned_prefs.get('formality_level', 'neutral')
    learned_topics = learned_prefs.get('topics_of_interest', [])
    
    if should_display and detected_lang != 'en':
        return f"""... (rest of the large prompt f-string) ..."""
    else:
        mixed_lang = utils.detect_mixed_indian_language(text)
        return f"""... (rest of the large prompt f-string) ..."""

def _build_vision_system_prompt(text, detected_lang, language_name, should_display):
    if should_display and detected_lang != 'en':
        return f"""... (rest of the large prompt f-string) ..."""
    else:
        mixed_lang = utils.detect_mixed_indian_language(text)
        return f"""... (rest of the large prompt f-string) ...""" 
