import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "JamboPOS.settings")
django.setup()

from point_of_sale.views import _analytics_context
from point_of_sale.models import Sale, Product, SaleItem
from django.utils import timezone
from decimal import Decimal

def reproduce():
    print("Checking analytics data...")
    
    # Check if there are any sales
    sales_count = Sale.objects.count()
    print(f"Total sales: {sales_count}")
    
    if sales_count == 0:
        print("No sales found. Creating a test sale...")
        # Create a product if none exists
        product = Product.objects.first()
        if not product:
            from point_of_sale.models import Category
            cat = Category.objects.create(name="Test Cat")
            product = Product.objects.create(name="Test Product", price=Decimal("1000.00"), category=cat)
        
        sale = Sale.objects.create(total_amount=Decimal("1000.00"), subtotal=Decimal("1000.00"))
        SaleItem.objects.create(sale=sale, product=product, quantity=1, unit_price=Decimal("1000.00"))
        print("Test sale created.")

    context = _analytics_context()
    
    print("\nAnalytics Context Data:")
    print(f"daily_labels: {context.get('daily_labels')}")
    print(f"daily_totals: {context.get('daily_totals')}")
    print(f"product_labels: {context.get('product_labels')}")
    print(f"product_qty: {context.get('product_qty')}")
    
    # Check for empty data
    if not context.get('daily_labels'):
        print("\nWARNING: daily_labels is empty!")
    if not context.get('product_labels'):
        print("\nWARNING: product_labels is empty!")

if __name__ == "__main__":
    reproduce()
