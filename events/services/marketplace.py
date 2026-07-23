"""Checkout and order cancellation.

Money model: at checkout the buyer is debited immediately and the seller is
*not* yet paid. Those credits sit with the platform until the courier confirms
delivery, at which point ``logistics.mark_delivered`` pays the seller. That gap
is the escrow. Cancelling before delivery refunds the buyer and relists the
product.

The original implementation debited the buyer, never paid the seller, set
``product_sold = 0`` on a sale, and did all of it without a transaction.
"""

import logging

from django.db import transaction

from ..models import (
    CartItem,
    CreditTransaction,
    Delivery,
    Order,
    OrderItem,
    Product,
    ProductStatus,
)
from .credits import InsufficientCredits, deposit, withdraw

logger = logging.getLogger("veritrade.marketplace")


class CheckoutError(Exception):
    """Raised when an order cannot be placed."""


@transaction.atomic
def purchase(buyer_profile, products):
    """Buy every product in ``products`` as a single order.

    Returns the created :class:`Order`.

    Raises :class:`CheckoutError` if the basket is empty, contains something no
    longer for sale, or contains the buyer's own listing, and
    :class:`InsufficientCredits` if the balance will not cover the total.
    """
    product_ids = [p.pk for p in products]
    if not product_ids:
        raise CheckoutError("There is nothing to buy.")

    # Re-read under a lock. Between rendering the cart and submitting it, another
    # buyer may have taken the same item; the status check below is only
    # meaningful because the rows are locked first.
    locked = list(
        Product.objects.select_for_update()
        .select_related("seller")
        .filter(pk__in=product_ids)
    )
    if len(locked) != len(set(product_ids)):
        raise CheckoutError("One of those products no longer exists.")

    for product in locked:
        if product.status != ProductStatus.LISTED:
            raise CheckoutError(f"'{product.name}' is no longer available.")
        if product.seller_id == buyer_profile.pk:
            raise CheckoutError("You cannot buy your own listing.")

    total = sum(product.price for product in locked)

    order = Order.objects.create(buyer=buyer_profile, total_amount=total)

    # Debit first: if the balance is short this raises and the atomic block
    # rolls the order back, so no half-finished purchase is ever visible.
    withdraw(
        buyer_profile.user,
        total,
        kind=CreditTransaction.Kind.PURCHASE,
        memo=f"Order {order.reference}",
        order=order,
    )

    for product in locked:
        item = OrderItem.objects.create(
            order=order,
            product=product,
            seller=product.seller,
            unit_price=product.price,
        )
        Delivery.objects.create(order_item=item)

        product.status = ProductStatus.SOLD
        product.save(update_fields=["status", "updated_at"])

    # The bought items leave every cart they were sitting in, not just this
    # buyer's, since each listing is a single physical item.
    CartItem.objects.filter(product_id__in=product_ids).delete()

    logger.info(
        "order placed reference=%s buyer=%s items=%s total=%s",
        order.reference, buyer_profile.pk, len(locked), total,
    )
    return order


@transaction.atomic
def cancel_order(order, *, reason=""):
    """Refund the buyer and return every undelivered item to the catalogue.

    Items already delivered are left alone: that money has been paid to the
    seller and is not clawed back here.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status != Order.Status.PENDING:
        raise CheckoutError("Only an in-progress order can be cancelled.")

    refund_total = 0
    items = order.items.select_related("product", "delivery")

    for item in items:
        delivery = getattr(item, "delivery", None)
        if delivery and delivery.status == Delivery.Status.DELIVERED:
            continue

        if delivery:
            delivery.status = Delivery.Status.CANCELLED
            delivery.courier = None
            delivery.save(update_fields=["status", "courier", "updated_at"])

        product = item.product
        product.status = ProductStatus.LISTED
        product.save(update_fields=["status", "updated_at"])

        refund_total += item.unit_price

    if refund_total:
        deposit(
            order.buyer.user,
            refund_total,
            kind=CreditTransaction.Kind.REFUND,
            memo=f"Refund for order {order.reference}" + (f": {reason}" if reason else ""),
            order=order,
        )

    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])

    logger.info(
        "order cancelled reference=%s refunded=%s reason=%s",
        order.reference, refund_total, reason or "-",
    )
    return order


__all__ = ["CheckoutError", "InsufficientCredits", "cancel_order", "purchase"]
