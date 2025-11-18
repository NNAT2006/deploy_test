from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from accounts.admin_site import admin_site

urlpatterns = [
    path('', include('accounts.urls')),  # 👈 thêm dòng này để / trỏ vào trang home
    path('admin/', admin_site.urls),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('social-auth/', include('social_django.urls', namespace='social')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
