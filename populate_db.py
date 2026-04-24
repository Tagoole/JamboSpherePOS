import os
import django
from decimal import Decimal

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "JamboPOS.settings")
django.setup()

from point_of_sale.models import Category, Product, Sale, SaleItem, Notification

def populate():
    print("Deleting current data...")
    SaleItem.objects.all().delete()
    Sale.objects.all().delete()
    Product.objects.all().delete()
    Category.objects.all().delete()
    Notification.objects.all().delete()
    print("Data cleared.")

    data = {
        "Beverages": [
            ("Espresso", 3500),
            ("Americano", 4500),
            ("Cappuccino", 6500),
            ("Cafe Latte", 7000),
            ("Caramel Macchiato", 8500),
            ("Iced Coffee", 5500),
            ("Masala Tea", 4000),
            ("Green Tea", 4000),
            ("Hot Chocolate", 6000),
            ("Fresh Orange Juice", 7500),
            ("Passion Fruit Juice", 6000),
            ("Mineral Water (500ml)", 2000),
            ("Coca Cola (300ml)", 2500),
        ],
        "Bakery": [
            ("Butter Croissant", 5000),
            ("Chocolate Croissant", 6500),
            ("Cinnamon Roll", 5500),
            ("Blueberry Muffin", 4500),
            ("Apple Turnovers", 6000),
            ("Baguette", 4000),
            ("Whole Wheat Bread", 7500),
            ("Donut (Glazed)", 3000),
        ],
        "Snacks & Light Meals": [
            ("Chicken Sandwich", 12000),
            ("Beef Burger", 15000),
            ("Veggie Wrap", 10000),
            ("Classic Club Sandwich", 18000),
            ("French Fries", 5000),
            ("Samosas (Pair)", 3000),
            ("Rolex (Special)", 4500),
        ],
        "Desserts": [
            ("Chocolate Brownie", 7000),
            ("New York Cheesecake", 12000),
            ("Fruit Salad", 8000),
            ("Ice Cream Scoop", 4000),
            ("Red Velvet Cupcake", 5000),
        ]
    }

    print("Creating categories and products...")
    for cat_name, products in data.items():
        category = Category.objects.create(name=cat_name)
        for prod_name, price in products:
            Product.objects.create(
                name=prod_name,
                price=Decimal(str(price)),
                category=category
            )
    
    print("Creating initial notifications...")
    from django.contrib.auth.models import User
    admin_user = User.objects.filter(is_staff=True).first()
    if admin_user:
        Notification.objects.create(
            title="System Reset",
            message="The database has been cleared and populated with fresh menu items.",
            created_by=admin_user
        )

    print("\nSuccess! Database populated inside the container.")

if __name__ == "__main__":
    populate()
