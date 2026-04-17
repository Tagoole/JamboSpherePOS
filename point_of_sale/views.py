from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

# Temporary in-memory storage for prototype routes.
# Swap these with model-backed queries later.
PRODUCTS = []
SALES = []
NEXT_PRODUCT_ID = 1
NEXT_SALE_ID = 1


def _as_money(value: Decimal) -> str:
	return f"{value:.2f}"


def _totals_context() -> dict:
	total_sales = sum(Decimal(sale["total_amount"]) for sale in SALES) if SALES else Decimal("0")
	return {
		"total_sales_today": _as_money(total_sales),
		"transactions_today": len(SALES),
		"products_added_today": len(PRODUCTS),
	}


def _find_product(product_id: int):
	return next((product for product in PRODUCTS if product["id"] == product_id), None)


def _find_sale(sale_id: int):
	return next((sale for sale in SALES if sale["id"] == sale_id), None)


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
		"products": list(reversed(PRODUCTS[:5])),
		"sales": list(reversed(SALES[:5])),
	}
	return render(request, "pos/dashboard.html", context)


@require_GET
def products_page(request):
	context = {"products": list(reversed(PRODUCTS))}
	return render(request, "pos/products.html", context)


@require_GET
def sales_page(request):
	context = {
		"products": list(reversed(PRODUCTS)),
		"sales": list(reversed(SALES)),
		**_totals_context(),
	}
	return render(request, "pos/sales.html", context)


@require_GET
def reports_daily_page(request):
	return render(request, "pos/reports_daily.html", _totals_context())


@require_http_methods(["GET", "POST"])
def settings_page(request):
	return render(request, "pos/settings.html")


@require_GET
def partial_products_list(request):
	return render(request, "pos/partials/product_row.html", {"products": list(reversed(PRODUCTS))})


@require_GET
def partial_sales_list(request):
	return render(request, "pos/partials/sale_row.html", {"sales": list(reversed(SALES))})


@require_GET
def partial_today_totals(request):
	return render(request, "pos/partials/today_totals.html", _totals_context())


@require_POST
def product_create(request):
	global NEXT_PRODUCT_ID

	name = (request.POST.get("product_name") or request.POST.get("name") or "").strip()
	price_raw = (request.POST.get("product_price") or request.POST.get("price") or "").strip()

	if not name:
		return HttpResponseBadRequest("Product name is required.")

	try:
		price = Decimal(price_raw)
	except (InvalidOperation, TypeError):
		return HttpResponseBadRequest("Valid price is required.")

	if price < 0:
		return HttpResponseBadRequest("Price cannot be negative.")

	PRODUCTS.append(
		{
			"id": NEXT_PRODUCT_ID,
			"name": name,
			"price": _as_money(price),
		}
	)
	NEXT_PRODUCT_ID += 1

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": list(reversed(PRODUCTS))})
	return redirect("products")


@require_GET
def product_detail(request, product_id: int):
	product = _find_product(product_id)
	if not product:
		return JsonResponse({"error": "Product not found"}, status=404)
	return JsonResponse(product)


@require_POST
def product_update(request, product_id: int):
	product = _find_product(product_id)
	if not product:
		return JsonResponse({"error": "Product not found"}, status=404)

	name = (request.POST.get("product_name") or request.POST.get("name") or product["name"]).strip()
	price_raw = (request.POST.get("product_price") or request.POST.get("price") or product["price"]).strip()

	try:
		price = Decimal(price_raw)
	except (InvalidOperation, TypeError):
		return HttpResponseBadRequest("Valid price is required.")

	if price < 0:
		return HttpResponseBadRequest("Price cannot be negative.")

	product["name"] = name
	product["price"] = _as_money(price)

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": list(reversed(PRODUCTS))})
	return redirect("products")


@require_POST
def product_delete(request, product_id: int):
	product = _find_product(product_id)
	if not product:
		return JsonResponse({"error": "Product not found"}, status=404)

	PRODUCTS.remove(product)
	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": list(reversed(PRODUCTS))})
	return redirect("products")


@require_POST
def sale_create(request):
	global NEXT_SALE_ID

	product_id_raw = (request.POST.get("sale_product") or "").strip()
	quantity_raw = (request.POST.get("sale_quantity") or "1").strip()
	amount_raw = (request.POST.get("sale_amount") or "").strip()

	try:
		quantity = int(quantity_raw)
	except ValueError:
		return HttpResponseBadRequest("Quantity must be an integer.")

	if quantity <= 0:
		return HttpResponseBadRequest("Quantity must be greater than zero.")

	try:
		total_amount = Decimal(amount_raw)
	except (InvalidOperation, TypeError):
		return HttpResponseBadRequest("Valid amount is required.")

	if total_amount < 0:
		return HttpResponseBadRequest("Amount cannot be negative.")

	product_name = "Unknown Product"
	if product_id_raw.isdigit():
		matched_product = _find_product(int(product_id_raw))
		if matched_product:
			product_name = matched_product["name"]

	sale = {
		"id": NEXT_SALE_ID,
		"product_name": product_name,
		"quantity": quantity,
		"total_amount": _as_money(total_amount),
		"created_at_display": datetime.now().strftime("%H:%M"),
	}
	SALES.append(sale)
	NEXT_SALE_ID += 1

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": list(reversed(SALES))})
	return redirect("sales")


@require_GET
def sale_detail(request, sale_id: int):
	sale = _find_sale(sale_id)
	if not sale:
		return JsonResponse({"error": "Sale not found"}, status=404)
	return JsonResponse(sale)


@require_POST
def sale_update(request, sale_id: int):
	sale = _find_sale(sale_id)
	if not sale:
		return JsonResponse({"error": "Sale not found"}, status=404)

	quantity_raw = (request.POST.get("sale_quantity") or sale["quantity"])
	amount_raw = (request.POST.get("sale_amount") or sale["total_amount"])
	product_name = (request.POST.get("product_name") or sale["product_name"]).strip()

	try:
		quantity = int(quantity_raw)
	except ValueError:
		return HttpResponseBadRequest("Quantity must be an integer.")

	if quantity <= 0:
		return HttpResponseBadRequest("Quantity must be greater than zero.")

	try:
		total_amount = Decimal(amount_raw)
	except (InvalidOperation, TypeError):
		return HttpResponseBadRequest("Valid amount is required.")

	if total_amount < 0:
		return HttpResponseBadRequest("Amount cannot be negative.")

	sale["quantity"] = quantity
	sale["total_amount"] = _as_money(total_amount)
	sale["product_name"] = product_name

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": list(reversed(SALES))})
	return redirect("sales")


@require_POST
def sale_delete(request, sale_id: int):
	sale = _find_sale(sale_id)
	if not sale:
		return JsonResponse({"error": "Sale not found"}, status=404)

	SALES.remove(sale)
	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": list(reversed(SALES))})
	return redirect("sales")
