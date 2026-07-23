"""Evaluation and delivery lifecycles, including their exclusivity rules."""

from django.test import TestCase

from events.models import Delivery, EvaluationJob, ProductStatus, Role
from events.services import evaluation, logistics, marketplace

from .factories import make_product, make_user


class EvaluationTests(TestCase):
    def setUp(self):
        self.evaluator = make_user(Role.EVALUATOR)
        self.seller = make_user()
        self.product = make_product(
            self.seller, status=ProductStatus.PENDING_EVALUATION
        )

    def test_claim_assigns_the_product(self):
        job = evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.IN_EVALUATION)
        self.assertEqual(job.status, EvaluationJob.Status.CLAIMED)

    def test_a_passing_score_lists_the_product(self):
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)
        evaluation.submit_evaluation(self.evaluator, score=75, notes="Good order.")

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.LISTED)
        self.assertEqual(self.product.evaluation_score, 75)
        self.assertEqual(self.product.evaluation_notes, "Good order.")

    def test_a_failing_score_rejects_the_product(self):
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)
        evaluation.submit_evaluation(self.evaluator, score=evaluation.PASS_MARK - 1)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.REJECTED)

    def test_the_pass_mark_itself_passes(self):
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)
        evaluation.submit_evaluation(self.evaluator, score=evaluation.PASS_MARK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.LISTED)

    def test_an_evaluator_may_hold_only_one_job(self):
        second = make_product(self.seller, status=ProductStatus.PENDING_EVALUATION)
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)

        with self.assertRaises(evaluation.EvaluationError):
            evaluation.claim_product_for_evaluation(self.evaluator, second.pk)

    def test_two_evaluators_cannot_claim_the_same_product(self):
        other = make_user(Role.EVALUATOR)
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)

        with self.assertRaises(evaluation.EvaluationError):
            evaluation.claim_product_for_evaluation(other, self.product.pk)

    def test_a_non_evaluator_cannot_claim(self):
        member = make_user(Role.MEMBER)
        with self.assertRaises(evaluation.EvaluationError):
            evaluation.claim_product_for_evaluation(member, self.product.pk)

    def test_cannot_claim_a_product_that_is_not_pending(self):
        listed = make_product(self.seller, status=ProductStatus.LISTED)
        with self.assertRaises(evaluation.EvaluationError):
            evaluation.claim_product_for_evaluation(self.evaluator, listed.pk)

    def test_scores_outside_the_range_are_refused(self):
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)
        for score in (-1, 101):
            with self.assertRaises(evaluation.EvaluationError):
                evaluation.submit_evaluation(self.evaluator, score=score)

    def test_submitting_without_a_job_fails(self):
        with self.assertRaises(evaluation.EvaluationError):
            evaluation.submit_evaluation(self.evaluator, score=50)

    def test_release_returns_the_product_to_the_queue(self):
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)
        evaluation.release_evaluation(self.evaluator)

        self.product.refresh_from_db()
        self.assertEqual(self.product.status, ProductStatus.PENDING_EVALUATION)
        # And the evaluator is free to take another.
        evaluation.claim_product_for_evaluation(self.evaluator, self.product.pk)


class DeliveryTests(TestCase):
    def setUp(self):
        self.buyer = make_user(balance=5000)
        self.seller = make_user()
        self.courier = make_user(Role.COURIER)
        product = make_product(self.seller, price=900)
        self.order = marketplace.purchase(self.buyer, [product])
        self.delivery = Delivery.objects.get(order_item__order=self.order)

    def test_claim_assigns_the_courier(self):
        delivery = logistics.claim_delivery(self.courier, self.delivery.pk)
        self.assertEqual(delivery.status, Delivery.Status.ASSIGNED)
        self.assertEqual(delivery.courier, self.courier)

    def test_a_courier_may_hold_only_one_delivery(self):
        other_product = make_product(self.seller, price=300)
        other_order = marketplace.purchase(self.buyer, [other_product])
        other_delivery = Delivery.objects.get(order_item__order=other_order)

        logistics.claim_delivery(self.courier, self.delivery.pk)
        with self.assertRaises(logistics.DeliveryError):
            logistics.claim_delivery(self.courier, other_delivery.pk)

    def test_two_couriers_cannot_claim_the_same_delivery(self):
        other = make_user(Role.COURIER)
        logistics.claim_delivery(self.courier, self.delivery.pk)

        with self.assertRaises(logistics.DeliveryError):
            logistics.claim_delivery(other, self.delivery.pk)

    def test_a_non_courier_cannot_claim(self):
        member = make_user(Role.MEMBER)
        with self.assertRaises(logistics.DeliveryError):
            logistics.claim_delivery(member, self.delivery.pk)

    def test_the_lifecycle_must_run_in_order(self):
        logistics.claim_delivery(self.courier, self.delivery.pk)

        # Cannot deliver before picking up.
        with self.assertRaises(logistics.DeliveryError):
            logistics.mark_delivered(self.courier)

        logistics.mark_picked_up(self.courier)

        # Cannot pick up twice.
        with self.assertRaises(logistics.DeliveryError):
            logistics.mark_picked_up(self.courier)

        logistics.mark_delivered(self.courier)

    def test_available_queue_only_lists_unassigned_work(self):
        self.assertEqual(logistics.available_deliveries().count(), 1)
        logistics.claim_delivery(self.courier, self.delivery.pk)
        self.assertEqual(logistics.available_deliveries().count(), 0)

    def test_completing_a_delivery_frees_the_courier(self):
        logistics.claim_delivery(self.courier, self.delivery.pk)
        logistics.mark_picked_up(self.courier)
        logistics.mark_delivered(self.courier)

        another = make_product(self.seller, price=300)
        another_order = marketplace.purchase(self.buyer, [another])
        another_delivery = Delivery.objects.get(order_item__order=another_order)

        logistics.claim_delivery(self.courier, another_delivery.pk)
