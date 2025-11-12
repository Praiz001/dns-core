"""
ASGI config for user_service project.
"""
import os
from django.core.asgi import get_asgi_application

# Force set to avoid conflicts with other projects
os.environ['DJANGO_SETTINGS_MODULE'] = 'user_service.settings'
application = get_asgi_application()
