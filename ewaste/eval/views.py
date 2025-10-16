from django.shortcuts import render, redirect, get_object_or_404
from django.db import IntegrityError
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse
from events.models import userFull, product, cart, PRODUCT_CATEGORIES, userCredits, evaluatorGuy, evaluatorJob
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse


# Create your views here.
def eval_home(request,pk):
     return render(request, 'eval/home.html')

def eval_loginForm(request):
     if request.method == "POST":
          email = request.POST.get("email")
          password = request.POST.get("password")

          try:
               user = User.objects.get(email=email)
               eval_user = evaluatorGuy.objects.get(evaluatorGuy_user_id=user)
               print("eval user exist and the id:", eval_user)
          except User.DoesNotExist:
               return render(
                    request, "eval/login.html", {"incorrect": "Email not registered"}
               )

          authenticated_user = authenticate(username=user.username, password=password)

          if authenticated_user:
               if user.is_active and not user.is_staff and not user.is_superuser:
                    login(request, authenticated_user)
                    return redirect("eval_home", pk=user.id)
               else:
                    return render(
                         request,
                         "eval/login.html",
                         {"incorrect": "User not active or unauthorized"},
                    )
          else:
               return render(
                    request, "eval/login.html", {"incorrect": "Incorrect credentials"}
               )

     return render(request, "eval/login.html")

def eval_signup(request):
     if request.method == "POST":
          first_name = request.POST.get("first_name")
          last_name = request.POST.get("last_name")
          username = request.POST.get("username")
          email = request.POST.get("email")
          phone = request.POST.get("phone")
          password = request.POST.get("password")

          try:
               if not User.objects.filter(email=email).exists():
                    user = User.objects.create_user(
                         username=username,
                         email=email,
                         password=password,
                         is_active=True,  # Account inactive until verified
                         first_name=first_name,
                         last_name=last_name,
                    )
                    user.save()

                    # Save additional Customer Care data
                    care_data = evaluatorGuy.objects.create(
                         evaluatorGuy_phoneNumber=phone,
                         evaluatorGuy_user=user,
                    )
                    care_data.save()
                    # Redirect to login page with success message
                    return redirect('eval_loginForm')
               else:
                    # If email exists, return error message
                    message1 = "A user with this email already exists."
                    return render(request, "eval/signup.html", {"message1": message1})

          except IntegrityError:
               # Handle database-related errors
               message1 = "There was an error processing your request. Please try again."
               return render(request, "eval/signup.html", {"message1": message1})

     # Render the signup form if not a POST request
     return render(request, "eval/signup.html")

def eval_logout(request):
     logout(request)
     return redirect("eval_loginForm")


def more_jobs(request, pk):
     has_job = evaluatorGuy.objects.filter(currently_working=1, evaluatorGuy_user_id=pk).exists()
     products = product.objects.filter(product_evaluation_status=0)
     return render(request, "eval/more_jobs.html", {"products": products, "has_job": has_job})

def select_eval_product(request, pk, prod):
     evaluator = evaluatorGuy.objects.filter(currently_working=0, evaluatorGuy_user_id=pk).first()
     if evaluator:
          current_product = get_object_or_404(product, product_id=prod)
          evaluator.current_product = current_product
          evaluator.currently_working = 1
          evaluator.save()
          evaluatorJob.objects.create(evaluatorJob_product=current_product, evaluatorGuy=evaluator)
     return redirect('current_job', pk=pk)

def complete_eval_product(request, pk, prod):
     evaluator = evaluatorGuy.objects.filter(currently_working=1, evaluatorGuy_user_id=pk).first()
     if request.method == "POST":
          score = request.POST.get("score")
          if evaluator:
               current_product = get_object_or_404(product, product_id=prod)
               current_product.product_evaluation_score = score
               current_product.product_evaluation_status = 1
               current_product.save()
               evaluator.current_product = None
               evaluator.currently_working = 0
               evaluator.save()
               evaluatorJob.objects.filter(evaluatorJob_product=current_product, evaluatorGuy=pk).update(evaluation_date=timezone.now())

     return redirect('more_jobs', pk=pk)

def current_job(request, pk):
     # Check if evaluator is working on a product
     evaluator = evaluatorGuy.objects.filter(currently_working=1, evaluatorGuy_user_id=pk).first()
     current_product = evaluator.current_product if evaluator else None

     return render(request, "eval/job.html", {"product": current_product, "has_job": bool(current_product)})

def evaluation_history(request, pk):
     history = evaluatorJob.objects.filter(evaluatorGuy__evaluatorGuy_user_id=pk).order_by('-evaluation_date')
     return render(request, "eval/history.html", {"history": history})


def evaluator_profile(request, pk):
    evaluator = get_object_or_404(evaluatorGuy, pk=pk)
    return render(request, "evaluator/more_jobs.html", {"phone_number": evaluator.evaluator_phoneNumber})

@login_required
def evaluator_update_password(request):
    if request.method == "POST":
        old_password = request.POST["old_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]

        if new_password != confirm_password:
            messages.error(request, "New password and confirmation password do not match!")
            return redirect("evaluator_update_password")

        user = request.user
        if not user.check_password(old_password):
            messages.error(request, "Old password is incorrect!")
            return redirect("evaluator_update_password")

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Password updated successfully!")
        return redirect("dashboard")  # Change to an appropriate redirect

    return render(request, "evaluator/update_password.html")

@login_required
def evaluator_update_phone(request):
    if request.method == "POST":
        new_phone = request.POST["new_phone"]
        user = request.user
        user.profile.phone_number = new_phone  # Assuming phone_number is stored in a Profile model
        user.profile.save()
        messages.success(request, "Phone number updated successfully!")
        return redirect("dashboard")

    return render(request, "evaluator/update_phone.html")
