from django.conf import settings


def astra_auth_base_url(request):
    """Exposes ASTRA_AUTH_BASE_URL (and AI_GURU_BASE_URL) to all templates:
    the former for the "Back to Astra Auth" sidebar link in
    tutor/templates/tutor/base.html, the latter for the lesson page's
    client-side /simplify-text fallback call in lesson_detail.html.
    AI_GURU_FRONTEND_BASE_URL is the separate React app humans click into
    (AI_GURU_BASE_URL is the backend API, a different host/port)."""
    return {
        'ASTRA_AUTH_BASE_URL': settings.ASTRA_AUTH_BASE_URL,
        'AI_GURU_BASE_URL': settings.AI_GURU_BASE_URL,
        'AI_GURU_FRONTEND_BASE_URL': settings.AI_GURU_FRONTEND_BASE_URL,
    }
