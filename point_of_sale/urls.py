from django.urls import path

from . import views

urlpatterns = [
	path("", views.login_view, name="root"),
	path("signup/", views.signup_view, name="signup"),
	path("login/", views.login_view, name="login"),
	path("logout/", views.logout_view, name="logout"),
	path("dashboard/", views.dashboard_view, name="dashboard"),
	path("products/", views.products_page, name="products"),
	path("products/add/", views.product_create, name="product-create"),
	path("products/<int:product_id>/", views.product_detail, name="product-detail"),
	path("products/<int:product_id>/update/", views.product_update, name="product-update"),
	path("products/<int:product_id>/delete/", views.product_delete, name="product-delete"),
	path("sales/", views.sales_page, name="sales"),
	path("sales/record/", views.sale_create, name="sale-create"),
	path("sales/<int:sale_id>/", views.sale_detail, name="sale-detail"),
	path("sales/<int:sale_id>/update/", views.sale_update, name="sale-update"),
	path("sales/<int:sale_id>/delete/", views.sale_delete, name="sale-delete"),
	path("reports/daily/", views.reports_daily_page, name="reports-daily"),
	path("partials/products-list/", views.partial_products_list, name="partials-products-list"),
	path("partials/sales-list/", views.partial_sales_list, name="partials-sales-list"),
	path("partials/today-totals/", views.partial_today_totals, name="partials-today-totals"),
]
