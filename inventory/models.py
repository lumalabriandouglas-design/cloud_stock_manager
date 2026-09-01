from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    low_stock_email_alerts = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def subscription(self):
        return getattr(self, "sub", None)

    def is_subscription_active(self):
        sub = self.subscription
        if sub is None:
            return False
        return sub.is_active


class Subscription(models.Model):
    STATUS_TRIAL = "trial"
    STATUS_ACTIVE = "active"
    STATUS_PAST_DUE = "past_due"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_TRIAL, "Trial"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_PAST_DUE, "Past due"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    PLAN_AMOUNT_UGX = 15000  # monthly price
    TRIAL_DAYS = 7

    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="sub")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    flutterwave_tx_ref = models.CharField(max_length=100, blank=True)
    last_payment_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company.name} – {self.status}"

    @classmethod
    def start_trial(cls, company):
        return cls.objects.create(
            company=company,
            status=cls.STATUS_TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=cls.TRIAL_DAYS),
        )

    @property
    def is_active(self):
        now = timezone.now()
        if self.status == self.STATUS_ACTIVE:
            if self.current_period_end and self.current_period_end < now:
                return False
            return True
        if self.status == self.STATUS_TRIAL:
            return self.trial_ends_at and self.trial_ends_at >= now
        return False

    def activate_for_month(self, tx_ref=""):
        now = timezone.now()
        self.status = self.STATUS_ACTIVE
        self.last_payment_at = now
        self.current_period_end = now + timedelta(days=30)
        if tx_ref:
            self.flutterwave_tx_ref = tx_ref
        self.save()

    def mark_suspended(self):
        self.status = self.STATUS_SUSPENDED
        self.save()


class UserProfile(models.Model):
    ROLE_OWNER = "owner"
    ROLE_STAFF = "staff"
    ROLE_CHOICES = [
        (ROLE_OWNER, "Owner"),
        (ROLE_STAFF, "Staff"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="users")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_OWNER)

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
        if self.is_owner:
            return True
        return getattr(self, perm_name, False)


class Category(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ("company", "name")
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Item(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
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

    @property
    def is_low_stock(self):
        return self.quantity_in_stock <= self.reorder_level


class Sale(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sales")
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
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="stock_entries")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity_added = models.IntegerField(default=0)
    entry_date = models.DateTimeField(auto_now_add=True)


class ActivityLog(models.Model):
    ACTION_SALE = "sale"
    ACTION_STOCK_IN = "stock_in"
    ACTION_ITEM_EDIT = "item_edit"
    ACTION_OTHER = "other"
    ACTION_CHOICES = [
        (ACTION_SALE, "Sale"),
        (ACTION_STOCK_IN, "Stock In"),
        (ACTION_ITEM_EDIT, "Item Edit"),
        (ACTION_OTHER, "Other"),
    ]

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="activities")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default=ACTION_OTHER)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.message} ({self.created_at})"
