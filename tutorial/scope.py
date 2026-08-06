"""
The transaction boundary.

transaction_scope() is the only sanctioned way to hold a credential in this
pipeline. Issue on enter, revoke on exit, even when the body raises. If you
find yourself calling broker.issue() directly outside this context manager,
you have left the protocol.

Provided complete. You do not modify this file.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Generator
from contextlib import contextmanager

from .broker import EphemeralCredential, IdentityBroker

logger = logging.getLogger(__name__)


@contextmanager
def transaction_scope(
    broker: IdentityBroker,
    resource: str,
    action: str,
    transaction_id: str | None = None,
) -> Generator[EphemeralCredential, None, None]:
    """
    Issue a credential, yield it, revoke it on the way out.

    The try/finally is the whole point. If the body raises, the credential is
    still revoked — or, for STS, the no-op still runs and still logs, which is
    what your audit trail needs to show.

    pymayfly's version takes a fourth argument, `ledger`, and writes a
    provenance record per transaction. That is out of scope today. See
    docs/WRAP_UP.md.

    Args:
        broker:         The broker to issue from.
        resource:       Full resource identifier, e.g. an S3 object ARN.
        action:         "read", "write", "delete", "tag".
        transaction_id: Override the generated UUID to correlate with an
                        upstream request ID.

    Yields:
        An EphemeralCredential scoped to exactly this resource and action.
    """
    txn_id = transaction_id or str(uuid.uuid4())
    credential = broker.issue(txn_id, resource, action)
    logger.debug("scope open txn=%s radius=%s", txn_id, broker.blast_radius(credential))

    try:
        yield credential
    finally:
        broker.revoke(credential)
        logger.debug("scope closed txn=%s", txn_id)
