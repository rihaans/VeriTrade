"""Evaluation workflow.

An evaluator claims a product awaiting assessment, scores it, and the product
either becomes listed or is rejected. A claim is exclusive: the unique
constraints on :class:`EvaluationJob` mean the database refuses a second open
job for the same product or the same evaluator, so two evaluators racing for
one item cannot both believe they own it.
"""

import logging

from django.db import IntegrityError, transaction

from ..models import EvaluationJob, Product, ProductStatus, Role

logger = logging.getLogger("veritrade.evaluation")

# Below this score the item is not fit to sell on.
PASS_MARK = 40


class EvaluationError(Exception):
    """Raised when an evaluation action is not permitted."""


@transaction.atomic
def claim_product_for_evaluation(evaluator_profile, product_id):
    """Assign a pending product to ``evaluator_profile``.

    Returns the created :class:`EvaluationJob`.
    """
    if evaluator_profile.role != Role.EVALUATOR:
        raise EvaluationError("Only evaluators can claim evaluation jobs.")

    if EvaluationJob.objects.filter(
        evaluator=evaluator_profile, status=EvaluationJob.Status.CLAIMED
    ).exists():
        raise EvaluationError("Finish your current evaluation before taking another.")

    try:
        product = Product.objects.select_for_update().get(pk=product_id)
    except Product.DoesNotExist as exc:
        raise EvaluationError("That product no longer exists.") from exc

    if product.status != ProductStatus.PENDING_EVALUATION:
        raise EvaluationError("That product is not waiting for evaluation.")

    try:
        job = EvaluationJob.objects.create(
            product=product, evaluator=evaluator_profile
        )
    except IntegrityError as exc:
        # Lost the race against another evaluator claiming the same product.
        raise EvaluationError("Another evaluator just claimed that product.") from exc

    product.status = ProductStatus.IN_EVALUATION
    product.save(update_fields=["status", "updated_at"])

    logger.info(
        "evaluation claimed job=%s product=%s evaluator=%s",
        job.pk, product.pk, evaluator_profile.pk,
    )
    return job


@transaction.atomic
def submit_evaluation(evaluator_profile, score, notes=""):
    """Complete the evaluator's open job with ``score`` (0-100).

    A score at or above :data:`PASS_MARK` lists the product; below it the
    product is rejected and never becomes purchasable.
    """
    if not 0 <= score <= 100:
        raise EvaluationError("Score must be between 0 and 100.")

    job = (
        EvaluationJob.objects.select_for_update()
        .filter(evaluator=evaluator_profile, status=EvaluationJob.Status.CLAIMED)
        .select_related("product")
        .first()
    )
    if job is None:
        raise EvaluationError("You have no evaluation in progress.")

    product = Product.objects.select_for_update().get(pk=job.product_id)
    job.complete(score=score, notes=notes)

    from django.utils import timezone

    product.evaluation_score = score
    product.evaluation_notes = notes
    product.evaluated_at = timezone.now()
    product.status = (
        ProductStatus.LISTED if score >= PASS_MARK else ProductStatus.REJECTED
    )
    product.save(
        update_fields=[
            "evaluation_score",
            "evaluation_notes",
            "evaluated_at",
            "status",
            "updated_at",
        ]
    )

    logger.info(
        "evaluation submitted job=%s product=%s score=%s outcome=%s",
        job.pk, product.pk, score, product.status,
    )
    return job


@transaction.atomic
def release_evaluation(evaluator_profile):
    """Give up the open job, returning the product to the pending queue."""
    job = (
        EvaluationJob.objects.select_for_update()
        .filter(evaluator=evaluator_profile, status=EvaluationJob.Status.CLAIMED)
        .first()
    )
    if job is None:
        raise EvaluationError("You have no evaluation in progress.")

    job.status = EvaluationJob.Status.ABANDONED
    job.save(update_fields=["status"])

    product = Product.objects.select_for_update().get(pk=job.product_id)
    product.status = ProductStatus.PENDING_EVALUATION
    product.save(update_fields=["status", "updated_at"])

    logger.info("evaluation released job=%s product=%s", job.pk, product.pk)
    return job
