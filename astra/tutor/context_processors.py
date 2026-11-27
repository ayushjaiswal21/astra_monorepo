from django.conf import settings


def astra_auth_base_url(request):
    """Exposes ASTRA_AUTH_BASE_URL to all templates for the "Back to Astra
    Auth" sidebar link in tutor/templates/tutor/base.html."""
    return {'ASTRA_AUTH_BASE_URL': settings.ASTRA_AUTH_BASE_URL}
