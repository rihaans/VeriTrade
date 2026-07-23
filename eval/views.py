"""Evaluator workspace.

Every view here is behind ``@evaluator_required``. The previous versions had no
authentication at all: an anonymous request could claim a product and set its
evaluation score, which is the gate that decides what reaches the catalogue.
"""

import logging

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from events.decorators import evaluator_required
from events.forms import EvaluationForm, EvaluationJobFilterForm
from events.models import EvaluationJob, Product
from events.services import evaluation

logger = logging.getLogger("veritrade.evaluation")

PAGE_SIZE = 12


def _open_job(profile):
    """The evaluator's in-progress job, if any."""
    return (
        EvaluationJob.objects.filter(
            evaluator=profile, status=EvaluationJob.Status.CLAIMED
        )
        .select_related("product", "product__seller")
        .prefetch_related("product__images")
        .first()
    )


@evaluator_required
def dashboard(request):
    """Current job, queue size, and the evaluator's running totals."""
    completed = EvaluationJob.objects.filter(
        evaluator=request.profile, status=EvaluationJob.Status.COMPLETED
    )
    stats = completed.aggregate(total=Count("pk"), average=Avg("score"))

    return render(
        request,
        "evaluation/dashboard.html",
        {
            "page_title": "Evaluator dashboard",
            "current_job": _open_job(request.profile),
            "queue_size": Product.objects.awaiting_evaluation().count(),
            "completed_count": stats["total"] or 0,
            "average_score": stats["average"],
        },
    )


@evaluator_required
def queue(request):
    """Products waiting to be evaluated."""
    form = EvaluationJobFilterForm(request.GET or None)
    products = (
        Product.objects.awaiting_evaluation()
        .select_related("seller", "seller__user")
        .prefetch_related("images")
        .order_by("created_at")
    )

    if form.is_valid() and form.cleaned_data.get("category"):
        products = products.filter(category=form.cleaned_data["category"])

    paginator = Paginator(products, PAGE_SIZE)

    return render(
        request,
        "evaluation/queue.html",
        {
            "page_title": "Evaluation queue",
            "filter_form": form,
            "page_obj": paginator.get_page(request.GET.get("page")),
            "current_job": _open_job(request.profile),
        },
    )


@evaluator_required
@require_POST
def claim(request, pk):
    try:
        evaluation.claim_product_for_evaluation(request.profile, pk)
    except evaluation.EvaluationError as exc:
        messages.error(request, str(exc))
        return redirect("evaluation:queue")

    messages.success(request, "Product claimed. It is now assigned to you.")
    return redirect("evaluation:current")


@evaluator_required
def current(request):
    """The product in the evaluator's hands, plus the scoring form."""
    job = _open_job(request.profile)
    return render(
        request,
        "evaluation/current.html",
        {
            "page_title": "Current evaluation",
            "job": job,
            "form": EvaluationForm(),
            "pass_mark": evaluation.PASS_MARK,
        },
    )


@evaluator_required
@require_POST
def submit(request):
    """Record the verdict, which lists or rejects the product."""
    form = EvaluationForm(request.POST)
    if not form.is_valid():
        job = _open_job(request.profile)
        messages.error(request, "Check the score and try again.")
        return render(
            request,
            "evaluation/current.html",
            {
                "page_title": "Current evaluation",
                "job": job,
                "form": form,
                "pass_mark": evaluation.PASS_MARK,
            },
            status=400,
        )

    try:
        job = evaluation.submit_evaluation(
            request.profile,
            score=form.cleaned_data["score"],
            notes=form.cleaned_data.get("notes", ""),
        )
    except evaluation.EvaluationError as exc:
        messages.error(request, str(exc))
        return redirect("evaluation:current")

    outcome = (
        "listed on the marketplace"
        if job.score >= evaluation.PASS_MARK
        else "rejected"
    )
    messages.success(request, f"Evaluation saved. The product was {outcome}.")
    return redirect("evaluation:queue")


@evaluator_required
@require_POST
def release(request):
    """Hand the product back to the queue without scoring it."""
    try:
        evaluation.release_evaluation(request.profile)
    except evaluation.EvaluationError as exc:
        messages.error(request, str(exc))
    else:
        messages.info(request, "Product returned to the queue.")
    return redirect("evaluation:queue")


@evaluator_required
def history(request):
    """Everything this evaluator has assessed."""
    jobs = (
        EvaluationJob.objects.filter(evaluator=request.profile)
        .exclude(status=EvaluationJob.Status.CLAIMED)
        .select_related("product")
        .order_by("-completed_at", "-claimed_at")
    )
    paginator = Paginator(jobs, PAGE_SIZE)

    return render(
        request,
        "evaluation/history.html",
        {
            "page_title": "Evaluation history",
            "page_obj": paginator.get_page(request.GET.get("page")),
            "pass_mark": evaluation.PASS_MARK,
        },
    )
