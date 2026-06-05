"""
Thuoc chuc nang nao: Ha tang khoi dong backend cho moi truong WSGI sau reverse proxy.
Vai tro backend: File nay tao WSGI application de Waitress hoac WSGI host khac dua request vao dung cau hinh Django.
Vai tro cua no trong frontend: Frontend Flutter Web duoc Nginx phuc vu o tang public; doi tuong WSGI nay chi xu ly request backend duoc proxy vao `/api/**`, `/api/auth/refresh/` va `/django-admin/**`.
Moi lien he voi nhung ham / source khac: Doc cau hinh tu `my_tennis_club.settings`, nap `my_tennis_club.urls`, roi noi tiep den `api/urls.py`, `TokenRefreshView` va admin Django.
Tac dung: Giu cho Django van hanh nhu application server private trong mo hinh Nginx public + Waitress.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_tennis_club.settings')

application = get_wsgi_application()
