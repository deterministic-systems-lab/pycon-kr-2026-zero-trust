"""
Identity-Per-Transaction credential broker.

One transaction gets one credential, scoped to one object, for one action,
for as short a time as the provider allows. When the transaction ends, the
credential is worthless.

The alternative — one long-lived identity per service — means a leaked key
grants everything that service was ever allowed to do, for as long as nobody
notices. IPT shrinks that to a single object and a 15-minute window.

You implement AWSSTSBroker in Module B.
"""

from __future__ import annotations

import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Friendly action names → S3 API actions. Anything not in this map passes
# through unchanged, so you can request "s3:ListBucket" directly.
ACTION_MAP: dict[str, str] = {
    "read": "s3:GetObject",
    "write": "s3:PutObject",
    "delete": "s3:DeleteObject",
    "tag": "s3:PutObjectTagging",
}


@dataclass
class EphemeralCredential:
    """
    A credential scoped to exactly one resource for one transaction.

    Attributes:
        token:          Provider-specific credential material. For AWS STS,
                        a dict with AccessKeyId / SecretAccessKey / SessionToken.
        expiry:         Unix timestamp at which the credential expires.
        scope:          Human-readable grant, "{action}:{resource}".
        transaction_id: Links this credential to one transaction.
        lease_id:       Provider revocation handle. STS has none, so it stays None.
        metadata:       Provider detail for audit and debugging.
    """

    token: Any
    expiry: int
    scope: str
    transaction_id: str
    lease_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return int(time.time()) >= self.expiry

    @property
    def ttl(self) -> int:
        """Seconds remaining before expiry. 0 once expired, never negative."""
        return max(0, self.expiry - int(time.time()))

    def __repr__(self) -> str:
        return (
            f"EphemeralCredential("
            f"transaction_id={self.transaction_id!r}, "
            f"scope={self.scope!r}, "
            f"ttl={self.ttl}s, "
            f"expired={self.is_expired})"
        )


class IdentityBroker(ABC):
    """
    Base class for identity brokers.

    A broker issues credentials scoped to a single resource and action for the
    duration of one transaction. Implementations enforce three rules:

      1. The credential expires at or before the transaction boundary.
      2. The scope is the narrowest the provider can express.
      3. No credential is reused across transactions.

    Providers that cannot revoke must say so in the docstring and treat the TTL
    as the backstop. Silence about a missing control is how audits go wrong.
    """

    @abstractmethod
    def issue(
        self,
        transaction_id: str,
        resource: str,
        action: str,
    ) -> EphemeralCredential:
        """Issue a credential scoped to exactly one resource and action."""
        ...

    @abstractmethod
    def revoke(self, credential: EphemeralCredential) -> None:
        """Revoke a credential early. Log and return if the provider cannot."""
        ...

    @abstractmethod
    def blast_radius(self, credential: EphemeralCredential) -> str:
        """Describe what this credential exposes if it leaks."""
        ...


class AWSSTSBroker(IdentityBroker):
    """
    Issues STS credentials scoped to a single S3 object.

    Each issue() call assumes a role with an inline session policy that allows
    exactly one action on exactly one object ARN. The assumed role may be broad;
    the session policy is the ceiling on top of it. The intersection is what the
    credential can actually do.

    Args:
        role_arn:    Role to assume. Its trust policy must allow the caller.
        ttl:         Credential lifetime in seconds. STS minimum is 900.
        region:      Region for the STS client.
        external_id: Optional STS external ID for cross-account assumes.

    Example::

        broker = AWSSTSBroker(role_arn="arn:aws:iam::123456789012:role/Processor")
        credential = broker.issue(
            transaction_id="abc123",
            resource="arn:aws:s3:::dirty-bucket/record.json",
            action="read",
        )
    """

    def __init__(
        self,
        role_arn: str,
        ttl: int = 900,
        region: str = "us-east-1",
        external_id: str | None = None,
    ) -> None:
        # TODO(you): reject ttl < 900 with a ValueError. STS will not issue a
        # credential shorter than 900 seconds, so failing here beats failing at
        # the API call. Put the number 900 in the message — the test checks for it.

        self._role_arn = role_arn
        self._ttl = ttl
        self._region = region
        self._external_id = external_id
        self._sts: Any = None  # lazy, so a broker can be built outside mock_aws

    def _get_sts_client(self) -> Any:
        if self._sts is None:
            import boto3

            self._sts = boto3.client("sts", region_name=self._region)
        return self._sts

    def _build_policy(self, resource: str, action: str) -> dict[str, Any]:
        """
        Build the inline session policy.

        Exactly one statement, one action, one resource. No wildcards, no
        prefixes, no bucket-level grants. Every character you widen here widens
        the blast radius of a leaked credential.

        The tests in Module D assert this shape directly, because — as you will
        find out — nothing else can.

        Shape to build::

            {
                "Version": "2012-10-17",
                "Statement": [
                    {"Effect": "Allow", "Action": [...], "Resource": [...]}
                ],
            }
        """
        # TODO(you): map `action` through ACTION_MAP. Anything not in the map is
        #            already a full S3 action string — pass it through unchanged.
        # TODO(you): return the policy document. One statement. One action. One
        #            resource. No wildcards anywhere.
        raise NotImplementedError("Module B: build the inline session policy.")

    def issue(
        self,
        transaction_id: str,
        resource: str,
        action: str,
    ) -> EphemeralCredential:
        """
        Issue STS credentials scoped to a single S3 object ARN.

        Args:
            transaction_id: Unique ID for this transaction.
            resource:       S3 object ARN, "arn:aws:s3:::bucket/key".
            action:         "read", "write", "delete", "tag", or a full S3
                            action string such as "s3:GetObject".

        Steps:

          1. Get the STS client with self._get_sts_client().
          2. Build the session policy with self._build_policy().
          3. Name the session "tutorial-" + the first 32 characters of the
             transaction ID. AWS caps RoleSessionName at 64, so truncate.
          4. Call sts.assume_role() with RoleArn, RoleSessionName, Policy and
             DurationSeconds. Policy is a JSON *string*, not a dict.
             Add ExternalId only when self._external_id is set.
          5. Wrap the response in an EphemeralCredential. The token holds
             AccessKeyId, SecretAccessKey and SessionToken. `expiry` is a unix
             timestamp — the response gives you a datetime.
             `scope` is f"{action}:{resource}". `lease_id` stays None: STS
             issues no revocation handle, so there is nothing to store.
             Put session_name and role_arn in `metadata`.
        """
        # TODO(you): steps 1-5 above. Run `pytest tests/test_b_broker.py` as you go.
        raise NotImplementedError("Module B: issue a scoped credential.")

    def revoke(self, credential: EphemeralCredential) -> None:
        """
        No-op. AWS STS cannot revoke a credential it has already issued.

        This is not an oversight in this code. It is a property of STS. Once
        assume_role returns, those keys are valid until they expire, and no API
        call takes them back. Read that sentence again before you design a
        pipeline around short-lived credentials.

        What you have instead:

          1. The TTL. 900 seconds, minimum, non-negotiable.
          2. The scope. One object. A leaked credential gets one object.
          3. Deleting the source object after processing, so the credential
             points at nothing for the rest of its life.

        Control 3 is the one people forget. It is also the strongest.
        """
        # TODO(you): log the no-op at debug level and return. Do not raise —
        # transaction_scope calls this in a `finally` block, and an exception
        # there would mask whatever real error the body was already raising.
        raise NotImplementedError("Module B: log the no-op and return None.")

    def blast_radius(self, credential: EphemeralCredential) -> str:
        # TODO(you): return f"Single S3 object: {credential.scope}"
        raise NotImplementedError("Module B: describe what a leak exposes.")
