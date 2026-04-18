from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Product, Sale, SaleItem


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = "__all__"


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ["sale_date"]


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ["sale", "product", "quantity"]


class SaleRecordForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    quantity = forms.IntegerField(min_value=1)
    total_amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False)


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=150)