"""Forms.

Every piece of user input reaches the database through one of these. The
original views read ``request.POST.get(...)`` directly and passed the raw
strings to ``objects.create()``, so nothing was validated: prices could be
negative or non-numeric (a 500), and uploads skipped image checking entirely.
"""

from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import (
    PRODUCT_CATEGORIES,
    EvaluationJob,
    Product,
    ProductImage,
    Role,
    UserProfile,
)
from .validators import phone_validator, validate_image_upload

MAX_PRODUCT_IMAGES = 4


class StyledFormMixin:
    """Attach the project's input class to every widget.

    Keeps presentation out of the templates without hand-writing each field.
    """

    default_input_class = "field__input"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                continue
            css = widget.attrs.get("class", "")
            widget.attrs["class"] = f"{css} {self.default_input_class}".strip()
            if field.required:
                widget.attrs.setdefault("required", "required")


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------


class SignUpForm(StyledFormMixin, UserCreationForm):
    """Registration for any role.

    Subclasses ``UserCreationForm`` so Django's password validators (length,
    commonness, similarity to the username) run. The old signup accepted any
    password, including a single character, and printed it to the console.
    """

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    phone_number = forms.CharField(
        max_length=20, validators=[phone_validator], required=False,
        help_text=_("Optional, but couriers use it to reach you."),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(_("An account already uses that email address."))
        return email

    def clean_phone_number(self):
        phone = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone:
            return ""
        if UserProfile.objects.filter(phone_number=phone).exists():
            raise ValidationError(_("An account already uses that phone number."))
        return phone

    def save(self, commit=True, role=Role.MEMBER):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
            # The post_save signal has created the profile; fill in the rest.
            profile = user.profile
            profile.role = role
            profile.phone_number = self.cleaned_data.get("phone_number") or None
            profile.save(update_fields=["role", "phone_number", "updated_at"])
        return user


class EmailLoginForm(StyledFormMixin, AuthenticationForm):
    """Sign in with an email address rather than a username."""

    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )

    error_messages = {
        **AuthenticationForm.error_messages,
        # One message for both "no such account" and "wrong password", so the
        # form cannot be used to discover which addresses are registered.
        "invalid_login": _("The email address or password is incorrect."),
    }


class ProfileDetailsForm(StyledFormMixin, forms.ModelForm):
    """Name and contact details."""

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)

    class Meta:
        model = UserProfile
        fields = ["phone_number", "avatar"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.instance.user.first_name
        self.fields["last_name"].initial = self.instance.user.last_name
        self.fields["avatar"].validators.append(validate_image_upload)
        self.fields["avatar"].widget.attrs["accept"] = "image/*"

    def clean_phone_number(self):
        phone = (self.cleaned_data.get("phone_number") or "").strip()
        if not phone:
            return None
        clash = UserProfile.objects.filter(phone_number=phone).exclude(
            pk=self.instance.pk
        )
        if clash.exists():
            raise ValidationError(_("An account already uses that phone number."))
        return phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data.get("last_name", "")
        if commit:
            user.save(update_fields=["first_name", "last_name"])
            profile.save()
        return profile


class AddressForm(StyledFormMixin, forms.ModelForm):
    """Where a courier collects from or delivers to."""

    class Meta:
        model = UserProfile
        fields = ["street", "city", "state", "postal_code", "country"]
        widgets = {"street": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("street", "city", "postal_code", "country"):
            self.fields[name].required = True


class TopUpForm(StyledFormMixin, forms.Form):
    """Mock credit purchase."""

    amount = forms.IntegerField(
        min_value=1,
        max_value=settings.MAX_TOPUP_CREDITS,
        label=_("Credits to add"),
        widget=forms.NumberInput(attrs={"step": 1, "inputmode": "numeric"}),
    )


# ---------------------------------------------------------------------------
# Selling
# ---------------------------------------------------------------------------


class ProductForm(StyledFormMixin, forms.ModelForm):
    """Create or edit a listing, with up to four photos."""

    category = forms.ChoiceField(choices=PRODUCT_CATEGORIES)

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "purchase_price",
            "purchased_on",
            "listed_price",
            "discount_percent",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "purchased_on": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "name": _("What are you selling?"),
            "purchase_price": _("What did you pay for it?"),
            "purchased_on": _("When did you buy it?"),
            "listed_price": _("Your asking price"),
            "discount_percent": _("Discount (%)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for index in range(1, MAX_PRODUCT_IMAGES + 1):
            required = index == 1 and self.instance.pk is None
            self.fields[f"image_{index}"] = forms.ImageField(
                required=required,
                validators=[validate_image_upload],
                label=_("Photo %(n)d") % {"n": index},
                widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
            )

    def clean_purchased_on(self):
        purchased_on = self.cleaned_data.get("purchased_on")
        if purchased_on:
            from django.utils import timezone

            if purchased_on > timezone.localdate():
                raise ValidationError(_("That date is in the future."))
        return purchased_on

    def clean(self):
        cleaned = super().clean()
        listed = cleaned.get("listed_price")
        discount = cleaned.get("discount_percent") or 0
        # Guard against a discount that prices the item at zero, which would
        # let a buyer take it for free.
        if listed and discount and round(listed * (100 - discount) / 100) < 1:
            raise ValidationError(
                _("That discount reduces the price below 1 credit.")
            )
        return cleaned

    @property
    def image_fields(self):
        """The photo fields, for templates that lay them out as a group."""
        return [self[f"image_{i}"] for i in range(1, MAX_PRODUCT_IMAGES + 1)]

    def save_images(self, product):
        """Persist uploaded photos as :class:`ProductImage` rows."""
        for index in range(1, MAX_PRODUCT_IMAGES + 1):
            upload = self.cleaned_data.get(f"image_{index}")
            if not upload:
                continue
            ProductImage.objects.update_or_create(
                product=product,
                position=index,
                defaults={"image": upload},
            )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------


class EvaluationForm(StyledFormMixin, forms.Form):
    """An evaluator's verdict on the product they are holding."""

    score = forms.IntegerField(
        min_value=0,
        max_value=100,
        label=_("Condition score (0-100)"),
        help_text=_("40 or above lists the product; below that it is rejected."),
        widget=forms.NumberInput(attrs={"step": 1, "inputmode": "numeric"}),
    )
    notes = forms.CharField(
        max_length=2000,
        required=False,
        label=_("Notes for the buyer"),
        widget=forms.Textarea(attrs={"rows": 4}),
    )


class EvaluationJobFilterForm(StyledFormMixin, forms.Form):
    """Narrow the queue of products awaiting evaluation."""

    category = forms.ChoiceField(
        choices=[("", _("All categories"))] + list(PRODUCT_CATEGORIES),
        required=False,
    )


# ---------------------------------------------------------------------------
# Catalogue browsing
# ---------------------------------------------------------------------------


class CatalogueFilterForm(StyledFormMixin, forms.Form):
    """Search and filter the public catalogue."""

    SORT_CHOICES = [
        ("-created_at", _("Newest first")),
        ("listed_price", _("Price: low to high")),
        ("-listed_price", _("Price: high to low")),
        ("-evaluation_score", _("Best condition")),
    ]

    q = forms.CharField(
        required=False,
        label=_("Search"),
        widget=forms.TextInput(attrs={"placeholder": _("Search listings")}),
    )
    category = forms.ChoiceField(
        choices=[("", _("All categories"))] + list(PRODUCT_CATEGORIES),
        required=False,
    )
    sort = forms.ChoiceField(choices=SORT_CHOICES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A filter bar should never look like a form with mandatory fields.
        for field in self.fields.values():
            field.widget.attrs.pop("required", None)
