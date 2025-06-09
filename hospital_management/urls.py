"""
URL configuration for hospital_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path,include
from hms.admin import admin_site
from hms import views as hms_views

urlpatterns = [
    path("admin/", admin_site.urls),
    path('', include('hms.urls')),
    path('dashboard/', hms_views.dashboard, name='dashboard'),
    path('doctor/dashboard/', hms_views.doctor_dashboard, name='doctor_dashboard'),
    path('nurse/dashboard/', hms_views.nurse_dashboard, name='nurse_dashboard'),
    path('redirect/', hms_views.redirect_after_login, name='redirect_after_login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    