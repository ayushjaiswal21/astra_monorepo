import google.generativeai as genai
import sys
import os
import requests # Import requests for mocking
import json # Import json for handling mock responses

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import utils

text_model = genai.GenerativeModel('gemini-pro')
vision_model = genai.GenerativeModel('gemini-pro-vision')

def generate_text_response(text, recent_context, learned_prefs, detected_lang, language_name, should_display):
    gemini_api_base_url = os.getenv('GEMINI_API_BASE_URL')
    if gemini_api_base_url:
        # Use mock server
        try:
            mock_response = requests.post(gemini_api_base_url, json={"message": text})
            mock_response.raise_for_status()
            return mock_response.json().get("response", "mocked AI reply")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to mock Gemini API: {e}. Falling back to default mock response.")
            return "mocked AI reply"
    
    system_prompt = _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display)
    full_prompt = system_prompt + text.strip()
    response = text_model.generate_content(full_prompt)
    return response.text if response.text else "Sorry, I couldn't generate a response."

def generate_image_response(pil_image, text, detected_lang, language_name, should_display):
    gemini_api_base_url = os.getenv('GEMINI_API_BASE_URL')
    if gemini_api_base_url:
        # Use mock server
        try:
            # For image, we might just return a generic mock response
            mock_response = requests.post(gemini_api_base_url, json={"message": text, "image_present": True})
            mock_response.raise_for_status()
            return mock_response.json().get("response", "mocked image reply")
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to mock Gemini API for image: {e}. Falling back to default mock response.")
            return "mocked image reply"

    vision_system_prompt = _build_vision_system_prompt(text, detected_lang, language_name, should_display)
    response = vision_model.generate_content([vision_system_prompt, pil_image])
    return response.text

def _build_system_prompt(text, recent_context, learned_prefs, detected_lang, language_name, should_display):
    learned_format_pref = learned_prefs.get('preferred_format', 'neutral')
    learned_formality = learned_prefs.get('formality_level', 'neutral')
    learned_topics = learned_prefs.get('topics_of_interest', [])
    
    if should_display and detected_lang != 'en':
        return f"""You are an AI assistant specializing in career guidance and learning. Your primary goal is to provide helpful, accurate, and encouraging advice to users seeking to advance their careers or learn new skills.
        
        Current user input language: {language_name} ({detected_lang}). Respond in {language_name}.
        
        User's recent conversation context:
        {recent_context}
        
        User's preferred response format: {learned_format_pref}
        User's preferred formality level: {learned_formality}
        User's topics of interest: {', '.join(learned_topics) if learned_topics else 'general'}
        
        Based on the above context and preferences, provide a comprehensive and personalized response to the user's query.
        """
    else:
        mixed_lang = utils.detect_mixed_indian_language(text)
        if mixed_lang:
            return f"""You are an AI assistant specializing in career guidance and learning. Your primary goal is to provide helpful, accurate, and encouraging advice to users seeking to advance their careers or learn new skills.
            
            Detected mixed language input (e.g., Hinglish): {mixed_lang}. Respond in a similar mixed language style if appropriate, or default to English.
            
            User's recent conversation context:
            {recent_context}
            
            User's preferred response format: {learned_format_pref}
            User's preferred formality level: {learned_formality}
            User's topics of interest: {', '.join(learned_topics) if learned_topics else 'general'}
            
            Based on the above context and preferences, provide a comprehensive and personalized response to the user's query.
            """
        else:
            return f"""You are an AI assistant specializing in career guidance and learning. Your primary goal is to provide helpful, accurate, and encouraging advice to users seeking to advance their careers or learn new skills.
            
            User's recent conversation context:
            {recent_context}
            
            User's preferred response format: {learned_format_pref}
            User's preferred formality level: {learned_formality}
            User's topics of interest: {', '.join(learned_topics) if learned_topics else 'general'}
            
            Based on the above context and preferences, provide a comprehensive and personalized response to the user's query.
            """

def _build_vision_system_prompt(text, detected_lang, language_name, should_display):
    if should_display and detected_lang != 'en':
        return f"""You are an AI assistant specializing in analyzing images and providing career guidance and learning advice based on them.
        
        Current user input language: {language_name} ({detected_lang}). Respond in {language_name}.
        
        Analyze the image and the user's question: "{text}". Provide a helpful and accurate response.
        """
    else:
        mixed_lang = utils.detect_mixed_indian_language(text)
        if mixed_lang:
            return f"""You are an AI assistant specializing in analyzing images and providing career guidance and learning advice based on them.
            
            Detected mixed language input (e.g., Hinglish): {mixed_lang}. Respond in a similar mixed language style if appropriate, or default to English.
            
            Analyze the image and the user's question: "{text}". Provide a helpful and accurate response.
            """
        else:
            return f"""You are an AI assistant specializing in analyzing images and providing career guidance and learning advice based on them.
            
            Analyze the image and the user's question: "{text}". Provide a helpful and accurate response.
            """
