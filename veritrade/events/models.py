"""Domain model for the VeriTrade marketplace.

Lifecycle, end to end:

    seller lists a product        -> Product.status = PENDING_EVALUATION
    evaluator claims it           -> EvaluationJob(CLAIMED), status = IN_EVALUATION
    evaluator submits a score     -> status = LISTED (or REJECTED)
    buyer checks out              -> Order + OrderItem + Delivery, status = SOLD
                                     buyer's credits are debited into escrow
    courier delivers              -> Delivery.DELIVERED, seller is paid out

Money never moves by assignment. Every balance change is written by
``events.services.credits`` alongside a :class:`CreditTransaction` row, so the
ledger and the balance can always be reconciled against each other.
"""

import uuid
from pathlib import Path

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .validators import phone_validator

PRODUCT_CATEGORIES = [
    ("MOB_TAB", _("Mobiles and Tablets")),
    ("LAP_COMP", _("Laptops and Computers")),
    ("TV_MON", _("Televisions and Monitors")),
    ("HOME_APP", _("Home Appliances")),
    ("COMP_ACC", _("Computer Accessories")),
    ("GAM_CON", _("Gaming Consoles")),
    ("AUD_VID", _("Audio and Video Devices")),
    ("NET_DEV", _("Networking Devices")),
    ("STO_DEV", _("Storage Devices")),
    ("CAM_CORD", _("Cameras and Camcorders")),
    ("WEAR", _("Wearables")),
    ("OFF_EQUIP", _("Office Equipment")),
    ("IND_ELEC", _("Industrial Electronics")),
    ("MED_DEV", _("Medical Devices")),
    ("MISC", _("Miscellaneous Electronics")),
]


class Role(models.TextChoices):
    MEMBER = "MEMBER", _("Buyer / Seller")
    EVALUATOR = "EVALUATOR", _("Evaluator")
    COURIER = "COURIER", _("Delivery partner")


def avatar_upload_to(instance, filename):
    """Opaque, collision-free path for a profile picture."""
    extension = Path(filename).suffix.lower().lstrip(".") or "jpg"
    return f"avatars/{uuid.uuid4().hex}.{extension}"


def product_image_upload_to(instance, filename):
    """Opaque, collision-free path for a product photo.

    Replaces the previous scheme, which renamed files on disk inside
    ``Model.save()`` and corrupted paths whenever a product was saved twice.
    """
    extension = Path(filename).suffix.lower().lstrip(".") or "jpg"
    return f"products/{uuid.uuid4().hex}.{extension}"


class TimestampedModel(models.Model):
    """Adds created/updated bookkeeping to every table that inherits it."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class UserProfile(TimestampedModel):
    """Everything about a person that Django's ``User`` does not already hold.

    A single profile carries the role, replacing the old parallel
    ``evaluatorGuy`` / ``deliveryGuy`` tables. The relation is one-to-one; the
    original code used a ForeignKey, which silently permitted several profiles
    per user and made "the user's address" ambiguous.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.MEMBER, db_index=True
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[phone_validator],
        help_text=_("Used by couriers to reach you about a delivery."),
    )
    avatar = models.ImageField(upload_to=avatar_upload_to, null=True, blank=True)

    street = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Workers can take themselves off the roster without logging out.
    is_available = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")
        indexes = [models.Index(fields=["role", "is_available"])]

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_role_display()})"

    def save(self, *args, **kwargs):
        # A blank phone number must be NULL, not "", or the unique constraint
        # would let only one person leave it empty.
        if not self.phone_number:
            self.phone_number = None
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.get_username()

    @property
    def has_address(self):
        return bool(self.street and self.city and self.postal_code)

    @property
    def full_address(self):
        parts = [self.street, self.city, self.state, self.postal_code, self.country]
        return ", ".join(part for part in parts if part)

    @property
    def is_member(self):
        return self.role == Role.MEMBER

    @property
    def is_evaluator(self):
        return self.role == Role.EVALUATOR

    @property
    def is_courier(self):
        return self.role == Role.COURIER


class CreditAccount(TimestampedModel):
    """A user's spendable balance.

    ``balance`` is a positive integer field, so the database itself refuses to
    store a negative balance. The old code subtracted the price without
    checking, letting buyers spend money they never had.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="credit_account"
    )
    balance = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = _("credit account")
        verbose_name_plural = _("credit accounts")

    def __str__(self):
        return f"{self.user.get_username()}: {self.balance}"


class CreditTransaction(models.Model):
    """Append-only ledger entry. One row per movement of credits.

    Rows are never updated or deleted; ``balance_after`` snapshots the account
    balance at the moment of the write so history can be audited without
    replaying every prior row.
    """

    class Kind(models.TextChoices):
        TOPUP = "TOPUP", _("Top-up")
        PURCHASE = "PURCHASE", _("Purchase")
        SALE = "SALE", _("Sale payout")
        REFUND = "REFUND", _("Refund")
        ADJUSTMENT = "ADJUSTMENT", _("Administrative adjustment")

    account = models.ForeignKey(
        CreditAccount, on_delete=models.CASCADE, related_name="transactions"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices, db_index=True)
    # Signed: negative debits the account, positive credits it.
    amount = models.IntegerField()
    balance_after = models.PositiveIntegerField()
    order = models.ForeignKey(
        "Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="credit_transactions",
    )
    memo = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("credit transaction")
        verbose_name_plural = _("credit transactions")
        ordering = ["-created_at", "-pk"]
        indexes = [models.Index(fields=["account", "-created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=~Q(amount=0), name="credit_transaction_amount_nonzero"
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.amount:+d} -> {self.balance_after}"


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


class ProductStatus(models.TextChoices):
    PENDING_EVALUATION = "PENDING", _("Awaiting evaluation")
    IN_EVALUATION = "EVALUATING", _("Being evaluated")
    LISTED = "LISTED", _("Listed for sale")
    REJECTED = "REJECTED", _("Rejected by evaluator")
    SOLD = "SOLD", _("Sold")


class ProductQuerySet(models.QuerySet):
    def listed(self):
        """Products a buyer may actually purchase."""
        return self.filter(status=ProductStatus.LISTED)

    def for_catalogue(self):
        """Listed products with everything the card template touches preloaded."""
        return (
            self.listed()
            .select_related("seller", "seller__user")
            .prefetch_related("images")
        )

    def awaiting_evaluation(self):
        return self.filter(status=ProductStatus.PENDING_EVALUATION)


class Product(TimestampedModel):
    seller = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="products"
    )
    name = models.CharField(max_length=120)
    category = models.CharField(
        max_length=16, choices=PRODUCT_CATEGORIES, default="MISC", db_index=True
    )
    description = models.TextField(max_length=5000)

    purchase_price = models.PositiveIntegerField(
        default=0, help_text=_("What the seller originally paid.")
    )
    purchased_on = models.DateField(null=True, blank=True)

    listed_price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    discount_percent = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(90)]
    )

    status = models.CharField(
        max_length=16,
        choices=ProductStatus.choices,
        default=ProductStatus.PENDING_EVALUATION,
        db_index=True,
    )
    evaluation_score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(100)]
    )
    evaluation_notes = models.TextField(max_length=2000, blank=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["seller", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(listed_price__gte=1), name="product_listed_price_positive"
            ),
            models.CheckConstraint(
                condition=Q(discount_percent__lte=90), name="product_discount_max_90"
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("marketplace:product_detail", args=[self.pk])

    @property
    def price(self):
        """What a buyer actually pays, after any seller discount."""
        if not self.discount_percent:
            return self.listed_price
        return round(self.listed_price * (100 - self.discount_percent) / 100)

    @property
    def savings(self):
        return self.listed_price - self.price

    @property
    def is_purchasable(self):
        return self.status == ProductStatus.LISTED

    @property
    def primary_image(self):
        """First photo, or None. Relies on prefetch_related('images')."""
        images = list(self.images.all())
        return images[0] if images else None


class ProductImage(models.Model):
    """One photo. Replaces the four ``product_image_N`` columns.

    Normalising these means the number of photos is a product decision rather
    than a schema change, and it removes the file-renaming logic that used to
    run inside ``Product.save()``.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=product_image_upload_to)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = _("product image")
        verbose_name_plural = _("product images")
        ordering = ["position", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "position"], name="product_image_unique_position"
            )
        ]

    def __str__(self):
        return f"{self.product.name} #{self.position}"


class CartItem(TimestampedModel):
    """A product a buyer intends to purchase.

    Adding to a cart deliberately does not reserve or hide the product. The old
    code flipped a flag on the product itself, so anyone could make any listing
    invisible to every other user simply by carting it.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="cart_entries"
    )

    class Meta:
        verbose_name = _("cart item")
        verbose_name_plural = _("cart items")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="cart_item_unique_per_user"
            )
        ]

    def __str__(self):
        return f"{self.user.get_username()} -> {self.product.name}"

    @property
    def price(self):
        return self.product.price


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class EvaluationJob(models.Model):
    """An evaluator's claim on a product awaiting assessment."""

    class Status(models.TextChoices):
        CLAIMED = "CLAIMED", _("In progress")
        COMPLETED = "COMPLETED", _("Completed")
        ABANDONED = "ABANDONED", _("Released")

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="evaluation_jobs"
    )
    evaluator = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="evaluation_jobs"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.CLAIMED, db_index=True
    )
    score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MaxValueValidator(100)]
    )
    notes = models.TextField(max_length=2000, blank=True)

    claimed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("evaluation job")
        verbose_name_plural = _("evaluation jobs")
        ordering = ["-claimed_at"]
        constraints = [
            # The database, not just the view layer, enforces "one open job".
            # Two evaluators racing for the same product means one gets an
            # IntegrityError rather than both believing they own it.
            models.UniqueConstraint(
                fields=["product"],
                condition=Q(status="CLAIMED"),
                name="evaluation_one_open_job_per_product",
            ),
            models.UniqueConstraint(
                fields=["evaluator"],
                condition=Q(status="CLAIMED"),
                name="evaluation_one_open_job_per_evaluator",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} / {self.evaluator.display_name}"

    def complete(self, score, notes=""):
        self.score = score
        self.notes = notes
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["score", "notes", "status", "completed_at"])


# ---------------------------------------------------------------------------
# Orders and delivery
# ---------------------------------------------------------------------------


class Order(TimestampedModel):
    """A single checkout. Holds one or more items, possibly across sellers."""

    class Status(models.TextChoices):
        PENDING = "PENDING", _("In progress")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    reference = models.CharField(max_length=12, unique=True, editable=False)
    buyer = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="orders"
    )
    total_amount = models.PositiveIntegerField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["buyer", "-created_at"])]

    def __str__(self):
        return self.reference

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = uuid.uuid4().hex[:10].upper()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """One product within an order.

    ``product`` is one-to-one: every listing is a single second-hand item, so it
    can appear in exactly one order for its whole life.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.OneToOneField(
        Product, on_delete=models.PROTECT, related_name="order_item"
    )
    seller = models.ForeignKey(
        UserProfile, on_delete=models.PROTECT, related_name="sales"
    )
    # Snapshot of the price at checkout; the product may be edited later.
    unit_price = models.PositiveIntegerField()

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")
        indexes = [models.Index(fields=["seller"])]

    def __str__(self):
        return f"{self.order.reference}: {self.product.name}"


class Delivery(TimestampedModel):
    """The physical movement of one order item from seller to buyer."""

    class Status(models.TextChoices):
        UNASSIGNED = "UNASSIGNED", _("Awaiting courier")
        ASSIGNED = "ASSIGNED", _("Courier assigned")
        PICKED_UP = "PICKED_UP", _("Picked up")
        DELIVERED = "DELIVERED", _("Delivered")
        CANCELLED = "CANCELLED", _("Cancelled")

    # Statuses in which the seller has not yet been paid and the job is live.
    OPEN_STATUSES = (Status.UNASSIGNED, Status.ASSIGNED, Status.PICKED_UP)

    order_item = models.OneToOneField(
        OrderItem, on_delete=models.CASCADE, related_name="delivery"
    )
    courier = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.UNASSIGNED,
        db_index=True,
    )

    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("delivery")
        verbose_name_plural = _("deliveries")
        ordering = ["-created_at"]
        constraints = [
            # Mirrors the evaluation constraint: a courier carries one job.
            models.UniqueConstraint(
                fields=["courier"],
                condition=Q(status__in=["ASSIGNED", "PICKED_UP"]),
                name="delivery_one_open_job_per_courier",
            ),
        ]

    def __str__(self):
        return f"{self.order_item.product.name} [{self.get_status_display()}]"

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def pickup_address(self):
        return self.order_item.seller.full_address

    @property
    def dropoff_address(self):
        return self.order_item.order.buyer.full_address
