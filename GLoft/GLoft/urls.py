from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('api.urls'))
    
]
