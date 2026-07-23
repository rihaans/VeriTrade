"""Admin configuration.

Registration used to be eight bare ``admin.site.register`` calls, which gives
unsearchable lists of ``object (1)`` rows and lets a staff user hand-edit a
credit balance without leaving a ledger entry. Financial records are read-only
here; balances change through ``events.services.credits`` or not at all.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CartItem,
    CreditAccount,
    CreditTransaction,
    Delivery,
    EvaluationJob,
    Order,
    OrderItem,
    Product,
    ProductImage,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "phone_number", "city", "is_available", "created_at")
    list_filter = ("role", "is_available", "country")
    search_fields = ("user__username", "user__email", "phone_number", "city")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("user",)


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 0
    fields = ("image", "position", "preview")
    readonly_fields = ("preview",)

    @admin.display(description="Preview")
    def preview(self, obj):
        if not obj.image:
            return "-"
        return format_html(
            '<img src="{}" style="height:64px;border-radius:6px" alt="">', obj.image.url
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name", "seller", "category", "status", "listed_price",
        "discount_percent", "evaluation_score", "created_at",
    )
    list_filter = ("status", "category", "created_at")
    search_fields = ("name", "description", "seller__user__username")
    autocomplete_fields = ("seller",)
    readonly_fields = ("created_at", "updated_at", "evaluated_at")
    inlines = [ProductImageInline]
    list_select_related = ("seller", "seller__user")
    date_hierarchy = "created_at"


@admin.register(EvaluationJob)
class EvaluationJobAdmin(admin.ModelAdmin):
    list_display = ("product", "evaluator", "status", "score", "claimed_at", "completed_at")
    list_filter = ("status", "claimed_at")
    search_fields = ("product__name", "evaluator__user__username")
    autocomplete_fields = ("product", "evaluator")
    readonly_fields = ("claimed_at", "completed_at")
    list_select_related = ("product", "evaluator", "evaluator__user")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "seller", "unit_price")
    readonly_fields = ("product", "seller", "unit_price")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "buyer", "total_amount", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "buyer__user__username", "buyer__user__email")
    readonly_fields = ("reference", "buyer", "total_amount", "created_at", "updated_at")
    inlines = [OrderItemInline]
    list_select_related = ("buyer", "buyer__user")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        # Orders are created by checkout, which moves money. Making one by hand
        # would debit nobody and pay everybody.
        return False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("__str__", "courier", "status", "assigned_at", "delivered_at")
    list_filter = ("status", "created_at")
    search_fields = (
        "order_item__product__name",
        "order_item__order__reference",
        "courier__user__username",
    )
    autocomplete_fields = ("courier",)
    readonly_fields = ("order_item", "assigned_at", "picked_up_at", "delivered_at")
    list_select_related = ("order_item", "order_item__product", "courier", "courier__user")

    def has_add_permission(self, request):
        return False


@admin.register(CreditAccount)
class CreditAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__username", "user__email")
    # Read-only on purpose: editing this field directly would desynchronise the
    # balance from the ledger. Use an ADJUSTMENT transaction instead.
    readonly_fields = ("user", "balance", "created_at", "updated_at")
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "account", "kind", "amount", "balance_after", "memo")
    list_filter = ("kind", "created_at")
    search_fields = ("account__user__username", "memo", "order__reference")
    readonly_fields = (
        "account", "kind", "amount", "balance_after", "order", "memo", "created_at",
    )
    list_select_related = ("account", "account__user")
    date_hierarchy = "created_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # The ledger is append-only; an editable audit trail audits nothing.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "created_at")
    search_fields = ("user__username", "product__name")
    autocomplete_fields = ("user", "product")
    list_select_related = ("user", "product")
