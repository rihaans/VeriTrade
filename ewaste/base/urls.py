from django.urls import path
from . import views

from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', views.home, name='home'),
    path('loginForm', views.loginForm, name='loginForm'),
    path('signupForm', views.signupForm, name='signupForm'),
    path('logout/', views.logout_view, name='logout'),
    
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),

    path('home/<int:pk>', views.home, name='home'),
    path('sell/<int:pk>', views.sell, name='sell'),
    path('product/<int:pk>/<int:pk2>/', views.product_detail, name='product_detail'),
    path('add_to_cart/<int:pk>/<int:pk2>/', views.add_to_cart, name='add_to_cart'),
    path('delete_cart_item/<int:pk>/<int:item_id>/', views.delete_cart_item, name='delete_cart_item'),
    path('direct_buy/<int:pk>/<int:item_id>/', views.direct_buy, name='direct_buy'),
    path('cart_to_buy/<int:pk>/', views.cart_to_buy, name='cart_to_buy'),

    path('profile/<int:pk>/', views.profile, name='profile'),
    path('change_address/', views.change_address, name='change_address'),
    path('change_password/', views.change_password, name='change_password'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('base/edit-profile/', views.edit_profile, name='edit_profile'),

    path('base/buy_credits/<int:pk>/', views.buy_credits, name='buy_credits'),



]