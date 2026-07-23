"""Reusable validators for user-supplied content.

The original code fed ``request.FILES`` straight into ``Model.objects.create()``,
which bypasses ``ImageField`` validation entirely and allowed arbitrary files to
be written into the media root. Everything that accepts an upload now runs
through :func:`validate_image_upload`.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext_lazy as _

# E.164-ish: optional leading +, then 7-15 digits. Deliberately permissive about
# formatting but strict about what ends up stored.
phone_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{6,14}$",
    message=_(
        "Enter a valid phone number: 7 to 15 digits, optionally starting with '+'."
    ),
)


def validate_image_upload(upload):
    """Reject uploads that are too large, wrongly typed, or not real images.

    Checked in three passes because each catches a different lie: the extension
    catches the honest case, the content type catches a renamed file, and
    Pillow's verify() catches a crafted header.
    """
    max_bytes = settings.MAX_UPLOAD_SIZE_BYTES
    if upload.size > max_bytes:
        raise ValidationError(
            _("Image is %(actual)s; the maximum is %(limit)s.")
            % {"actual": filesizeformat(upload.size), "limit": filesizeformat(max_bytes)}
        )

    extension = Path(upload.name).suffix.lower().lstrip(".")
    allowed = settings.ALLOWED_IMAGE_EXTENSIONS
    if extension not in allowed:
        raise ValidationError(
            _("'%(ext)s' files are not accepted. Use one of: %(allowed)s.")
            % {"ext": extension or upload.name, "allowed": ", ".join(allowed)}
        )

    content_type = getattr(upload, "content_type", "") or ""
    if content_type and not content_type.startswith("image/"):
        raise ValidationError(_("That file is not an image."))

    # Confirm the bytes really decode as an image. verify() consumes the file
    # object, so rewind it for whoever saves the upload afterwards.
    try:
        from PIL import Image

        upload.seek(0)
        Image.open(upload).verify()
    except ImportError:  # pragma: no cover - Pillow is a hard dependency
        pass
    except Exception as exc:  # noqa: BLE001 - Pillow raises a wide range here
        raise ValidationError(_("That file is not a readable image.")) from exc
    finally:
        upload.seek(0)
