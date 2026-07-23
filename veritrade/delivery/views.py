"""Courier workspace.

Addresses come from the buyer's and seller's stored profiles. The previous
implementation read ``product_seller.address`` and ``product.product_buyer``,
neither of which exists on any model, so this screen raised ``AttributeError``
on every request. It also called a live geocoding API inline on page load,
which blocked the response on a third-party service.
"""

import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from events.decorators import courier_required
from events.models import Delivery
from events.services import logistics

logger = logging.getLogger("veritrade.logistics")

PAGE_SIZE = 12


def _open_delivery(profile):
    """The courier's in-progress delivery, if any."""
    return (
        Delivery.objects.filter(courier=profile, status__in=Delivery.OPEN_STATUSES)
        .select_related(
            "order_item",
            "order_item__product",
            "order_item__seller",
            "order_item__seller__user",
            "order_item__order",
            "order_item__order__buyer",
            "order_item__order__buyer__user",
        )
        .first()
    )


@courier_required
def dashboard(request):
    completed = Delivery.objects.filter(
        courier=request.profile, status=Delivery.Status.DELIVERED
    ).aggregate(total=Count("pk"))

    return render(
        request,
        "logistics/dashboard.html",
        {
            "page_title": "Delivery dashboard",
            "current_delivery": _open_delivery(request.profile),
            "queue_size": logistics.available_deliveries().count(),
            "completed_count": completed["total"] or 0,
        },
    )


@courier_required
def queue(request):
    """Deliveries waiting for a courier."""
    paginator = Paginator(logistics.available_deliveries(), PAGE_SIZE)
    return render(
        request,
        "logistics/queue.html",
        {
            "page_title": "Available deliveries",
            "page_obj": paginator.get_page(request.GET.get("page")),
            "current_delivery": _open_delivery(request.profile),
        },
    )


@courier_required
@require_POST
def claim(request, pk):
    try:
        logistics.claim_delivery(request.profile, pk)
    except logistics.DeliveryError as exc:
        messages.error(request, str(exc))
        return redirect("logistics:queue")

    messages.success(request, "Delivery assigned to you.")
    return redirect("logistics:current")


@courier_required
def current(request):
    """The active job, with collection and drop-off addresses."""
    delivery = _open_delivery(request.profile)
    return render(
        request,
        "logistics/current.html",
        {
            "page_title": "Current delivery",
            "delivery": delivery,
            "Status": Delivery.Status,
        },
    )


@courier_required
@require_POST
def pick_up(request):
    try:
        logistics.mark_picked_up(request.profile)
    except logistics.DeliveryError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Marked as picked up.")
    return redirect("logistics:current")


@courier_required
@require_POST
def deliver(request):
    """Complete the delivery, which releases payment to the seller."""
    try:
        logistics.mark_delivered(request.profile)
    except logistics.DeliveryError as exc:
        messages.error(request, str(exc))
        return redirect("logistics:current")

    messages.success(request, "Delivery completed and the seller has been paid.")
    return redirect("logistics:queue")


@courier_required
def history(request):
    deliveries = (
        Delivery.objects.filter(courier=request.profile)
        .exclude(status__in=Delivery.OPEN_STATUSES)
        .select_related("order_item", "order_item__product", "order_item__order")
        .order_by("-delivered_at", "-created_at")
    )
    paginator = Paginator(deliveries, PAGE_SIZE)

    return render(
        request,
        "logistics/history.html",
        {
            "page_title": "Delivery history",
            "page_obj": paginator.get_page(request.GET.get("page")),
        },
    )
