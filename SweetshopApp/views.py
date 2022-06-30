from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render, redirect
from django import views
from django.http import HttpResponseRedirect
from django.contrib.auth import login, authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.utils.http import urlsafe_base64_decode

from datetime import date, datetime, timedelta

from .models import Product, CartProduct, Customer, Category

from .forms import LoginForm, RegistrationForm, OrderForm

from .mixins import CartMixin

from .utils import send_email_verify
from utils import recalc_cart


User=get_user_model()

class BaseView(CartMixin, views.View): #рендеринг главной страницы

    def get(self, request, *args, **kwargs):
        products = Product.objects.all()
        categories = Category.objects.all()
        context = {
            'cart': self.cart,
            'categories': categories,
            'products': products,
        }
        return render(request, 'base.html', context)



class CategoryView(CartMixin, views.View):

    def get(self,request, *args, **kwargs):
        cat_selected = self.kwargs['cat_slug']
        categories = Category.objects.all()
        products = Product.objects.filter(category__slug=cat_selected)
        context = {
            'cart': self.cart,
            'categories': categories,
            'products': products,
            'cat_selected': Category.objects.get(slug=cat_selected)
        }
        return render(request, 'base.html', context)


class ProductDetailView(CartMixin, views.generic.DetailView):

    model = Product
    template_name = 'product/product_detail.html'
    slug_url_kwarg = 'product_slug'


class LoginView(views.View):

    def get(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        context = {
            'form': form
        }
        return render(request, 'login.html', context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                customer = Customer.objects.get(user=user)
                if not customer.is_active:
                    message = 'Подтвердите вашу учетную запись!'
                    messages.add_message(request, messages.INFO, message)
                    return HttpResponseRedirect('/')
                login(request, user)
                return HttpResponseRedirect('/')
        context = {
            'form': form
        }
        return render(request, 'login.html', context)


class RegistrationView(views.View):

    def get(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST or None)
        context = {
            'form': form
        }
        return render(request, 'registration.html', context)

    def post(self, request, *args, **kwargs):
        form = RegistrationForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = form.cleaned_data['username']
            new_user.email = form.cleaned_data['email']
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.save()
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            Customer.objects.create(
                user=new_user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
            send_email_verify(request, user)
            return redirect('confirm_email')
        context = {
            'form': form
        }
        return render(request, 'registration.html', context)

class EmailVerifyView(views.View):

    def get(self, request, uidb64, token):
        user = self.get_user(uidb64)
        if user is not None and token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            customer = Customer.objects.get(user=user)
            customer.is_active = True
            customer.save()
            login(request, user)
            message = 'Вы успешно зарегистрированы!'
            messages.add_message(request, messages.INFO, message)
            return HttpResponseRedirect('/')
        return redirect('invalid_verify')

    @staticmethod
    def get_user(uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError,
                User.DoesNotExist, ValidationError):
            user = None
        return user

class InvalidVerify(views.View):

    def get(self, request):
        return render(request, 'invalid_verify.html')

class ConfirmView(views.View):

    def get(self, request):
        return render(request, 'confirm_email.html')

class AccountView(CartMixin, views.View):

    def get(self, request, *args, **kwargs):
        customer = Customer.objects.filter(user=request.user).first()
        context = {
            'customer': customer,
            'cart': self.cart
        }
        return render(request, 'account.html', context)


class CartView(CartMixin, views.View):

    def get(self, request, *args, **kwargs):
        return render(request, 'cart.html', {"cart": self.cart})


class AddToCartView(CartMixin, views.View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        cart_product, created = CartProduct.objects.get_or_create(
            user=self.cart.owner, cart=self.cart, product=product
        )
        if created:
            self.cart.products.add(cart_product)
        recalc_cart(self.cart)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


class DeleteFromCartView(CartMixin, views.View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product = product
        )
        self.cart.products.remove(cart_product)
        cart_product.delete()
        recalc_cart(self.cart)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


class ChangeQTYView(CartMixin, views.View):

    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get('product_slug')
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product=product
        )
        qty = int(request.POST.get('qty'))
        cart_product.qty = qty
        cart_product.save()
        recalc_cart(self.cart)
        return HttpResponseRedirect(request.META['HTTP_REFERER'])


class CheckoutView(CartMixin, views.View):

    def get(self, request, *args, **kwargs):
        form = OrderForm(request.POST or None)
        context = {
            'cart': self.cart,
            'form': form,
        }
        return render(request, 'checkout.html', context)

class MakeOrderView(CartMixin, views.View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        form = OrderForm(request.POST or None)
        customer = Customer.objects.get(user=request.user)
        if form.is_valid():
            startdate = date.today()
            mindate = startdate+timedelta(days=3)
            order_date = form.cleaned_data['order_date']
            if order_date < mindate:
                message = 'Выберите корректную дату получения заказа'
                messages.add_message(request, messages.INFO, message)
                return HttpResponseRedirect('/checkout/')
            new_order = form.save(commit=False)
            new_order.customer = customer
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.order_date = form.cleaned_data['order_date']
            new_order.comment = form.cleaned_data['comment']
            new_order.save()

            self.cart.in_order = True
            self.cart.save()
            new_order.cart = self.cart
            new_order.save()
            customer.orders.add(new_order)
            messages.add_message(request, messages.INFO, 'Спасибо за заказ! Отслеживайте статус в разделе "Заказы"')
            return HttpResponseRedirect('/')
        return HttpResponseRedirect('/checkout/')


