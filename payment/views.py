from django.shortcuts import render, redirect
from cart.cart import Cart
from payment.forms import ShippingForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from store.models import Product, Profile
import datetime
from django.conf import settings
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def orders(request, pk):
    if request.user.is_authenticated and request.user.is_superuser:
        order = Order.objects.get(id=pk)
        items = OrderItem.objects.filter(order=pk)

        if request.POST:
            status = request.POST['shipping_status']
            if status == "true":
                order = Order.objects.filter(id=pk)
                now = datetime.datetime.now()
                order.update(shipped=True, date_shipped=now)
            else:
                order = Order.objects.filter(id=pk)
                order.update(shipped=False)
            messages.success(request, "Shipping Status Updated")
            return redirect('home')

        return render(request, 'payment/orders.html', {"order":order, "items":items})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def shipped_dash(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)

        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            now = datetime.datetime.now()
            order.update(shipped=False, date_shipped=now)
            messages.success(request, "Shipping Status Updated")
            return redirect('home')
        
        return render(request, 'payment/shipped_dash.html', {"orders":orders})
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def not_shipped_dash(request):
     if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=False)

        if request.POST:
            status = request.POST['shipping_status']
            num = request.POST['num']
            order = Order.objects.filter(id=num)
            now = datetime.datetime.now()
            order.update(shipped=True, date_shipped=now)
            messages.success(request, "Shipping Status Updated")
            return redirect('home')
        
        return render(request, 'payment/not_shipped_dash.html', {"orders":orders})
     else:
        messages.success(request, "Access Denied")
        return redirect('home')

def process_order(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()
        payment_form = PaymentForm(request.POST or None)
        my_shipping = request.session.get('my_shipping') 
        full_name = my_shipping['shipping_full_name']
        email = my_shipping['shipping_email']
        shipping_address = f"{my_shipping['shipping_address1']}\n{my_shipping['shipping_address2']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zipcode']}\n{my_shipping['shipping_country']}"
        amount_paid = totals
        # Build payload for FastAPI
        items_payload = []
        for product in cart_products():
            product_id = product.id
            price = product.sale_price if getattr(product, 'is_sale', False) else product.price
            for key, value in quantities().items():
                if int(key) == product.id:
                    items_payload.append({
                        "product_id": product_id,
                        "quantity": int(value),
                        "price": str(price),
                    })

        payload = {
            "user_id": request.user.id if request.user.is_authenticated else None,
            "full_name": full_name,
            "email": email,
            "shipping_address": shipping_address,
            "amount_paid": str(amount_paid),
            "items": items_payload,
        }

        try:
            req = Request(f"{settings.FASTAPI_BASE_URL}/orders", data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=10) as resp:
                _ = json.loads(resp.read().decode())
        except Exception:
            messages.error(request, "Failed to place order. Please try again.")
            return redirect('checkout')

        # Clear session cart
        for key in list(request.session.keys()):
            if key == "session_key":
                del request.session[key]

        if request.user.is_authenticated:
            current_user = Profile.objects.filter(user__id=request.user.id)
            current_user.update(old_cart="")

        messages.success(request, "Order Placed")
        return redirect('home')
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def billing_info(request):
    if request.POST:
        cart = Cart(request)
        cart_products = cart.get_prods
        quantities = cart.get_quants
        totals = cart.cart_total()

        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping

        if request.user.is_authenticated:
            billing_form = PaymentForm()
            return render(request, 'payment/billing_info.html', {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_info':request.POST, 'billing_form':billing_form })
        else:
            billing_form = PaymentForm()
            return render(request, 'payment/billing_info.html', {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_info':request.POST, 'billing_form':billing_form })
    else:
        messages.success(request, "Access Denied")
        return redirect('home')

def payment_success(request):
    return render(request, "payment/payment_success.html", {})

def checkout(request):
    cart = Cart(request)
    cart_products = cart.get_prods
    quantities = cart.get_quants
    totals = cart.cart_total()

    if request.user.is_authenticated:
        shipping_user = ShippingAddress.objects.get(user__id=request.user.id)
        shipping_form = ShippingForm(request.POST or None, instance=shipping_user)
        return render(request, 'payment/checkout.html', {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_form':shipping_form})
    else:
        shipping_form = ShippingForm(request.POST or None)
        return render(request, 'payment/checkout.html', {'cart_products':cart_products, 'quantities':quantities, 'totals':totals, 'shipping_form':shipping_form})
