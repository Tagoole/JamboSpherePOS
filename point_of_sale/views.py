from django.db.models import Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import *
from .models import Product, Sale, SaleItem


def _as_money(value) -> str:
	return f"{value:.2f}"


def _totals_context() -> dict:
	today = timezone.localdate()
	today_sales = Sale.objects.filter(sale_date__date=today)
	total_sales = today_sales.aggregate(total=Sum("total_amount"))["total"] or 0
	return {
		"total_sales_today": _as_money(total_sales),
		"transactions_today": today_sales.count(),
		"products_added_today": Product.objects.filter(created_at__date=today).count(),
	}


def _sales_rows(limit=None):
	queryset = SaleItem.objects.select_related("sale", "product").order_by("-sale__sale_date", "-id")
	if limit:
		queryset = queryset[:limit]

	return [
		{
			"id": item.sale_id,
			"created_at_display": timezone.localtime(item.sale.sale_date).strftime("%H:%M"),
			"product_name": item.product.name,
			"quantity": item.quantity,
			"total_amount": _as_money(item.subtotal),
		}
		for item in queryset
	]


@require_http_methods(["GET", "POST"])
def signup_view(request):
	if request.method == "POST":
		return redirect("dashboard")
	return render(request, "auth/signup.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
	if request.method == "POST":
		return redirect("dashboard")
	return render(request, "auth/login.html")


@require_GET
def logout_view(request):
	return redirect("login")


@require_GET
def dashboard_view(request):
	context = {
		**_totals_context(),
		"products": Product.objects.order_by("-created_at")[:5],
		"sales": _sales_rows(limit=5),
	}
	return render(request, "pos/dashboard.html", context)


@require_GET
def products_page(request):
	context = {"products": Product.objects.all()}
	return render(request, "pos/products.html", context)


@require_GET
def sales_page(request):
	context = {
		"products": Product.objects.all(),
		"sales": _sales_rows(),
		**_totals_context(),
	}
	return render(request, "pos/sales.html", context)


@require_GET
def reports_daily_page(request):
	return render(request, "pos/reports_daily.html", _totals_context())


@require_GET
def partial_products_list(request):
	return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})


@require_GET
def partial_sales_list(request):
	return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})


@require_GET
def partial_today_totals(request):
	return render(request, "pos/partials/today_totals.html", _totals_context())


@require_POST
def product_create(request):
	form_data = request.POST.copy()
	if "product_name" in form_data:
		form_data["name"] = form_data.get("product_name")
	if "product_price" in form_data:
		form_data["price"] = form_data.get("product_price")

	form = ProductForm(form_data)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid product data.")

	form.save()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@require_GET
def product_detail(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)
	return JsonResponse(
		{
			"id": product.id,
			"name": product.name,
			"price": _as_money(product.price),
			"created_at": timezone.localtime(product.created_at).isoformat(),
		}
	)


@require_POST
def product_update(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)

	form_data = request.POST.copy()
	if "product_name" in form_data:
		form_data["name"] = form_data.get("product_name")
	if "product_price" in form_data:
		form_data["price"] = form_data.get("product_price")

	form = ProductForm(form_data, instance=product)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid product update data.")

	form.save()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@require_POST
def product_delete(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)
	product.delete()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@require_POST
def sale_create(request):
	product_id = request.POST.get("sale_product")
	quantity = request.POST.get("sale_quantity")

	form = SaleRecordForm(
		{
			"product": product_id,
			"quantity": quantity,
			"total_amount": request.POST.get("sale_amount") or None,
		}
	)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid sale data.")

	product = form.cleaned_data["product"]
	qty = form.cleaned_data["quantity"]

	sale = Sale.objects.create()
	SaleItem.objects.create(sale=sale, product=product, quantity=qty)

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})
	return redirect("sales")


@require_GET
def sale_detail(request, sale_id: int):
	sale = get_object_or_404(Sale, pk=sale_id)
	items = [
		{
			"product": item.product.name,
			"quantity": item.quantity,
			"unit_price": _as_money(item.unit_price),
			"subtotal": _as_money(item.subtotal),
		}
		for item in sale.items.select_related("product").all()
	]
	return JsonResponse(
		{
			"id": sale.id,
			"sale_date": timezone.localtime(sale.sale_date).isoformat(),
			"total_amount": _as_money(sale.total_amount),
			"items": items,
		}
	)


@require_POST
def sale_update(request, sale_id: int):
	sale = get_object_or_404(Sale, pk=sale_id)
	item = sale.items.select_related("product").first()
	if not item:
		return JsonResponse({"error": "Sale item not found"}, status=404)

	product_id = request.POST.get("sale_product") or item.product_id
	quantity = request.POST.get("sale_quantity") or item.quantity

	form = SaleRecordForm(
		{
			"product": product_id,
			"quantity": quantity,
			"total_amount": request.POST.get("sale_amount") or None,
		}
	)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid sale update data.")

	item.product = form.cleaned_data["product"]
	item.quantity = form.cleaned_data["quantity"]
	item.unit_price = item.product.price
	item.subtotal = item.unit_price * item.quantity
	item.save()
	sale.update_total()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})
	return redirect("sales")


@require_POST
def sale_delete(request, sale_id: int):
	sale = get_object_or_404(Sale, pk=sale_id)
	sale.delete()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})
	return redirect("sales")
