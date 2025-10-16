from django.contrib import admin
from django.urls import include, path
from django.conf import settings 
from django.conf.urls.static import static 
from base import views 

urlpatterns = [
    path('',include('events.urls')),
    path('base/',include('base.urls')),
    path('eval/',include('eval.urls')),
    path('dlv/',include('delivery.urls')),
    path('admin/',admin.site.urls),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.logout_view, name='logout'),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)