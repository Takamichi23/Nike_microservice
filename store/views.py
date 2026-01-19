from django.shortcuts import render, redirect
from .models import Product, Category, Profile
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm, UpdateUserForm, ChangePasswordForm, UserInfoForm
from payment.forms import ShippingForm
from payment.models import ShippingAddress
from django import forms
from django.db.models import Q
from django.conf import settings
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import json
from cart.cart import Cart

def search(request):
    if request.method == "POST":
        query = request.POST['searched']
        try:
            req = Request(f"{settings.FASTAPI_BASE_URL}/items")
            with urlopen(req, timeout=5) as resp:
                products = json.loads(resp.read().decode())
        except Exception:
            products = []
        def _norm(p):
            img = p.get('image')
            if img and not str(img).startswith(('http://', 'https://', settings.MEDIA_URL)):
                p['image'] = {'url': f"{settings.MEDIA_URL}{img}"}
            elif isinstance(img, str):
                p['image'] = {'url': img}
            return p
        products = [_norm(p) for p in products]
        searched = [p for p in products if query.lower() in (p.get('name','') or '').lower() or query.lower() in (p.get('description','') or '').lower()]
        if not searched:
            messages.success(request, ("That product does not exist, please try again"))
        return render(request, 'search.html', {'searched': searched})
    return render(request, 'search.html', {})


def category_summary(request):
    categories = Category.objects.all()
    return render(request, 'category_summary.html', {"categories": categories})

def category(request, foo):
    foo = foo.replace('-', ' ')
    try:
        category = Category.objects.get(name=foo)
        try:
            req = Request(f"{settings.FASTAPI_BASE_URL}/items")
            with urlopen(req, timeout=5) as resp:
                items = json.loads(resp.read().decode())
        except Exception:
            items = []
        def _norm(p):
            img = p.get('image')
            if img and not str(img).startswith(('http://', 'https://', settings.MEDIA_URL)):
                p['image'] = {'url': f"{settings.MEDIA_URL}{img}"}
            elif isinstance(img, str):
                p['image'] = {'url': img}
            return p
        products = [_norm(p) for p in items if p.get('category_id') == category.id]
        return render(request, 'category.html', {'products': products, 'category': category})
    except:
        messages.success(request, ("That category doesn't exist"))
        return redirect('home')

def product(request, pk):
    try:
        req = Request(f"{settings.FASTAPI_BASE_URL}/items/{pk}")
        with urlopen(req, timeout=5) as resp:
            product = json.loads(resp.read().decode())
    except Exception:
        product = None
    if not product:
        messages.success(request, ("That product doesn't exist"))
        return redirect('home')
    img = product.get('image')
    if img and not str(img).startswith(('http://', 'https://', settings.MEDIA_URL)):
        product['image'] = {'url': f"{settings.MEDIA_URL}{img}"}
    elif isinstance(img, str):
        product['image'] = {'url': img}
    return render(request, 'product.html', {'product': product})


def home(request):
    try:
        req = Request(f"{settings.FASTAPI_BASE_URL}/items")
        with urlopen(req, timeout=5) as resp:
            products = json.loads(resp.read().decode())
    except Exception:
        products = []
    def _norm(p):
        img = p.get('image')
        if img and not str(img).startswith(('http://', 'https://', settings.MEDIA_URL)):
            p['image'] = {'url': f"{settings.MEDIA_URL}{img}"}
        elif isinstance(img, str):
            p['image'] = {'url': img}
        return p
    products = [_norm(p) for p in products]
    return render(request, 'home.html', {'products': products})

def about(request):
    return render(request, 'about.html', {})

def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            current_user = Profile.objects.get(user__id=request.user.id)
            saved_cart = current_user.old_cart
            if saved_cart:
                converted_cart = json.loads(saved_cart)
                cart = Cart(request)
                for key,value in converted_cart.items():
                    cart.db_add(product=key, quantity=value)

            messages.success(request, ("You have been logged in"))
            return redirect('home')
        else:
            messages.success(request, ("There was an error, Please try again"))
            return redirect('login')
    else:
        return render(request, 'login.html', {})

def logout_user(request):
    logout(request)
    messages.success(request, ("You have been logged out"))
    return redirect('home')

def register_user(request):
    form = SignUpForm()
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            #login user
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, ("You have registered successfully, Please Fill out your user information below"))
            return redirect('update_info')
        else:
            messages.success(request, ("There was an problem in Registration, Please try again"))
            return redirect('register')
    else:
        return render(request, 'register.html', {'form':form})
    
def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        user_form = UpdateUserForm(request.POST or None, instance=current_user)

        if user_form.is_valid():
            user_form.save()

            login(request, current_user)
            messages.success(request, "User has been updated")
            return redirect('home')
        return render(request, "update_user.html", {'user_form':user_form})
    else:
        messages.success(request, "You must be logged in first to access this page")
        return redirect('home')
    
def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been updated")
                login(request, current_user)
                return redirect('update_user')
            else:
                for error in list(form.errors.values()):
                    messages.error(request, error)
                    return redirect('update_password')
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "update_password.html", {'form':form})
    else:
        messages.success(request, "You must be logged in to view the page")
        return redirect('home')
    
def update_info(request):
    if request.user.is_authenticated:
        current_user = Profile.objects.get(user__id=request.user.id)
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        form = UserInfoForm(request.POST or None, instance=current_user)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)

        if form.is_valid() or shipping_form.is_valid():
            form.save()
            shipping_form.save()

            messages.success(request, "Your info has been updated")
            return redirect('home')
        return render(request, "update_info.html", {'form':form, 'shipping_form':shipping_form})
    else:
        messages.success(request, "You must be logged in first to access this page")
        return redirect('home')