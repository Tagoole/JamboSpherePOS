from datetime import datetime

from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import *
from .models import Category, Notification, Product, Sale, SaleItem
from .cart import Cart


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


def _sales_date_options() -> list:
	dates = list(Sale.objects.dates("sale_date", "day", order="DESC"))
	if not dates:
		dates = [timezone.localdate()]
	return [{"value": day.isoformat(), "label": day.strftime("%a, %B %d, %Y")} for day in dates]


def _selected_report_date(request):
	raw = request.GET.get("report_date")
	if raw:
		try:
			return datetime.strptime(raw, "%Y-%m-%d").date()
		except ValueError:
			pass

	date_options = _sales_date_options()
	if date_options:
		return datetime.strptime(date_options[0]["value"], "%Y-%m-%d").date()
	return timezone.localdate()


def _daily_summary_context(report_date) -> dict:
	today_sales = Sale.objects.filter(sale_date__date=report_date).order_by("-sale_date")
	today_items = SaleItem.objects.filter(sale__sale_date__date=report_date).select_related("product", "sale")

	total_sales = today_sales.aggregate(total=Sum("total_amount"))["total"] or 0
	transactions = today_sales.count()
	total_items = today_items.aggregate(total=Sum("quantity"))["total"] or 0
	unique_products = today_items.values("product_id").distinct().count()
	average_ticket = (total_sales / transactions) if transactions else 0
	highest_sale = today_sales.order_by("-total_amount").first()
	products_sold = (
		today_items.values("product__name")
		.annotate(total_qty=Sum("quantity"), revenue=Sum("subtotal"))
		.order_by("-total_qty", "product__name")
	)
	top_product = (
		today_items.values("product__name")
		.annotate(total_qty=Sum("quantity"))
		.order_by("-total_qty")
		.first()
	)

	products_sold_rows = [
		{
			"name": row["product__name"],
			"qty": row["total_qty"],
			"revenue": _as_money(row["revenue"] or 0),
		}
		for row in products_sold
	]

	return {
		"total_sales_today": _as_money(total_sales),
		"transactions_today": transactions,
		"products_added_today": Product.objects.filter(created_at__date=report_date).count(),
		"total_items_sold_today": total_items,
		"unique_products_sold_today": unique_products,
		"avg_sale_value_today": _as_money(average_ticket),
		"highest_sale_today": _as_money(highest_sale.total_amount) if highest_sale else "0.00",
		"top_product_today": top_product["product__name"] if top_product else "N/A",
		"recent_sales": _sales_rows(limit=8, report_date=report_date),
		"products_sold_rows": products_sold_rows,
		"selected_report_date": report_date.isoformat(),
		"selected_report_date_label": report_date.strftime("%a, %B %d, %Y"),
	}


def _analytics_context() -> dict:
	rows = list(
		Sale.objects.annotate(day=TruncDate("sale_date"))
		.values("day")
		.annotate(total=Sum("total_amount"), transactions=Count("id"))
		.order_by("day")
	)

	daily_labels = [row["day"].strftime("%d %b") for row in rows]
	daily_totals = [float(row["total"] or 0) for row in rows]
	daily_transactions = [int(row["transactions"] or 0) for row in rows]

	weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
	weekday_totals = [0.0] * 7
	for row in rows:
		weekday_totals[row["day"].weekday()] += float(row["total"] or 0)

	weekly_totals = {}
	for row in rows:
		year, week, _ = row["day"].isocalendar()
		key = f"{year}-W{int(week):02d}"
		weekly_totals[key] = weekly_totals.get(key, 0.0) + float(row["total"] or 0)

	weekly_items = list(weekly_totals.items())[-10:]
	weekly_labels = [item[0] for item in weekly_items]
	weekly_values = [round(item[1], 2) for item in weekly_items]

	product_rows = (
		SaleItem.objects.values("product__name")
		.annotate(qty=Sum("quantity"), revenue=Sum("subtotal"))
		.order_by("-qty", "product__name")[:8]
	)
	product_labels = [row["product__name"] for row in product_rows]
	product_qty = [int(row["qty"] or 0) for row in product_rows]
	product_revenue = [float(row["revenue"] or 0) for row in product_rows]

	total_revenue = round(sum(daily_totals), 2)
	total_transactions = sum(daily_transactions)
	avg_daily = round((total_revenue / len(rows)), 2) if rows else 0

	return {
		"daily_labels": daily_labels,
		"daily_totals": daily_totals,
		"daily_transactions": daily_transactions,
		"weekday_labels": weekday_labels,
		"weekday_totals": [round(v, 2) for v in weekday_totals],
		"weekly_labels": weekly_labels,
		"weekly_totals": weekly_values,
		"product_labels": product_labels,
		"product_qty": product_qty,
		"product_revenue": product_revenue,
		"analytics_total_revenue": _as_money(total_revenue),
		"analytics_total_transactions": total_transactions,
		"analytics_average_daily": _as_money(avg_daily),
	}


def _sales_rows(limit=None, report_date=None):
	queryset = Sale.objects.all()
	if report_date:
		queryset = queryset.filter(sale_date__date=report_date)

	queryset = queryset.order_by("-sale_date")
	if limit:
		queryset = queryset[:limit]

	return [
		{
			"id": sale.id,
			"created_at_display": timezone.localtime(sale.sale_date).strftime("%H:%M"),
			"total_amount": _as_money(sale.total_amount),
		}
		for sale in queryset
	]


@require_http_methods(["GET", "POST"])
def signup_view(request):
	if request.user.is_authenticated:
		return redirect("dashboard")

	form = SignUpForm(request.POST or None)
	if request.method == "POST":
		if form.is_valid():
			user = form.save()
			auth_login(request, user)
			return redirect("dashboard")
	return render(request, "auth/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def login_view(request):
	if request.user.is_authenticated:
		return redirect("dashboard")

	form = LoginForm(request, data=request.POST or None)
	if request.method == "POST":
		if form.is_valid():
			auth_login(request, form.get_user())
			next_url = request.POST.get("next") or request.GET.get("next")
			return redirect(next_url or "dashboard")

	return render(request, "auth/login.html", {"form": form, "next": request.GET.get("next", "")})


@require_GET
def logout_view(request):
	auth_logout(request)
	return redirect("login")


@login_required(login_url="login")
@require_GET
def dashboard_view(request):
	context = {
		**_totals_context(),
		"products": Product.objects.order_by("-created_at")[:5],
		"sales": _sales_rows(limit=5),
		"notifications": Notification.objects.all()[:5],
	}
	return render(request, "pos/dashboard.html", context)


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def notifications_page(request):
	if request.method == "POST":
		if not request.user.is_staff:
			return HttpResponseBadRequest("Only admins can create notifications.")
		
		form = NotificationForm(request.POST)
		if form.is_valid():
			notification = form.save(commit=False)
			notification.created_by = request.user
			notification.save()
			return redirect("notifications")
	
	context = {
		"notifications": Notification.objects.all(),
		"form": NotificationForm() if request.user.is_staff else None
	}
	return render(request, "pos/notifications.html", context)


@login_required(login_url="login")
@require_POST
def notification_delete(request, notification_id: int):
	if not request.user.is_staff:
		return HttpResponseBadRequest("Only admins can delete notifications.")
	
	notification = get_object_or_404(Notification, pk=notification_id)
	notification.delete()
	return redirect("notifications")


@login_required(login_url="login")
@require_GET
def products_page(request):
	context = {
		"products": Product.objects.all(),
		"categories": Category.objects.all()
	}
	return render(request, "pos/products.html", context)


@login_required(login_url="login")
@require_GET
def sales_page(request):
	context = {
		"products": Product.objects.all(),
		"categories": Category.objects.all(),
		"sales": _sales_rows(),
		**_totals_context(),
		"cart": Cart(request),
	}
	return render(request, "pos/sales.html", context)


@login_required(login_url="login")
@require_POST
def category_create(request):
	if not request.user.is_staff:
		return HttpResponseBadRequest("Only admins can create categories.")
	
	form = CategoryForm(request.POST)
	if form.is_valid():
		form.save()
		return redirect("products")
	return HttpResponseBadRequest("Invalid category data.")


@login_required(login_url="login")
@require_GET
def reports_daily_page(request):
	report_date = _selected_report_date(request)
	context = {
		**_daily_summary_context(report_date),
		"sale_dates": _sales_date_options(),
	}
	return render(request, "pos/reports_daily.html", context)


@login_required(login_url="login")
@require_GET
def analytics_page(request):
	context = {
		**_totals_context(),
		**_analytics_context(),
	}
	return render(request, "pos/analytics.html", context)


@login_required(login_url="login")
@require_GET
def partial_analytics_summary(request):
	context = {
		**_totals_context(),
		**_analytics_context(),
	}
	return render(request, "pos/partials/analytics_summary.html", context)


@login_required(login_url="login")
@require_GET
def partial_products_list(request):
	return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})


@login_required(login_url="login")
@require_GET
def partial_recent_products_list(request):
	return render(request, "pos/partials/product_row_dashboard.html", {"products": Product.objects.order_by("-created_at")[:5]})


@login_required(login_url="login")
@require_GET
def partial_sales_list(request):
	return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})


@login_required(login_url="login")
@require_GET
def partial_recent_sales_list(request):
	return render(request, "pos/partials/sale_row_dashboard.html", {"sales": _sales_rows(limit=5)})


@login_required(login_url="login")
@require_GET
def partial_today_totals(request):
	return render(request, "pos/partials/today_totals.html", _totals_context())


@login_required(login_url="login")
@require_GET
def partial_daily_summary_details(request):
	report_date = _selected_report_date(request)
	return render(request, "pos/partials/daily_summary_detail.html", _daily_summary_context(report_date))


@login_required(login_url="login")
@require_POST
def product_create(request):
	form_data = request.POST.copy()
	if "product_name" in form_data:
		form_data["name"] = form_data.get("product_name")
	if "product_price" in form_data:
		form_data["price"] = form_data.get("product_price")
	if "product_category" in form_data:
		form_data["category"] = form_data.get("product_category")

	form = ProductForm(form_data, request.FILES)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid product data.")

	form.save()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@login_required(login_url="login")
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


@login_required(login_url="login")
@require_http_methods(["GET", "POST"])
def product_edit_page(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)
	if request.method == "POST":
		form_data = request.POST.copy()
		if "product_name" in form_data:
			form_data["name"] = form_data.get("product_name")
		if "product_price" in form_data:
			form_data["price"] = form_data.get("product_price")
		if "product_category" in form_data:
			form_data["category"] = form_data.get("product_category")

		form = ProductForm(form_data, request.FILES, instance=product)
		if form.is_valid():
			form.save()
			return redirect("products")
	else:
		form = ProductForm(instance=product)

	return render(request, "pos/product_edit.html", {
		"form": form,
		"product": product,
		"categories": Category.objects.all()
	})


@login_required(login_url="login")
@require_POST
def product_update(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)

	form_data = request.POST.copy()
	if "product_name" in form_data:
		form_data["name"] = form_data.get("product_name")
	if "product_price" in form_data:
		form_data["price"] = form_data.get("product_price")
	if "product_category" in form_data:
		form_data["category"] = form_data.get("product_category")

	form = ProductForm(form_data, request.FILES, instance=product)
	if not form.is_valid():
		return HttpResponseBadRequest("Invalid product update data.")

	form.save()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@login_required(login_url="login")
@require_POST
def product_delete(request, product_id: int):
	product = get_object_or_404(Product, pk=product_id)

	# Keep analytics and sales screens consistent: if a product is removed,
	# remove all sales that contain that product.
	related_sale_ids = list(
		SaleItem.objects.filter(product=product).values_list("sale_id", flat=True).distinct()
	)
	if related_sale_ids:
		Sale.objects.filter(id__in=related_sale_ids).delete()

	product.delete()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/product_row.html", {"products": Product.objects.all()})
	return redirect("products")


@login_required(login_url="login")
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


@login_required(login_url="login")
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


@login_required(login_url="login")
@require_POST
def sale_delete(request, sale_id: int):
	sale = get_object_or_404(Sale, pk=sale_id)
	sale.delete()

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/sale_row.html", {"sales": _sales_rows()})
	return redirect("sales")
@login_required(login_url="login")
@require_POST
def cart_add(request, product_id):
	cart = Cart(request)
	product = get_object_or_404(Product, id=product_id)
	quantity = int(request.POST.get("quantity", 1))
	override = request.POST.get("override", "False") == "True"
	
	cart.add(product=product, quantity=quantity, override_quantity=override)
	
	# If quantity is <= 0 after update, remove it
	if str(product.id) in cart.cart and cart.cart[str(product.id)]["quantity"] <= 0:
		cart.remove(product)

	if request.headers.get("HX-Request") == "true":
		return render(request, "pos/partials/cart_count.html", {"cart_count": len(cart)})
	
	# If request came from cart page, redirect back to cart
	if "cart" in request.META.get("HTTP_REFERER", ""):
		return redirect("cart_detail")
	
	return redirect("sales")


@login_required(login_url="login")
@require_POST
def cart_remove(request, product_id):
	cart = Cart(request)
	product = get_object_or_404(Product, id=product_id)
	cart.remove(product)
	return redirect("cart_detail")


@login_required(login_url="login")
def cart_detail(request):
	cart = Cart(request)
	return render(request, "pos/cart.html", {"cart": cart})


@login_required(login_url="login")
@require_POST
def checkout(request):
	cart = Cart(request)
	if not cart:
		return redirect("sales")

	# Get extra info from form
	client_name = request.POST.get("client_name", "")
	client_contact = request.POST.get("client_contact", "")
	notes = request.POST.get("notes", "")
	tax_rate_val = Decimal(request.POST.get("tax_rate", "0"))

	subtotal = Decimal(cart.get_total_price())
	tax_amount = (subtotal * (tax_rate_val / 100)).quantize(Decimal("0.01"))
	total_amount = subtotal + tax_amount

	# Create the Sale
	sale = Sale.objects.create(
		subtotal=subtotal,
		tax_rate=tax_rate_val,
		tax_amount=tax_amount,
		total_amount=total_amount,
		client_name=client_name,
		client_contact=client_contact,
		notes=notes,
		sold_by=request.user
	)

	# Record Sale Items
	for item in cart:
		SaleItem.objects.create(
			sale=sale,
			product=item["product"],
			quantity=item["quantity"],
			unit_price=item["price"]
		)

	# Clear Cart
	cart.clear()

	return redirect("sale_receipt", sale_id=sale.id)


@login_required(login_url="login")
@require_GET
def sale_receipt(request, sale_id):
	sale = get_object_or_404(Sale, id=sale_id)
	context = {
		"sale": sale,
		"items": sale.items.all(),
	}
	return render(request, "pos/receipt.html", context)
