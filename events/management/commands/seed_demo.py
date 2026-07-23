"""Populate the database with a realistic, explorable demo dataset.

    python manage.py seed_demo

Creates members, evaluators, and couriers, lists devices across several
categories, runs some of them through evaluation, and takes a few all the way
through purchase and delivery so the order, escrow, and payout screens have
real data in them.

Idempotent: running it twice will not duplicate accounts.
"""

import io
import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from events.models import (
    CreditTransaction,
    Product,
    ProductImage,
    ProductStatus,
    Role,
    UserProfile,
)
from events.services import credits, evaluation, logistics, marketplace

DEMO_PASSWORD = "veritrade-demo-2026"

MEMBERS = [
    ("amara", "Amara", "Okonkwo", "amara@example.com", "Lagos"),
    ("priya", "Priya", "Raghavan", "priya@example.com", "Bengaluru"),
    ("tomas", "Tomas", "Novak", "tomas@example.com", "Brno"),
    ("wei", "Wei", "Chen", "wei@example.com", "Singapore"),
]
EVALUATORS = [
    ("elena", "Elena", "Marchetti", "elena@example.com", "Turin"),
    ("kwame", "Kwame", "Asante", "kwame@example.com", "Accra"),
]
COURIERS = [
    ("dmitri", "Dmitri", "Volkov", "dmitri@example.com", "Riga"),
    ("saoirse", "Saoirse", "Byrne", "saoirse@example.com", "Cork"),
]

LISTINGS = [
    ("ThinkPad X1 Carbon (9th gen)", "LAP_COMP", 92000, 41000,
     "Business ultrabook, i7 with 16GB and a 512GB drive. Used daily for two "
     "years as a work machine. Keyboard and trackpad are unmarked; there is a "
     "shallow scratch on the lid near the hinge. Battery still holds most of a "
     "working day. Charger included, original box long gone."),
    ("iPhone 13 Pro, 256GB", "MOB_TAB", 119000, 52000,
     "Graphite, always in a case with a screen protector from day one. Face ID "
     "and all cameras work correctly. Battery health reported at 86%, which is "
     "why it is priced where it is. Cable included, no earphones."),
    ("Dell UltraSharp U2720Q 27\"", "TV_MON", 58000, 24000,
     "4K IPS panel with USB-C power delivery, so it drives a laptop over a "
     "single cable. No dead pixels and no backlight bleed that I can see. "
     "Stand included. Selling because I moved to an ultrawide."),
    ("Sony WH-1000XM4", "AUD_VID", 29000, 11500,
     "Noise cancelling over-ears, black. Earpads are original and starting to "
     "show wear at the edge, which is normal for the age. Sound and ANC are "
     "unaffected. Comes with the hard case and both cables."),
    ("Nintendo Switch OLED", "GAM_CON", 37000, 21000,
     "White Joy-Cons, bought new eighteen months ago. No drift on either stick "
     "as of this listing. Dock, both cables, and the original box are all here. "
     "Screen has been protected since day one."),
    ("Canon EOS M50 Mark II", "CAM_CORD", 62000, 27000,
     "Mirrorless body with the 15-45mm kit lens. Shutter count is a little "
     "under 8000. Small scuff on the base plate from a tripod. Two batteries, "
     "charger, and a 64GB card included."),
    ("Logitech MX Master 3S", "COMP_ACC", 11000, 4800,
     "Graphite, quiet-click version. Scroll wheel and all buttons work "
     "correctly. Some shine on the thumb rest from use. USB-C cable and the "
     "Bolt receiver are both included."),
    ("Kindle Paperwhite (11th gen)", "MISC", 14000, 6200,
     "16GB, no adverts on the lock screen. Screen is unmarked; the bezel has "
     "one small nick in the corner. Battery still lasts weeks. Charges over "
     "USB-C. Cover not included."),
    ("Synology DS220+ NAS", "STO_DEV", 47000, 26000,
     "Two-bay unit, sold as the enclosure only with no drives. Ran continuously "
     "for about three years with no faults. Both bays tested. Power supply and "
     "an ethernet cable are included."),
    ("iPad Air (4th gen), 64GB", "MOB_TAB", 61000, 27500,
     "Sky blue, wifi only. Screen is in excellent condition under a protector "
     "that I will leave on. Rear casing has light scuffing at two corners. "
     "Works with the second-gen Pencil, which is not included."),
    ("Bose SoundLink Revolve+", "AUD_VID", 33000, 12000,
     "Portable bluetooth speaker, triple black. Grille has a small dent on one "
     "side that does not affect the sound. Battery still gives most of a day. "
     "Charging cradle included."),
    ("Raspberry Pi 4 Model B, 8GB", "IND_ELEC", 9500, 5200,
     "Complete kit: board, official case with fan, power supply, and a 32GB "
     "card with a clean OS install. Ran a home server for a year. No overclock "
     "was ever applied."),
]

# A deterministic palette so seeded listings are visually distinguishable.
SWATCHES = [
    (198, 68, 32), (32, 78, 110), (86, 96, 60), (140, 60, 84),
    (58, 92, 88), (120, 88, 40), (70, 66, 108), (44, 100, 72),
]


def placeholder_image(seed, index):
    """Generate a small flat-colour JPEG so listings are not blank.

    Real photos are not committed to the repository; this keeps the seed
    self-contained rather than depending on files under media/.
    """
    from PIL import Image, ImageDraw

    colour = SWATCHES[seed % len(SWATCHES)]
    shade = tuple(max(0, channel - index * 14) for channel in colour)

    image = Image.new("RGB", (800, 600), shade)
    draw = ImageDraw.Draw(image)
    # A few hairlines, so the placeholder reads as deliberate rather than broken.
    for offset in range(0, 800, 40):
        draw.line([(offset, 0), (offset - 200, 600)], fill=tuple(
            min(255, channel + 12) for channel in shade
        ), width=1)

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=82)
    return ContentFile(buffer.getvalue(), name=f"seed-{seed}-{index}.jpg")


class Command(BaseCommand):
    help = "Create a demo dataset covering every role and lifecycle stage."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing demo accounts and their data first.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(20260722)

        if options["flush"]:
            emails = [row[3] for row in MEMBERS + EVALUATORS + COURIERS]
            deleted, _ = User.objects.filter(email__in=emails).delete()
            self.stdout.write(f"Removed {deleted} demo records.")

        members = [self._user(row, Role.MEMBER) for row in MEMBERS]
        evaluators = [self._user(row, Role.EVALUATOR) for row in EVALUATORS]
        couriers = [self._user(row, Role.COURIER) for row in COURIERS]

        for profile in members:
            if credits.get_balance(profile.user) == 0:
                credits.top_up(profile.user, 100000)

        products = self._listings(members)
        self._evaluate(evaluators, products)
        self._trade(members, couriers)

        self.stdout.write(self.style.SUCCESS("\nDemo data ready."))
        self.stdout.write(f"  Password for every demo account: {DEMO_PASSWORD}")
        self.stdout.write(f"  Member:    {MEMBERS[0][3]}")
        self.stdout.write(f"  Evaluator: {EVALUATORS[0][3]}")
        self.stdout.write(f"  Courier:   {COURIERS[0][3]}")

    # -- helpers ---------------------------------------------------------

    def _user(self, row, role):
        username, first, last, email, city = row
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "first_name": first, "last_name": last},
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=["password"])

        profile = UserProfile.objects.get(user=user)
        profile.role = role
        profile.city = city
        profile.street = f"{random.randint(1, 180)} Harbour Road"
        profile.state = ""
        profile.postal_code = f"{random.randint(10000, 99999)}"
        profile.country = "International"
        if not profile.phone_number:
            profile.phone_number = f"+4470{random.randint(10000000, 99999999)}"
        profile.save()

        if created:
            self.stdout.write(f"  + {role.lower()}: {username}")
        return profile

    def _listings(self, members):
        products = []
        for index, (name, category, paid, asking, description) in enumerate(LISTINGS):
            seller = members[index % len(members)]
            product, created = Product.objects.get_or_create(
                name=name,
                seller=seller,
                defaults={
                    "category": category,
                    "description": description,
                    "purchase_price": paid,
                    "purchased_on": timezone.localdate()
                    - timedelta(days=random.randint(200, 1100)),
                    "listed_price": asking,
                    "discount_percent": random.choice([0, 0, 0, 5, 10]),
                    "status": ProductStatus.PENDING_EVALUATION,
                },
            )
            if created:
                for position in range(1, random.choice([2, 3, 4])):
                    ProductImage.objects.create(
                        product=product,
                        position=position,
                        image=placeholder_image(index, position),
                    )
            products.append(product)
        self.stdout.write(f"  {len(products)} listings present.")
        return products

    def _evaluate(self, evaluators, products):
        """Grade most listings; leave a few in the queue to look at."""
        scores = [88, 76, 91, 64, 82, 71, 57, 84, 35, 79]
        pending = [p for p in products if p.status == ProductStatus.PENDING_EVALUATION]

        for index, product in enumerate(pending[: len(scores)]):
            evaluator = evaluators[index % len(evaluators)]
            evaluation.claim_product_for_evaluation(evaluator, product.pk)
            evaluation.submit_evaluation(
                evaluator,
                score=scores[index],
                notes=self._notes(scores[index]),
            )
        self.stdout.write(f"  {len(pending[: len(scores)])} listings evaluated.")

    def _notes(self, score):
        if score >= 80:
            return (
                "Powers on and runs without fault. Cosmetic condition is strong "
                "with only light handling marks. Everything the seller described "
                "matches what arrived."
            )
        if score >= 60:
            return (
                "Fully functional. Visible cosmetic wear on the casing that is "
                "worse than the photos suggest, though nothing structural. "
                "Priced fairly for the condition."
            )
        if score >= 40:
            return (
                "Works, but with noticeable wear and one minor fault noted on "
                "the report. Buyer should read the description carefully."
            )
        return (
            "Does not meet the condition standard: intermittent fault confirmed "
            "under test. Not suitable for sale."
        )

    def _trade(self, members, couriers):
        """Buy several listed items and push them to different delivery stages."""
        listed = list(Product.objects.listed().order_by("pk"))
        if len(listed) < 4:
            return

        buyer = members[0]
        # Not the buyer's own listings, and cheapest first so the seeded orders
        # comfortably fit inside a single demo top-up.
        purchasable = sorted(
            (p for p in listed if p.seller_id != buyer.pk),
            key=lambda p: p.price,
        )[:3]
        if not purchasable:
            return

        order = marketplace.purchase(buyer, purchasable[:2])
        self.stdout.write(f"  Order {order.reference} placed.")

        # One delivery is carried all the way through, so a seller payout and a
        # completed order both exist in the data.
        courier = couriers[0]
        deliveries = logistics.available_deliveries()
        if deliveries:
            logistics.claim_delivery(courier, deliveries.first().pk)
            logistics.mark_picked_up(courier)
            logistics.mark_delivered(courier)
            self.stdout.write("  One delivery completed and the seller paid.")

        # A second order left mid-flight, so the courier queue is not empty.
        if len(purchasable) > 2:
            second = marketplace.purchase(members[1], purchasable[2:])
            self.stdout.write(f"  Order {second.reference} awaiting a courier.")

        ledger = CreditTransaction.objects.count()
        self.stdout.write(f"  {ledger} ledger entries written.")
