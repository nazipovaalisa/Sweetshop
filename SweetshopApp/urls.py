from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import BaseView, ProductDetailView, AddToCartView, ChangeQTYView, DeleteFromCartView, LoginView, \
    RegistrationView, AccountView, CartView, CheckoutView, MakeOrderView, CategoryView, EmailVerifyView, ConfirmView, InvalidVerify

urlpatterns = [
    path('add-to-cart/<str:product_slug>/', AddToCartView.as_view(), name='add_to_cart'),
    path('delete-from-cart/<str:product_slug>/', DeleteFromCartView.as_view(), name='delete_from_cart'),
    path('change-qty/<str:product_slug>/', ChangeQTYView.as_view(), name='change_gty'),
    path('', BaseView.as_view(), name='base'),
    path('category/<slug:cat_slug>/', CategoryView.as_view(), name='category'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('verify_email/<uidb64>/<token>', EmailVerifyView.as_view(), name='verify_email'),
    path('confirm_email/', ConfirmView.as_view(), name='confirm_email'),
    path('invalid_verify/', InvalidVerify.as_view(), name='invalid_verify'),
    path('account/', AccountView.as_view(), name='account'),
    path('cart/', CartView.as_view(), name = 'cart'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('make-order/', MakeOrderView.as_view(), name='make-order'),
    path('<str:cat_slug>/<str:product_slug>/', ProductDetailView.as_view(), name='product_detail'),
]