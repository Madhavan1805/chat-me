"""
WSGI entry point for platforms that expect gunicorn app:app.
Use this when the start command is gunicorn app:app (e.g. from project root).
Run gunicorn from the mysocial folder: cd mysocial && gunicorn app:app
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysocial.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
