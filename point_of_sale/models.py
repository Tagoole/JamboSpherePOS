from django.db import models
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ["name"]
        
        

class Sale(models.Model):
    sale_date = models.DateTimeField(default=timezone.now)
    subtotal = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00) # Percentage
    tax_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    
    # Client info
    client_name = models.CharField(max_length=100, blank=True, null=True)
    client_contact = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    # Audit
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sales_recorded")

    def __str__(self):
        return f"Sale #{self.id} - {self.sale_date.strftime('%Y-%m-%d %H:%M')} - UGX {self.total_amount:,}"
    
    class Meta:
        ordering = ["-sale_date"]
        
        
    def update_total(self):
        total = self.items.aggregate(total=Sum("subtotal"))["total"] or 0
        self.total_amount = total
        self.save(update_fields=["total_amount"])
        
        
        
        

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale,on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        editable=False,
        help_text="Price at the time of sale (auto-filled)"
    )
    
    subtotal = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0.00,
        editable=False
    )
    
    def save(self, *args, **kwargs):
        if not self.unit_price or self.unit_price == 0:
            self.unit_price = self.product.price # automatically set unit price from the product price
            
            #calculate the subtotal
            self.subtotal = self.unit_price * self.quantity
            
            super().save(*args, **kwargs)
            
            if self.sale:
                self.sale.update_total() # update the total amount of the sale whenever a sale item is saved or updated
                
    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ UGX {self.unit_price:,}"
    
    class Meta:
        unique_together = ('sale', 'product')


class Notification(models.Model):
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_notifications")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-created_at"]
            
            