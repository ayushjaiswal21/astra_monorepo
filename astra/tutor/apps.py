from django.apps import AppConfig


class TutorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tutor'
    
    def ready(self):
        import tutor.signals
        from django.conf import settings
        import google.generativeai as genai

        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
