from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.encoding import smart_str

import stripe

from . import invoices
from . import sources
from ..conf import settings
from .. import hooks
from .. import models
from .. import utils


def can_charge(customer):
    """
    Can the given customer create a charge

    Args:
        customer: a pinax.stripe.models.Customer object
    """
    if customer.date_purged is not None:
        return False
    if customer.default_source:
        return True
    return False


def create(user, card=None, plan=settings.PINAX_STRIPE_DEFAULT_PLAN, charge_immediately=True):
    """
    Creates a Stripe customer.

    If a customer already exists, the existing customer will be returned.

    Args:
        user: a user object
        card: optionally, the token for a new card
        plan: a plan to subscribe the user to
        charge_immediately: whether or not the user should be immediately
                            charged for the subscription

    Returns:
        the pinax.stripe.models.Customer object that was created
    """
    trial_end = hooks.hookset.trial_period(user, plan)

    stripe_customer = stripe.Customer.create(
        email=user.email,
        source=card,
        plan=plan,
        trial_end=trial_end
    )
    try:
        # wrap in a transaction to keep tests happy
        with transaction.atomic():
            cus = models.Customer.objects.create(
                user=user,
                stripe_id=stripe_customer["id"]
            )
    except IntegrityError:
        # There is already a Customer object for this user
        stripe.Customer.retrieve(stripe_customer["id"]).delete()
        return models.Customer.objects.get(user=user)

    sync_customer(cus, stripe_customer)

    if plan and charge_immediately:
        invoices.create_and_pay(cus)
    return cus


def get_customer_for_user(user):
    """
    Get a customer object for a given user

    Args:
        user: a user object

    Returns:
        a pinax.stripe.models.Customer object
    """
    return next(iter(models.Customer.objects.filter(user=user)), None)


def purge(customer):
    """
    Deletes the Stripe customer data and purges the linking of the transaction
    data to the Django user.

    Args:
        customer: the pinax.stripe.models.Customer object to purge
    """
    try:
        customer.stripe_customer.delete()
    except stripe.InvalidRequestError as e:
        if not smart_str(e).startswith("No such customer:"):
            # The exception was thrown because the customer was already
            # deleted on the stripe side, ignore the exception
            raise
    customer.user = None
    customer.date_purged = timezone.now()
    customer.save()


def link_customer(event):
    """
    Links a customer referenced in a webhook event message to the event object

    Args:
        event: the pinax.stripe.models.Event object to link
    """
    cus_id = None
    customer_crud_events = [
        "customer.created",
        "customer.updated",
        "customer.deleted"
    ]
    event_data_object = event.message["data"]["object"]
    if event.kind in customer_crud_events:
        cus_id = event_data_object["id"]
    else:
        cus_id = event_data_object.get("customer", None)
    if cus_id is not None:
        customer, created = models.Customer.objects.get_or_create(
            stripe_id=cus_id,
            stripe_account=event.stripe_account
        )
        if event.kind in customer_crud_events:
            sync_customer(customer, event_data_object)

        event.customer = customer
        event.save()


def set_default_source(customer, source):
    """
    Sets the default payment source for a customer

    Args:
        customer: a Customer object
        source: the Stripe ID of the payment source
    """
    stripe_customer = customer.stripe_customer
    stripe_customer.default_source = source
    cu = stripe_customer.save()
    sync_customer(customer, cu=cu)


def sync_customer(customer, cu=None):
    """
    Syncronizes a local Customer object with details from the Stripe API

    Args:
        customer: a Customer object
        cu: optionally, data from the Stripe API representing the customer
    """
    if cu is None:
        cu = customer.stripe_customer
    customer.account_balance = utils.convert_amount_for_db(cu["account_balance"], cu["currency"])
    customer.currency = cu["currency"] or ""
    customer.delinquent = cu["delinquent"]
    customer.default_source = cu["default_source"] or ""
    customer.save()
    for source in cu["sources"]["data"]:
        sources.sync_payment_source_from_stripe_data(customer, source)
    # Luke: at some stage, subscription data was no longer returned, not to mention
    # that we do not need it at Poparide
    # for subscription in cu["subscriptions"]["data"]:
        # subscriptions.sync_subscription_from_stripe_data(customer, subscription)
