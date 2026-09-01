from django.contrib.auth.models import User
from django.db import models


class Company(models.Model):
  name = models.CharField(max_length=255, unique=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return self.name


class UserProfile(models.Model):
  user = models.OneToOneField(
      User, on_delete=models.CASCADE, related_name='profile'
  )
  company = models.ForeignKey(
      Company, on_delete=models.CASCADE, related_name='users'
  )

  def __str__(self):
    return f'{self.user.username} ({self.company.name})'


class Category(models.Model):
  company = models.ForeignKey(
      Company, on_delete=models.CASCADE, related_name='categories'
  )
  name = models.CharField(max_length=100)

  class Meta:
    unique_together = ('company', 'name')
    verbose_name_plural = 'Categories'

  def __str__(self):
    return self.name


class Item(models.Model):
  company = models.ForeignKey(
      Company, on_delete=models.CASCADE, related_name='items'
  )
  name = models.CharField(max_length=255)
  category = models.ForeignKey(
      Category, on_delete=models.SET_NULL, null=True, blank=True
  )
  buy_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
  sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
  quantity_in_stock = models.IntegerField(default=0)
  reorder_level = models.IntegerField(default=5)

  class Meta:
    unique_together = ('company', 'name')

  def __str__(self):
    return self.name


class Sale(models.Model):
  company = models.ForeignKey(
      Company, on_delete=models.CASCADE, related_name='sales'
  )
  item = models.ForeignKey(Item, on_delete=models.CASCADE)
  quantity_sold = models.IntegerField(default=1)
  sell_price = models.DecimalField(max_digits=12, decimal_places=2)
  sales_date = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f'{self.quantity_sold}x {self.item.name} - {self.company.name}'


class StockIn(models.Model):
  company = models.ForeignKey(
      Company, on_delete=models.CASCADE, related_name='stock_entries'
  )
  item = models.ForeignKey(Item, on_delete=models.CASCADE)
  quantity_added = models.IntegerField(default=0)
  entry_date = models.DateTimeField(auto_now_add=True)