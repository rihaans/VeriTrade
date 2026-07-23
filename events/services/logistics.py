"""Delivery workflow.

A courier claims an unassigned delivery, marks it picked up, then delivered.
Confirming delivery is the moment the seller is paid: it releases the escrow
created at checkout.

The original code listed products that had *not* been bought as available
delivery jobs, and created a second delivery row with null seller and buyer
foreign keys, which could not be saved.
"""

import logging

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import CreditTransaction, Delivery, Order, Role
from .credits import deposit

logger = logging.getLogger("veritrade.logistics")


class DeliveryError(Exception):
    """Raised when a delivery action is not permitted."""


def available_deliveries():
    """Deliveries waiting for a courier to pick them up."""
    return (
        Delivery.objects.filter(
            status=Delivery.Status.UNASSIGNED, courier__isnull=True
        )
        .select_related(
            "order_item",
            "order_item__product",
            "order_item__seller",
            "order_item__order",
            "order_item__order__buyer",
        )
        .order_by("created_at")
    )


@transaction.atomic
def claim_delivery(courier_profile, delivery_id):
    """Assign an unassigned delivery to ``courier_profile``."""
    if courier_profile.role != Role.COURIER:
        raise DeliveryError("Only delivery partners can claim deliveries.")

    if Delivery.objects.filter(
        courier=courier_profile, status__in=Delivery.OPEN_STATUSES
    ).exists():
        raise DeliveryError("Complete your current delivery before taking another.")

    try:
        delivery = Delivery.objects.select_for_update().get(pk=delivery_id)
    except Delivery.DoesNotExist as exc:
        raise DeliveryError("That delivery no longer exists.") from exc

    if delivery.status != Delivery.Status.UNASSIGNED or delivery.courier_id:
        raise DeliveryError("That delivery has already been taken.")

    delivery.courier = courier_profile
    delivery.status = Delivery.Status.ASSIGNED
    delivery.assigned_at = timezone.now()
    try:
        delivery.save(update_fields=["courier", "status", "assigned_at", "updated_at"])
    except IntegrityError as exc:
        raise DeliveryError("That delivery has already been taken.") from exc

    logger.info(
        "delivery claimed id=%s courier=%s", delivery.pk, courier_profile.pk
    )
    return delivery


def _open_delivery_for(courier_profile):
    return (
        Delivery.objects.select_for_update()
        .filter(courier=courier_profile, status__in=Delivery.OPEN_STATUSES)
        .select_related("order_item", "order_item__order", "order_item__seller")
        .first()
    )


@transaction.atomic
def mark_picked_up(courier_profile):
    """Record that the courier has collected the item from the seller."""
    delivery = _open_delivery_for(courier_profile)
    if delivery is None:
        raise DeliveryError("You have no delivery in progress.")
    if delivery.status != Delivery.Status.ASSIGNED:
        raise DeliveryError("That delivery has already been picked up.")

    delivery.status = Delivery.Status.PICKED_UP
    delivery.picked_up_at = timezone.now()
    delivery.save(update_fields=["status", "picked_up_at", "updated_at"])

    logger.info("delivery picked up id=%s", delivery.pk)
    return delivery


@transaction.atomic
def mark_delivered(courier_profile):
    """Complete the delivery and release the escrowed payment to the seller.

    This is the only place a seller is ever paid.
    """
    delivery = _open_delivery_for(courier_profile)
    if delivery is None:
        raise DeliveryError("You have no delivery in progress.")
    if delivery.status != Delivery.Status.PICKED_UP:
        raise DeliveryError("Mark the item as picked up before delivering it.")

    delivery.status = Delivery.Status.DELIVERED
    delivery.delivered_at = timezone.now()
    delivery.save(update_fields=["status", "delivered_at", "updated_at"])

    item = delivery.order_item
    deposit(
        item.seller.user,
        item.unit_price,
        kind=CreditTransaction.Kind.SALE,
        memo=f"Sale of {item.product.name} (order {item.order.reference})",
        order=item.order,
    )

    _complete_order_if_finished(item.order)

    logger.info(
        "delivery completed id=%s seller=%s paid=%s",
        delivery.pk, item.seller_id, item.unit_price,
    )
    return delivery


def _complete_order_if_finished(order):
    """Close the order once none of its deliveries are still open."""
    still_open = Delivery.objects.filter(
        order_item__order=order, status__in=Delivery.OPEN_STATUSES
    ).exists()
    if still_open:
        return

    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == Order.Status.PENDING:
        order.status = Order.Status.COMPLETED
        order.save(update_fields=["status", "updated_at"])
        logger.info("order completed reference=%s", order.reference)
