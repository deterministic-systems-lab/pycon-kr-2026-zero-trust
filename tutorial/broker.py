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
        if ttl < 900:
            raise ValueError(
                f"STS minimum TTL is 900 seconds. Got {ttl}. "
                "AWS rejects anything shorter. If you need a 30-second credential, "
                "you need a provider with revocable leases, not STS."
            )

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
        """
        api_action = ACTION_MAP.get(action, action)
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [api_action],
                    "Resource": [resource],
                }
            ],
        }

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
        """
        sts = self._get_sts_client()
        policy = self._build_policy(resource, action)

        # pymayfly uses the "mayfly-" prefix. Ours says "tutorial-" so you can
        # tell your sessions apart from the library's in CloudTrail.
        session_name = f"tutorial-{transaction_id[:32]}"

        assume_kwargs: dict[str, Any] = dict(
            RoleArn=self._role_arn,
            RoleSessionName=session_name,
            Policy=json.dumps(policy),
            DurationSeconds=self._ttl,
        )
        if self._external_id:
            assume_kwargs["ExternalId"] = self._external_id

        response = sts.assume_role(**assume_kwargs)
        creds = response["Credentials"]

        logger.info(
            "issued credential txn=%s scope=%s:%s session=%s",
            transaction_id,
            action,
            resource,
            session_name,
        )

        return EphemeralCredential(
            token={
                "AccessKeyId": creds["AccessKeyId"],
                "SecretAccessKey": creds["SecretAccessKey"],
                "SessionToken": creds["SessionToken"],
            },
            expiry=int(creds["Expiration"].timestamp()),
            scope=f"{action}:{resource}",
            transaction_id=transaction_id,
            lease_id=None,  # STS issues no revocation handle. There is nothing to store.
            metadata={"session_name": session_name, "role_arn": self._role_arn},
        )

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
        logger.debug(
            "revoke() is a no-op for STS. txn=%s ttl_remaining=%ds",
            credential.transaction_id,
            credential.ttl,
        )

    def blast_radius(self, credential: EphemeralCredential) -> str:
        return f"Single S3 object: {credential.scope}"
