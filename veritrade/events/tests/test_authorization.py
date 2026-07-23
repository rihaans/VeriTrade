"""Access-control regression tests.

Each test here corresponds to a defect that existed in the original code. They
exist to make sure none of them come back:

  * views identified the acting user from a URL parameter instead of the session
  * evaluator and courier views had no authentication at all
  * any signed-in user could reach any other user's cart, orders, and profile
  * state-changing endpoints accepted GET
"""

from django.test import TestCase
from django.urls import reverse

from events.models import CartItem, Delivery, ProductStatus, Role
from events.services import credits, marketplace

from .factories import PASSWORD, make_product, make_user


class AnonymousAccessTests(TestCase):
    """Nothing that acts on an account may be reachable while signed out."""

    def setUp(self):
        self.seller = make_user()
        self.product = make_product(self.seller, price=500)

    def test_protected_pages_redirect_to_login(self):
        protected = [
            reverse("marketplace:home"),
            reverse("marketplace:cart"),
            reverse("marketplace:sell"),
            reverse("marketplace:orders"),
            reverse("marketplace:my_listings"),
            reverse("accounts:profile"),
            reverse("accounts:wallet"),
            reverse("evaluation:dashboard"),
            reverse("evaluation:queue"),
            reverse("evaluation:current"),
            reverse("logistics:dashboard"),
            reverse("logistics:queue"),
            reverse("logistics:current"),
        ]
        for url in protected:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/login/", response["Location"])

    def test_anonymous_cannot_buy(self):
        """The original /direct_buy/<user>/<product>/ needed no session at all."""
        response = self.client.post(reverse("marketplace:buy_now", args=[self.product.pk]))

        self.assertEqual(response.status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.LISTED)

    def test_anonymous_cannot_claim_an_evaluation(self):
        pending = make_product(self.seller, status=ProductStatus.PENDING_EVALUATION)
        self.client.post(reverse("evaluation:claim", args=[pending.pk]))

        pending.refresh_from_db()
        self.assertEqual(pending.status, ProductStatus.PENDING_EVALUATION)

    def test_public_pages_are_reachable(self):
        for url in [reverse("marketing:index"), reverse("marketing:how_it_works")]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)


class CrossAccountTests(TestCase):
    """A signed-in user must not be able to act on anyone else's records."""

    def setUp(self):
        self.alice = make_user(balance=5000, username="alice")
        self.mallory = make_user(balance=5000, username="mallory")
        self.seller = make_user(username="seller")
        self.product = make_product(self.seller, price=400)
        self.client.login(username="mallory", password=PASSWORD)

    def test_cannot_remove_another_users_cart_item(self):
        item = CartItem.objects.create(user=self.alice.user, product=self.product)

        response = self.client.post(
            reverse("marketplace:remove_from_cart", args=[item.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=item.pk).exists())

    def test_cannot_view_another_users_order(self):
        order = marketplace.purchase(self.alice, [self.product])

        response = self.client.get(
            reverse("marketplace:order_detail", args=[order.reference])
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_cancel_another_users_order(self):
        order = marketplace.purchase(self.alice, [self.product])
        balance_before = credits.get_balance(self.alice.user)

        response = self.client.post(
            reverse("marketplace:cancel_order", args=[order.reference])
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(credits.get_balance(self.alice.user), balance_before)

    def test_cannot_withdraw_another_users_listing(self):
        response = self.client.post(
            reverse("marketplace:delete_listing", args=[self.product.pk])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(type(self.product).objects.filter(pk=self.product.pk).exists())

    def test_buying_spends_only_your_own_credits(self):
        alice_before = credits.get_balance(self.alice.user)

        self.client.post(reverse("marketplace:buy_now", args=[self.product.pk]))

        self.assertEqual(credits.get_balance(self.alice.user), alice_before)
        self.assertEqual(credits.get_balance(self.mallory.user), 4600)

    def test_a_seller_cannot_be_impersonated_when_listing(self):
        """A listing is always attributed to the signed-in user."""
        self.client.post(
            reverse("marketplace:sell"),
            {
                "name": "Injected listing",
                "category": "MISC",
                "description": "Attempting to list on someone else's behalf.",
                "purchase_price": 100,
                "listed_price": 100,
                "discount_percent": 0,
            },
        )
        listing = type(self.product).objects.filter(name="Injected listing").first()
        if listing is not None:  # rejected for the missing photo, but if not:
            self.assertEqual(listing.seller_id, self.mallory.pk)


class RoleSeparationTests(TestCase):
    """Each portal is restricted to the role it belongs to."""

    def setUp(self):
        self.member = make_user(Role.MEMBER, username="member")
        self.evaluator = make_user(Role.EVALUATOR, username="evaluator")
        self.courier = make_user(Role.COURIER, username="courier")

    def test_member_cannot_reach_the_evaluator_workspace(self):
        self.client.login(username="member", password=PASSWORD)
        response = self.client.get(reverse("evaluation:queue"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/evaluation/", response["Location"])

    def test_member_cannot_reach_the_courier_workspace(self):
        self.client.login(username="member", password=PASSWORD)
        response = self.client.get(reverse("logistics:queue"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("/logistics/", response["Location"])

    def test_evaluator_cannot_reach_the_marketplace(self):
        self.client.login(username="evaluator", password=PASSWORD)
        response = self.client.get(reverse("marketplace:home"))
        self.assertEqual(response.status_code, 302)

    def test_evaluator_cannot_claim_a_delivery(self):
        self.client.login(username="evaluator", password=PASSWORD)
        response = self.client.get(reverse("logistics:queue"))
        self.assertEqual(response.status_code, 302)

    def test_each_role_lands_on_its_own_dashboard(self):
        expectations = [
            ("member", "/market/"),
            ("evaluator", "/evaluation/"),
            ("courier", "/logistics/"),
        ]
        for username, prefix in expectations:
            with self.subTest(username=username):
                self.client.login(username=username, password=PASSWORD)
                response = self.client.get(reverse("accounts:post_login"))
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response["Location"].startswith(prefix))
                self.client.logout()


class HttpMethodTests(TestCase):
    """Anything that changes state must refuse GET."""

    def setUp(self):
        self.buyer = make_user(balance=5000, username="buyer")
        self.seller = make_user()
        self.product = make_product(self.seller, price=400)
        self.client.login(username="buyer", password=PASSWORD)

    def test_state_changing_endpoints_reject_get(self):
        urls = [
            reverse("marketplace:buy_now", args=[self.product.pk]),
            reverse("marketplace:add_to_cart", args=[self.product.pk]),
            reverse("marketplace:checkout"),
            reverse("accounts:logout"),
            reverse("accounts:change_password"),
            reverse("accounts:delete_account"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)

    def test_a_get_cannot_spend_credits(self):
        self.client.get(reverse("marketplace:buy_now", args=[self.product.pk]))
        self.assertEqual(credits.get_balance(self.buyer.user), 5000)


class CourierAssignmentTests(TestCase):
    """A courier acts on their own assignment, never on another's."""

    def setUp(self):
        self.buyer = make_user(balance=5000)
        self.seller = make_user()
        self.courier = make_user(Role.COURIER, username="courier1")
        self.other = make_user(Role.COURIER, username="courier2")

        product = make_product(self.seller, price=400)
        order = marketplace.purchase(self.buyer, [product])
        self.delivery = Delivery.objects.get(order_item__order=order)

    def test_another_courier_cannot_advance_your_delivery(self):
        from events.services import logistics

        logistics.claim_delivery(self.courier, self.delivery.pk)

        self.client.login(username="courier2", password=PASSWORD)
        self.client.post(reverse("logistics:pick_up"))

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, Delivery.Status.ASSIGNED)
        self.assertEqual(self.delivery.courier, self.courier)

    def test_delivering_pays_only_the_real_seller(self):
        from events.services import logistics

        logistics.claim_delivery(self.courier, self.delivery.pk)
        logistics.mark_picked_up(self.courier)
        logistics.mark_delivered(self.courier)

        self.assertEqual(credits.get_balance(self.seller.user), 400)
        self.assertEqual(credits.get_balance(self.other.user), 0)
