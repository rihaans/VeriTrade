# VeriTrade

A marketplace for pre-owned electronics where **every listing is physically
inspected and graded by a person before it can be bought**. The score (0–100)
and the evaluator's notes are published on the listing, and the seller is not
paid until a courier confirms the item was delivered.

Built with Django. The credit balance is a demonstration currency — no payment
provider is connected and no real money changes hands.

---

## How it works

There are three roles, each with its own portal:

| Role | Does |
| --- | --- |
| **Member** | Lists devices for sale and buys ones that have been graded. |
| **Evaluator** | Claims a submitted device, assesses it, and scores it out of 100. |
| **Courier** | Collects from the seller and delivers to the buyer. |

The lifecycle of a device:

1. A member **lists** it. It is *not* on sale yet — it enters the evaluation queue.
2. An evaluator **claims and scores** it. A score of **40 or above** lists it;
   below that it is rejected and never appears in the catalogue.
3. A buyer **purchases** it. Their credits are debited immediately, but the
   money is **held in escrow**, not forwarded to the seller.
4. A courier **delivers** it. Confirming delivery is what **releases payment**
   to the seller and completes the order.

Cancelling an order before delivery refunds the buyer in full and returns the
item to the catalogue. Every movement of credits, in both directions, is
written to an append-only ledger.

---

## Architecture

```
ewaste/
├── ewaste/            Project config (settings, root urls, wsgi/asgi)
├── events/            The domain core
│   ├── models.py          Roles, products, orders, deliveries, credit ledger
│   ├── services/          All business logic, transaction-safe:
│   │   ├── credits.py         deposits, withdrawals, reconciliation
│   │   ├── marketplace.py     purchase (escrow), cancellation (refund)
│   │   ├── evaluation.py      claim / score / release
│   │   └── logistics.py       claim / pick up / deliver (payout)
│   ├── decorators.py      role guards (member / evaluator / courier)
│   ├── forms.py           every user input is validated here
│   ├── validators.py      upload validation (real image, size, extension)
│   ├── auth_backends.py   email-based login
│   ├── admin.py           the operations console
│   └── management/commands/
│       ├── seed_demo.py       populate a full, explorable dataset
│       └── check_ledger.py    reconcile every balance against the ledger
├── base/              Member marketplace + account views (thin, call services)
├── eval/              Evaluator portal (thin, calls services)
├── delivery/          Courier portal (thin, calls services)
└── templates/         One design system, server-rendered
```

**The important rule:** money and lifecycle transitions live *only* in
`events/services/`. Views authenticate, authorise, and delegate; they never
touch a balance or a status directly. Each service function runs inside a
database transaction and re-checks its preconditions under a row lock, so
concurrent requests cannot double-spend, double-sell, or double-pay.

---

## Running it locally

Requires **Python 3.12+**.

```bash
cd ewaste

# 1. Create a virtual environment and install dependencies
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# 2. Configure (the defaults are fine for local work)
cp ../.env.example .env

# 3. Set up the database
python manage.py migrate

# 4. Load a realistic demo dataset (optional but recommended)
python manage.py seed_demo

# 5. Run
python manage.py runserver
```

Then open http://127.0.0.1:8000/.

### Demo accounts

`seed_demo` creates accounts for every role. The password for all of them is
`veritrade-demo-2026`.

| Role | Sign in with |
| --- | --- |
| Member | `amara@example.com` |
| Evaluator | `elena@example.com` |
| Courier | `dmitri@example.com` |

Sign in as the member to browse and buy; as the evaluator to work the grading
queue; as the courier to run deliveries. Create an admin with
`python manage.py createsuperuser` to see the operations console at `/admin/`.

---

## Testing

```bash
cd ewaste
python manage.py test          # ~80 tests, runs in ~2s
```

The suite concentrates on the things that would hurt if they broke:

- **Credit accounting** — balances never go negative, the ledger always sums to
  the balance, top-ups are capped.
- **Purchase & payout** — escrow holds, delivery pays out, credits are conserved
  end to end, cancellation refunds.
- **Lifecycles** — evaluation and delivery can only advance in order, and a
  worker can hold only one job at a time.
- **Authorization** — a regression test exists for every access-control flaw the
  original code had: no acting-user-from-URL, no unauthenticated evaluator or
  courier actions, no cross-account cart/order/listing access, and no
  state-changing GETs.

Run `python manage.py check_ledger` at any time (including in production, on a
schedule) to confirm every balance still reconciles against its transactions.

---

## Deploying

`DJANGO_DEBUG=False` turns on the full production posture and makes
`DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` mandatory — the app refuses to
start without them. See `.env.example` for every setting.

- **Database:** SQLite by default (WAL, foreign keys enforced); set `POSTGRES_DB`
  and friends to switch to PostgreSQL with no code change.
- **Static files:** served by WhiteNoise with hashed, long-cached filenames.
  Run `python manage.py collectstatic`.
- **Media:** in production, uploaded files are meant to be served by the web
  server or an object store, not Django.
- **Security:** HTTPS redirect, HSTS, secure cookies, and a strict referrer
  policy all switch on automatically when `DEBUG` is off.

Verify a deployment build with `python manage.py check --deploy`.
