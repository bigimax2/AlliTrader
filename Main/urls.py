from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from trader.views import webhook_deploy


urlpatterns = [
        path('admin/', admin.site.urls),
        path('sso/', include('esi.urls', namespace='esi')),
        path('', include('authenticated.urls', namespace='authenticated')),
        path('', include('groupmanagement.urls', namespace='groupmanagement')),
        path('', include('trader.urls', namespace='trader')),
        path('webhooc_deploy/', webhook_deploy, name='webhook_deploy'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
