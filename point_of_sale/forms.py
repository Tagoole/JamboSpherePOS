from django import forms

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