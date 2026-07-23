"""Marketplace routes, mounted at /market/ under the ``marketplace`` namespace.

State-changing routes are POST-only (enforced by ``require_POST`` on the view),
so no purchase, cart change, or deletion can be triggered by a link, an image
tag, or a prefetch.
"""

from django.urls import path

from .views import marketplace

app_name = "marketplace"

urlpatterns = [
    path("", marketplace.home, name="home"),
    path("product/<int:pk>/", marketplace.product_detail, name="product_detail"),

    path("sell/", marketplace.sell, name="sell"),
    path("listings/", marketplace.my_listings, name="my_listings"),
    path("listings/<int:pk>/delete/", marketplace.delete_listing, name="delete_listing"),

    path("cart/", marketplace.cart, name="cart"),
    path("cart/add/<int:pk>/", marketplace.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:pk>/", marketplace.remove_from_cart, name="remove_from_cart"),
    path("cart/checkout/", marketplace.checkout, name="checkout"),
    path("product/<int:pk>/buy/", marketplace.buy_now, name="buy_now"),

    path("orders/", marketplace.orders, name="orders"),
    path("orders/<str:reference>/", marketplace.order_detail, name="order_detail"),
    path("orders/<str:reference>/cancel/", marketplace.cancel_order, name="cancel_order"),
]
