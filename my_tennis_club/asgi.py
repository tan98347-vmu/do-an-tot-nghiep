"""
Thuoc chuc nang nao: Ha tang khoi dong backend va diem vao cho moi truong ASGI.
Vai tro backend: File nay tao ASGI application de server async dua request vao dung bo cau hinh Django, tu do cac app `accounts`, `api`, `documents`, `signing`, `ai_engine` va `document_templates` moi duoc kich hoat.
Vai tro cua no trong frontend: Frontend Flutter Web van duoc Nginx phuc vu o tang public; doi tuong ASGI nay chi xu ly request backend duoc proxy vao app server neu he thong chay bang uvicorn, daphne hoac ASGI host tuong tu.
Moi lien he voi nhung ham / source khac: Doc bien `DJANGO_SETTINGS_MODULE` tro vao `my_tennis_club.settings`, sau do nap route tu `my_tennis_club.urls`; cac route nay dan den `api/urls.py`, `rest_framework_simplejwt` va admin Django.
Tac dung: Bao dam request backend di qua dung lop cau hinh va middleware truoc khi toi cac view va service nghiep vu.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_tennis_club.settings')

application = get_asgi_application()
