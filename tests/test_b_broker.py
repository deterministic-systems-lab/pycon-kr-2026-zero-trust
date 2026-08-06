"""
Checkpoint B — the broker.

    pytest tests/test_b_broker.py

Read the last test in this file carefully. It issues a credential scoped to one
object, uses that credential to read that object, and passes. It looks like
proof that scoping works.

It is not. Module D explains why. Do not skip Module D.
"""

from __future__ import annotations

import json

import pytest

from tutorial.broker import ACTION_MAP, AWSSTSBroker, EphemeralCredential
from tutorial.clean_room import DIRTY_BUCKET, REGION, build_s3_client, object_arn


def test_ttl_below_sts_minimum_is_rejected(role_arn):
    """STS will not issue a credential shorter than 900 seconds. Fail early."""
    with pytest.raises(ValueError) as exc_info:
        AWSSTSBroker(role_arn=role_arn, ttl=60)
    assert "900" in str(exc_info.value), (
        "The error message should name the 900-second minimum so the caller "
        "knows what to change."
    )


def test_ttl_at_minimum_is_accepted(role_arn):
    AWSSTSBroker(role_arn=role_arn, ttl=900)


def test_issue_returns_a_scoped_credential(broker, dirty_key):
    resource = object_arn(DIRTY_BUCKET, dirty_key)
    credential = broker.issue("txn-abc", resource, "read")

    assert isinstance(credential, EphemeralCredential)
    assert credential.transaction_id == "txn-abc"
    assert credential.scope == f"read:{resource}"
    assert credential.lease_id is None, "STS issues no revocation handle."
    assert set(credential.token) == {"AccessKeyId", "SecretAccessKey", "SessionToken"}


def test_credential_expires_within_the_ttl(broker, dirty_key):
    credential = broker.issue("txn-ttl", object_arn(DIRTY_BUCKET, dirty_key), "read")
    assert 0 < credential.ttl <= 900
    assert not credential.is_expired


def test_expired_credential_reports_zero_ttl():
    """ttl floors at 0. A negative number here would break every caller."""
    stale = EphemeralCredential(
        token={}, expiry=0, scope="read:arn:aws:s3:::b/k", transaction_id="old"
    )
    assert stale.is_expired
    assert stale.ttl == 0


@pytest.mark.parametrize(
    "action,expected",
    [
        ("read", "s3:GetObject"),
        ("write", "s3:PutObject"),
        ("delete", "s3:DeleteObject"),
        ("tag", "s3:PutObjectTagging"),
        ("s3:ListBucket", "s3:ListBucket"),  # unknown strings pass through
    ],
)
def test_action_mapping(broker, action, expected):
    policy = broker._build_policy("arn:aws:s3:::bucket/key", action)
    assert policy["Statement"][0]["Action"] == [expected]


def test_action_map_matches_the_documented_set():
    assert ACTION_MAP == {
        "read": "s3:GetObject",
        "write": "s3:PutObject",
        "delete": "s3:DeleteObject",
        "tag": "s3:PutObjectTagging",
    }


def test_session_name_is_prefixed_and_bounded(broker, dirty_key):
    """
    AWS caps RoleSessionName at 64 characters. Truncating the transaction ID at
    32 keeps the prefixed name inside that limit for any ID you throw at it.
    """
    long_id = "x" * 200
    credential = broker.issue(long_id, object_arn(DIRTY_BUCKET, dirty_key), "read")
    session_name = credential.metadata["session_name"]
    assert session_name.startswith("tutorial-")
    assert len(session_name) <= 64


def test_blast_radius_names_the_single_object(broker, dirty_key):
    resource = object_arn(DIRTY_BUCKET, dirty_key)
    credential = broker.issue("txn-radius", resource, "read")
    assert broker.blast_radius(credential) == f"Single S3 object: read:{resource}"


def test_revoke_is_a_silent_no_op(broker, dirty_key):
    """
    STS cannot revoke. revoke() must not raise, because transaction_scope calls
    it in a finally block and an exception there would mask the real error.
    """
    credential = broker.issue("txn-revoke", object_arn(DIRTY_BUCKET, dirty_key), "read")
    assert broker.revoke(credential) is None


def test_issued_credential_can_read_the_triggering_object(s3, broker, dirty_key, record):
    """
    The happy path: issue a credential for one object, use it, get the bytes.

    This passes. It will keep passing after you sabotage the policy in Module D.
    That is the problem.
    """
    credential = broker.issue(
        "txn-read", object_arn(DIRTY_BUCKET, dirty_key), "read"
    )
    scoped = build_s3_client(credential, REGION)
    body = scoped.get_object(Bucket=DIRTY_BUCKET, Key=dirty_key)["Body"].read()
    assert json.loads(body)["record_id"] == record["record_id"]
