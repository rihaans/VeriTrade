"""Public marketing pages."""

from django.db.models import Avg, Count
from django.shortcuts import redirect, render

from .models import Delivery, Product, ProductStatus

FEATURED_LIMIT = 8


def index(request):
    """The landing page.

    A signed-in user has no reason to see the pitch, so they go straight to
    their own dashboard.
    """
    if request.user.is_authenticated:
        return redirect("accounts:post_login")

    featured = Product.objects.for_catalogue().order_by(
        "-evaluation_score", "-created_at"
    )[:FEATURED_LIMIT]

    listed = Product.objects.listed()
    stats = {
        "listings": listed.count(),
        "categories": listed.values("category").distinct().count(),
        "average_score": listed.aggregate(score=Avg("evaluation_score"))["score"],
        "delivered": Delivery.objects.filter(
            status=Delivery.Status.DELIVERED
        ).aggregate(total=Count("pk"))["total"],
    }

    # Category tiles, each with a live count, skipping anything empty.
    categories = [
        {
            "code": row["category"],
            "label": dict(Product._meta.get_field("category").choices)[row["category"]],
            "count": row["total"],
        }
        for row in listed.values("category")
        .annotate(total=Count("pk"))
        .order_by("-total")
    ]

    return render(
        request,
        "marketing/index.html",
        {
            "page_title": "Verified second-hand electronics",
            "featured": featured,
            "stats": stats,
            "categories": categories,
        },
    )


def how_it_works(request):
    return render(
        request,
        "marketing/how_it_works.html",
        {"page_title": "How VeriTrade works"},
    )
