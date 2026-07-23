"""Checkout, escrow, payout, and cancellation."""

from django.test import TestCase

from events.models import (
    CartItem,
    CreditTransaction,
    Delivery,
    Order,
    ProductStatus,
    Role,
)
from events.services import credits, logistics, marketplace

from .factories import make_product, make_user


class PurchaseTests(TestCase):
    def setUp(self):
        self.buyer = make_user(balance=5000)
        self.seller = make_user()
        self.product = make_product(self.seller, price=1200)

    def test_purchase_debits_buyer_and_marks_product_sold(self):
        order = marketplace.purchase(self.buyer, [self.product])

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.SOLD)
        self.assertEqual(credits.get_balance(self.buyer.user), 3800)
        self.assertEqual(order.total_amount, 1200)
        self.assertEqual(order.items.count(), 1)

    def test_seller_is_not_paid_until_delivery(self):
        """The escrow gap: money leaves the buyer but does not arrive yet."""
        marketplace.purchase(self.buyer, [self.product])
        self.assertEqual(credits.get_balance(self.seller.user), 0)

    def test_purchase_creates_an_unassigned_delivery(self):
        order = marketplace.purchase(self.buyer, [self.product])
        delivery = Delivery.objects.get(order_item__order=order)
        self.assertEqual(delivery.status, Delivery.Status.UNASSIGNED)
        self.assertIsNone(delivery.courier)

    def test_cannot_buy_without_enough_credits(self):
        expensive = make_product(self.seller, price=99999)

        with self.assertRaises(credits.InsufficientCredits):
            marketplace.purchase(self.buyer, [expensive])

        # The whole transaction rolls back: no order, no status change.
        expensive.refresh_from_db()
        self.assertEqual(expensive.status, ProductStatus.LISTED)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(credits.get_balance(self.buyer.user), 5000)

    def test_cannot_buy_your_own_listing(self):
        own = make_product(self.buyer, price=100)
        with self.assertRaises(marketplace.CheckoutError):
            marketplace.purchase(self.buyer, [own])

    def test_cannot_buy_an_unlisted_product(self):
        pending = make_product(
            self.seller, price=100, status=ProductStatus.PENDING_EVALUATION
        )
        with self.assertRaises(marketplace.CheckoutError):
            marketplace.purchase(self.buyer, [pending])

    def test_cannot_buy_the_same_product_twice(self):
        marketplace.purchase(self.buyer, [self.product])
        second = make_user(balance=5000)

        with self.assertRaises(marketplace.CheckoutError):
            marketplace.purchase(second, [self.product])

    def test_empty_basket_is_refused(self):
        with self.assertRaises(marketplace.CheckoutError):
            marketplace.purchase(self.buyer, [])

    def test_checkout_clears_the_product_from_every_cart(self):
        """Each listing is one physical item, so it leaves other carts too."""
        other = make_user(balance=5000)
        CartItem.objects.create(user=self.buyer.user, product=self.product)
        CartItem.objects.create(user=other.user, product=self.product)

        marketplace.purchase(self.buyer, [self.product])

        self.assertEqual(CartItem.objects.filter(product=self.product).count(), 0)

    def test_multi_item_order_totals_correctly(self):
        second = make_product(self.seller, price=800)
        order = marketplace.purchase(self.buyer, [self.product, second])

        self.assertEqual(order.total_amount, 2000)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(credits.get_balance(self.buyer.user), 3000)

    def test_discount_is_applied_to_the_charged_price(self):
        discounted = make_product(self.seller, price=1000, discount_percent=25)
        order = marketplace.purchase(self.buyer, [discounted])

        self.assertEqual(order.total_amount, 750)
        self.assertEqual(credits.get_balance(self.buyer.user), 4250)


class PayoutTests(TestCase):
    def setUp(self):
        self.buyer = make_user(balance=5000)
        self.seller = make_user()
        self.courier = make_user(Role.COURIER)
        self.product = make_product(self.seller, price=1200)
        self.order = marketplace.purchase(self.buyer, [self.product])
        self.delivery = Delivery.objects.get(order_item__order=self.order)

    def _deliver(self):
        logistics.claim_delivery(self.courier, self.delivery.pk)
        logistics.mark_picked_up(self.courier)
        return logistics.mark_delivered(self.courier)

    def test_delivery_pays_the_seller(self):
        self._deliver()
        self.assertEqual(credits.get_balance(self.seller.user), 1200)

    def test_delivery_completes_the_order(self):
        self._deliver()
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.COMPLETED)

    def test_payout_is_recorded_as_a_sale_in_the_ledger(self):
        self._deliver()
        entry = CreditTransaction.objects.get(
            account__user=self.seller.user, kind=CreditTransaction.Kind.SALE
        )
        self.assertEqual(entry.amount, 1200)

    def test_credits_are_conserved_across_the_whole_lifecycle(self):
        """Nothing is created or destroyed between checkout and payout."""
        before = (
            credits.get_balance(self.buyer.user)
            + credits.get_balance(self.seller.user)
        )
        self._deliver()
        after = (
            credits.get_balance(self.buyer.user)
            + credits.get_balance(self.seller.user)
        )
        self.assertEqual(before + 1200, after)  # 1200 released from escrow


class CancellationTests(TestCase):
    def setUp(self):
        self.buyer = make_user(balance=5000)
        self.seller = make_user()
        self.product = make_product(self.seller, price=1200)
        self.order = marketplace.purchase(self.buyer, [self.product])

    def test_cancel_refunds_the_buyer_in_full(self):
        marketplace.cancel_order(self.order)
        self.assertEqual(credits.get_balance(self.buyer.user), 5000)

    def test_cancel_returns_the_product_to_the_catalogue(self):
        marketplace.cancel_order(self.order)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.LISTED)

    def test_cancel_cancels_the_delivery(self):
        marketplace.cancel_order(self.order)
        delivery = Delivery.objects.get(order_item__order=self.order)
        self.assertEqual(delivery.status, Delivery.Status.CANCELLED)

    def test_cannot_cancel_twice(self):
        marketplace.cancel_order(self.order)
        with self.assertRaises(marketplace.CheckoutError):
            marketplace.cancel_order(self.order)

    def test_delivered_items_are_not_refunded(self):
        courier = make_user(Role.COURIER)
        delivery = Delivery.objects.get(order_item__order=self.order)
        logistics.claim_delivery(courier, delivery.pk)
        logistics.mark_picked_up(courier)
        logistics.mark_delivered(courier)

        # The order auto-completed on delivery, so it can no longer be cancelled.
        self.order.refresh_from_db()
        with self.assertRaises(marketplace.CheckoutError):
            marketplace.cancel_order(self.order)
        self.assertEqual(credits.get_balance(self.seller.user), 1200)
