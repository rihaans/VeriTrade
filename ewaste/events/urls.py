from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='Index'),
    path('login/', views.login, name='Login'),
    path('signup/', views.signup, name='Signup'),
    path('home/', views.home, name='Home'),


]

