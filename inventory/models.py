from django.contrib.auth.models import User
from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    ROLE_OWNER = "owner"
    ROLE_STAFF = "staff"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_STAFF, "Staff"),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="users"
    )
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER
    )

    # Flexible permissions (Owner always has full access)
    can_manage_stock = models.BooleanField(default=True)
    can_edit_items = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=True)
    can_manage_categories = models.BooleanField(default=False)
    can_manage_team = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.company.name}) – {self.get_role_display()}"

    @property
    def is_owner(self):
        return self.role == self.ROLE_OWNER

    def has_perm(self, perm_name):
        """Check a permission. Owners always return True."""
        if self.is_owner:
            return True
        return getattr(self, perm_name, False)


class Category(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("company", "name")
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Item(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="items"
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
        unique_together = ("company", "name")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name:
            self.name = " ".join(self.name.strip().split()).title()
        super().save(*args, **kwargs)


class Sale(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="sales"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity_sold = models.IntegerField(default=1)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2)
    sales_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity_sold}x {self.item.name} - {self.company.name}"

    @property
    def line_total(self):
        return self.quantity_sold * self.sell_price

    @property
    def estimated_cost(self):
        return self.quantity_sold * self.item.buy_price

    @property
    def estimated_profit(self):
        return self.line_total - self.estimated_cost


class StockIn(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="stock_entries"
    )
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity_added = models.IntegerField(default=0)
    entry_date = models.DateTimeField(auto_now_add=True)
