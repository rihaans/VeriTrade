from django.shortcuts import render
from .models import product

def index(request):
    categories = product.objects.values_list('product_category', flat=True).distinct()
    categorized_products = {category: product.objects.filter(product_category=category, product_evaluation_status=True) for category in categories}

    return render(request,'index_new.html', {'categorized_products': categorized_products})

def login(request):
    return render(request,'base/login_new.html')

def signup(request):
    return render(request,'base/signup_new.html')

def home(request):
    return render(request, 'home.html')


