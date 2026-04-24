from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Product, Category, Sale, SaleItem
from django.utils import timezone
from decimal import Decimal

class PerformanceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', price=Decimal('100.00'), category=self.category)
        self.client = Client()
        self.client.login(username='testuser', password='password')

    def test_dashboard_load(self):
        # Create some sales
        sale = Sale.objects.create(total_amount=Decimal('100.00'), sold_by=self.user)
        SaleItem.objects.create(sale=sale, product=self.product, quantity=1, unit_price=Decimal('100.00'), subtotal=Decimal('100.00'))
        
        response = self.client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_analytics_load(self):
        # Create some sales across different days
        sale = Sale.objects.create(total_amount=Decimal('100.00'), sold_by=self.user)
        SaleItem.objects.create(sale=sale, product=self.product, quantity=1, unit_price=Decimal('100.00'), subtotal=Decimal('100.00'))
        
        response = self.client.get('/analytics/')
        self.assertEqual(response.status_code, 200)

    def test_checkout_logic(self):
        # Test the checkout view which used Decimal
        session = self.client.session
        session['cart'] = {str(self.product.id): {'quantity': 2, 'price': 100.00}}
        session.save()
        
        response = self.client.post('/checkout/', {
            'client_name': 'Test Client',
            'tax_rate': '10'
        })
        # Should redirect to receipt
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Sale.objects.filter(client_name='Test Client').exists())
        sale = Sale.objects.get(client_name='Test Client')
        self.assertEqual(sale.total_amount, Decimal('220.00')) # 200 + 10% tax
