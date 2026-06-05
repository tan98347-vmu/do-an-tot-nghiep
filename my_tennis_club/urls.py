"""
Thuoc chuc nang nao: Dinh tuyen URL trung tam cho backend Django trong mo hinh Nginx public + Flutter static.
Vai tro backend: File nay chi giu admin Django, JWT refresh va namespace API; Django khong con serve frontend Flutter hay catch-all route.
Vai tro cua no trong frontend: Frontend Flutter Web duoc Nginx phuc vu tu `flutter_frontend/build/web` va goi same-origin vao `/api/`, con file nay chi nhan cac request da duoc proxy vao app server.
Moi lien he voi nhung ham / source khac: Include `api.urls`, dung `TokenRefreshView`, va duoc `my_tennis_club.wsgi` hoac `my_tennis_club.asgi` nap khi Waitress/ASGI host khoi dong.
Tac dung: Giu boundary ro rang giua frontend public do Nginx phuc vu va backend Django chi chiu trach nhiem API, admin va auth refresh.
"""

from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
