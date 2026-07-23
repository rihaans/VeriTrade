"""Template context shared by every page.

Keeps the header honest without every view having to remember to pass the
cart count and balance into its context.
"""

from django.conf import settings

from .models import CartItem, CreditAccount, Role, UserProfile


def navigation(request):
    """Expose the current profile, balance, and cart size to all templates."""
    context = {
        "currency_symbol": settings.CURRENCY_SYMBOL,
        "current_profile": None,
        "credit_balance": 0,
        "cart_count": 0,
        "Role": Role,
    }

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return context

    profile = UserProfile.objects.filter(user=user).first()
    context["current_profile"] = profile

    account = CreditAccount.objects.filter(user=user).only("balance").first()
    context["credit_balance"] = account.balance if account else 0

    # Only buyers have a cart; skip the query for everyone else.
    if profile is None or profile.role == Role.MEMBER:
        context["cart_count"] = CartItem.objects.filter(user=user).count()

    return context
