"""Small helpers for building test data without a fixtures dependency."""

import io
import itertools

from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from events.models import Product, ProductImage, ProductStatus, Role, UserProfile
from events.services import credits

PASSWORD = "correct-horse-battery-staple"

_counter = itertools.count(1)


def make_user(role=Role.MEMBER, *, username=None, email=None, balance=0, **profile_kwargs):
    """Create a user with a profile in ``role`` and an optional balance."""
    index = next(_counter)
    username = username or f"user{index}"
    email = email or f"{username}@example.test"

    user = User.objects.create_user(
        username=username,
        email=email,
        password=PASSWORD,
        first_name=f"Test{index}",
        last_name="User",
    )

    profile = UserProfile.objects.get(user=user)
    profile.role = role
    profile.street = profile_kwargs.pop("street", "1 Test Street")
    profile.city = profile_kwargs.pop("city", "Testville")
    profile.postal_code = profile_kwargs.pop("postal_code", "00000")
    profile.country = profile_kwargs.pop("country", "Testland")
    for key, value in profile_kwargs.items():
        setattr(profile, key, value)
    profile.save()

    if balance:
        credits.top_up(user, balance)

    return profile


def make_product(seller, *, price=1000, status=ProductStatus.LISTED, **kwargs):
    """Create a listing owned by ``seller``."""
    index = next(_counter)
    return Product.objects.create(
        seller=seller,
        name=kwargs.pop("name", f"Test device {index}"),
        category=kwargs.pop("category", "MISC"),
        description=kwargs.pop("description", "A device used in a test."),
        listed_price=price,
        status=status,
        evaluation_score=kwargs.pop(
            "evaluation_score", 80 if status == ProductStatus.LISTED else None
        ),
        **kwargs,
    )


def tiny_image(name="test.jpg"):
    """A real, decodable 4x4 JPEG for upload-validation tests."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), (200, 90, 40)).save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name=name)


def attach_image(product, position=1):
    return ProductImage.objects.create(
        product=product, position=position, image=tiny_image()
    )
