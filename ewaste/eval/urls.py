from django.urls import path
from . import views

from django.contrib.auth import views as auth_views


urlpatterns = [
    path('home/<int:pk>', views.eval_home, name='eval_home'),
    path('more_jobs/<int:pk>', views.more_jobs, name='more_jobs'),
    path('current_job/<int:pk>', views.current_job, name='current_job'),
    path('select_product/<int:pk>,<int:prod>', views.select_eval_product, name='select_eval_product'),
    path('complete_eval/<int:pk>,<int:prod>', views.complete_eval_product, name='complete_eval_product'),
    path('history/<int:pk>', views.evaluation_history, name='evaluation_history'),
    path('login', views.eval_loginForm, name='eval_loginForm'),
    path('signup', views.eval_signup, name='eval_signup'),
    path('logout', views.eval_logout, name='eval_logout'),

    path('evaluator_profile/<int:pk>/', views.evaluator_profile, name='evaluator_profile'),
    path('evaluator_update_password/', views.evaluator_update_password, name='evaluator_update_password'),
    path('evaluator_update_phone/', views.evaluator_update_phone, name='evaluator_update_phone'),


]