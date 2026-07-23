"""Browsing, selling, the cart, checkout, and order history.

Every view acts on ``request.user``. None of them accept a user id in the URL,
which is what made the previous versions exploitable: ``/direct_buy/7/12/``
spent user 7's credits no matter who sent the request.
"""

import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from events.decorators import get_profile, member_required
from events.forms import CatalogueFilterForm, ProductForm
from events.models import (
    CartItem,
    Delivery,
    Order,
    OrderItem,
    Product,
    ProductStatus,
)
from events.services import credits, marketplace

logger = logging.getLogger("veritrade.marketplace")

PAGE_SIZE = 12


def _filtered_catalogue(request, exclude_profile=None):
    """Apply the search/filter/sort form to the listed-products queryset."""
    form = CatalogueFilterForm(request.GET or None)
    queryset = Product.objects.for_catalogue()

    if exclude_profile is not None:
        # You cannot buy your own listing, so it does not belong in the grid.
        queryset = queryset.exclude(seller=exclude_profile)

    if form.is_valid():
        query = form.cleaned_data.get("q")
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )
        category = form.cleaned_data.get("category")
        if category:
            queryset = queryset.filter(category=category)
        sort = form.cleaned_data.get("sort")
        if sort:
            queryset = queryset.order_by(sort)

    return form, queryset


def _paginate(request, queryset):
    paginator = Paginator(queryset, PAGE_SIZE)
    return paginator.get_page(request.GET.get("page"))


@member_required
def home(request):
    """The buyer's catalogue."""
    profile = request.profile
    form, queryset = _filtered_catalogue(request, exclude_profile=profile)

    return render(
        request,
        "marketplace/home.html",
        {
            "page_title": "Browse",
            "filter_form": form,
            "page_obj": _paginate(request, queryset),
            "balance": credits.get_balance(request.user),
        },
    )


def product_detail(request, pk):
    """A single listing. Public, so a shared link works before signing in."""
    product = get_object_or_404(
        Product.objects.select_related("seller", "seller__user").prefetch_related(
            "images"
        ),
        pk=pk,
    )

    viewer = get_profile(request.user) if request.user.is_authenticated else None
    is_own_listing = viewer is not None and product.seller_id == viewer.pk

    # An unlisted product is only visible to the person selling it.
    if product.status != ProductStatus.LISTED and not is_own_listing:
        if not (request.user.is_authenticated and request.user.is_staff):
            raise Http404("No product matches the given query.")

    in_cart = (
        viewer is not None
        and CartItem.objects.filter(user=request.user, product=product).exists()
    )

    return render(
        request,
        "marketplace/product_detail.html",
        {
            "page_title": product.name,
            "product": product,
            "is_own_listing": is_own_listing,
            "in_cart": in_cart,
            "balance": credits.get_balance(request.user)
            if request.user.is_authenticated
            else 0,
        },
    )


@member_required
def sell(request):
    """Create a listing. It enters the evaluation queue, not the catalogue."""
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.profile
            product.status = ProductStatus.PENDING_EVALUATION
            product.save()
            form.save_images(product)

            logger.info(
                "listing created product=%s seller=%s", product.pk, request.profile.pk
            )
            messages.success(
                request,
                f"'{product.name}' has been submitted and is queued for evaluation.",
            )
            return redirect("marketplace:my_listings")
    else:
        form = ProductForm()

    return render(
        request,
        "marketplace/sell.html",
        {"page_title": "Sell an item", "form": form},
    )


@member_required
def my_listings(request):
    """Everything the signed-in user has listed, with its current status."""
    products = (
        Product.objects.filter(seller=request.profile)
        .prefetch_related("images")
        .order_by("-created_at")
    )

    sales = (
        OrderItem.objects.filter(seller=request.profile)
        .select_related("product", "order", "order__buyer", "order__buyer__user", "delivery")
        .order_by("-order__created_at")
    )

    earned = (
        OrderItem.objects.filter(
            seller=request.profile, delivery__status=Delivery.Status.DELIVERED
        ).aggregate(total=Sum("unit_price"))["total"]
        or 0
    )
    pending = (
        OrderItem.objects.filter(
            seller=request.profile, delivery__status__in=Delivery.OPEN_STATUSES
        ).aggregate(total=Sum("unit_price"))["total"]
        or 0
    )

    return render(
        request,
        "marketplace/my_listings.html",
        {
            "page_title": "Your listings",
            "page_obj": _paginate(request, products),
            "sales": sales,
            "earned": earned,
            "pending": pending,
        },
    )


@member_required
@require_POST
def delete_listing(request, pk):
    """Withdraw a listing that has not been sold."""
    product = get_object_or_404(Product, pk=pk, seller=request.profile)
    if product.status == ProductStatus.SOLD:
        messages.error(request, "A sold item cannot be withdrawn.")
        return redirect("marketplace:my_listings")

    name = product.name
    product.delete()
    messages.success(request, f"'{name}' has been withdrawn.")
    return redirect("marketplace:my_listings")


@member_required
def cart(request):
    items = (
        CartItem.objects.filter(user=request.user)
        .select_related("product", "product__seller")
        .prefetch_related("product__images")
    )

    # A listing may have sold since it was added; show it but block checkout.
    available = [item for item in items if item.product.is_purchasable]
    unavailable = [item for item in items if not item.product.is_purchasable]
    total = sum(item.product.price for item in available)
    balance = credits.get_balance(request.user)

    return render(
        request,
        "marketplace/cart.html",
        {
            "page_title": "Your cart",
            "available": available,
            "unavailable": unavailable,
            "total": total,
            "balance": balance,
            "shortfall": max(0, total - balance),
        },
    )


@member_required
@require_POST
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if product.seller_id == request.profile.pk:
        messages.error(request, "That is your own listing.")
    elif not product.is_purchasable:
        messages.error(request, "That item is no longer available.")
    else:
        _, created = CartItem.objects.get_or_create(
            user=request.user, product=product
        )
        messages.success(
            request,
            f"'{product.name}' added to your cart."
            if created
            else f"'{product.name}' is already in your cart.",
        )

    return redirect(request.POST.get("next") or "marketplace:cart")


@member_required
@require_POST
def remove_from_cart(request, pk):
    """Remove one item. Scoped to the signed-in user's own cart."""
    item = get_object_or_404(CartItem, pk=pk, user=request.user)
    name = item.product.name
    item.delete()
    messages.success(request, f"'{name}' removed from your cart.")
    return redirect("marketplace:cart")


@member_required
@require_POST
def checkout(request):
    """Buy everything purchasable in the cart as one order."""
    items = CartItem.objects.filter(user=request.user).select_related("product")
    products = [item.product for item in items if item.product.is_purchasable]

    if not products:
        messages.error(request, "There is nothing available to buy in your cart.")
        return redirect("marketplace:cart")

    return _place_order(request, products, back="marketplace:cart")


@member_required
@require_POST
def buy_now(request, pk):
    """Buy a single listing without going through the cart."""
    product = get_object_or_404(Product, pk=pk)
    return _place_order(
        request, [product], back="marketplace:product_detail", back_args=[pk]
    )


def _place_order(request, products, *, back, back_args=None):
    """Run a purchase and translate any failure into a message."""
    try:
        order = marketplace.purchase(request.profile, products)
    except credits.InsufficientCredits as exc:
        messages.error(
            request,
            f"You need {exc.required} credits but have {exc.available}. "
            "Top up and try again.",
        )
        return redirect("accounts:wallet")
    except marketplace.CheckoutError as exc:
        messages.error(request, str(exc))
        return redirect(back, *(back_args or []))

    messages.success(
        request,
        f"Order {order.reference} placed. A courier will collect it shortly.",
    )
    return redirect("marketplace:order_detail", reference=order.reference)


@member_required
def orders(request):
    """The buyer's order history."""
    queryset = (
        Order.objects.filter(buyer=request.profile)
        .annotate(item_count=Count("items"))
        .order_by("-created_at")
    )
    return render(
        request,
        "marketplace/orders.html",
        {"page_title": "Your orders", "page_obj": _paginate(request, queryset)},
    )


@member_required
def order_detail(request, reference):
    order = get_object_or_404(
        Order.objects.prefetch_related(
            "items__product__images", "items__seller__user", "items__delivery"
        ),
        reference=reference,
        buyer=request.profile,  # Scoping here is what prevents reading others' orders.
    )
    return render(
        request,
        "marketplace/order_detail.html",
        {"page_title": f"Order {order.reference}", "order": order},
    )


@member_required
@require_POST
def cancel_order(request, reference):
    order = get_object_or_404(Order, reference=reference, buyer=request.profile)
    try:
        marketplace.cancel_order(order, reason="Cancelled by buyer")
    except marketplace.CheckoutError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request, f"Order {order.reference} cancelled and refunded."
        )
    return redirect("marketplace:order_detail", reference=reference)
