"""Business logic.

Views in this project do not talk to the ORM to change state. They validate
input with a form, call one of these functions, and render the result. Every
function here is responsible for its own atomicity and its own invariants, so
the same rules hold whether the caller is a view, the admin, a management
command, or a test.
"""

from .credits import InsufficientCredits, deposit, get_balance, top_up, withdraw
from .evaluation import (
    EvaluationError,
    claim_product_for_evaluation,
    release_evaluation,
    submit_evaluation,
)
from .logistics import (
    DeliveryError,
    claim_delivery,
    mark_delivered,
    mark_picked_up,
)
from .marketplace import CheckoutError, cancel_order, purchase

__all__ = [
    "CheckoutError",
    "DeliveryError",
    "EvaluationError",
    "InsufficientCredits",
    "cancel_order",
    "claim_delivery",
    "claim_product_for_evaluation",
    "deposit",
    "get_balance",
    "mark_delivered",
    "mark_picked_up",
    "purchase",
    "release_evaluation",
    "submit_evaluation",
    "top_up",
    "withdraw",
]
