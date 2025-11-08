"""List available Gemini models"""
import google.generativeai as genai
import config

genai.configure(api_key=config.GEMINI_API_KEY)

print("📋 Listing available Gemini models:\n")
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"✅ {model.name}")
        print(f"   Description: {model.description[:100]}...")
        print()
