"""
The finale.

    pip install -e ".[finale]"
    pytest tests/test_e_finale.py

Every test in this file runs twice: once against the broker you wrote today, and
once against `pymayfly.AWSSTSBroker` off PyPI.

The same tests pass for both, because you rebuilt the library's API from first
principles without being shown it. That was the exercise. The point is not that
pymayfly exists — it is that once you know what Identity-Per-Transaction has to
do, the shape of the code is forced.

Skips cleanly if pymayfly is not installed. Nothing in Modules A–D needs it.
"""

from __future__ import annotations

import json

import pytest

from tutorial.broker import AWSSTSBroker as TutorialBroker
from tutorial.clean_room import DIRTY_BUCKET, REGION, build_s3_client, object_arn

pymayfly = pytest.importorskip(
    "pymayfly",
    reason=(
        "pymayfly is not installed — that is fine, it is optional and the rest of "
        "the tutorial does not use it. To see the reveal: pip install -e \".[finale]\""
    ),
)

PymayflyBroker = pymayfly.AWSSTSBroker

BROKERS = [
    pytest.param(TutorialBroker, id="tutorial"),
    pytest.param(PymayflyBroker, id="pymayfly"),
]


@pytest.fixture
def make_broker(s3, role_arn):
    """Build either broker inside the mock. Same constructor signature, both."""

    def _make(cls, ttl: int = 900):
        return cls(role_arn=role_arn, ttl=ttl, region=REGION)

    return _make


@pytest.mark.parametrize("Broker", BROKERS)
def test_constructor_signature_matches(Broker, make_broker):
    assert make_broker(Broker) is not None


@pytest.mark.parametrize("Broker", BROKERS)
def test_ttl_guard_matches(Broker, make_broker):
    with pytest.raises(ValueError):
        make_broker(Broker, ttl=60)


@pytest.mark.parametrize("Broker", BROKERS)
def test_issue_returns_the_same_shaped_credential(Broker, make_broker, dirty_key):
    broker = make_broker(Broker)
    resource = object_arn(DIRTY_BUCKET, dirty_key)
    credential = broker.issue("txn-finale", resource, "read")

    assert credential.transaction_id == "txn-finale"
    assert credential.scope == f"read:{resource}"
    assert credential.lease_id is None
    assert set(credential.token) == {"AccessKeyId", "SecretAccessKey", "SessionToken"}
    assert 0 < credential.ttl <= 900
    assert not credential.is_expired


@pytest.mark.parametrize("Broker", BROKERS)
def test_policy_is_identical(Broker, make_broker):
    """
    The structural test from Module D, applied to both brokers.

    Byte-for-byte the same policy document. The only difference between the two
    implementations is the session-name prefix.
    """
    resource = "arn:aws:s3:::dirty-bucket/R-002.json"
    policy = make_broker(Broker)._build_policy(resource, "read")

    assert policy == {
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": [resource]}
        ],
    }
    assert "*" not in json.dumps(policy)


@pytest.mark.parametrize("Broker", BROKERS)
def test_blast_radius_matches(Broker, make_broker, dirty_key):
    broker = make_broker(Broker)
    resource = object_arn(DIRTY_BUCKET, dirty_key)
    credential = broker.issue("txn-radius", resource, "read")
    assert broker.blast_radius(credential) == f"Single S3 object: read:{resource}"


@pytest.mark.parametrize("Broker", BROKERS)
def test_revoke_is_a_no_op_in_both(Broker, make_broker, dirty_key):
    broker = make_broker(Broker)
    credential = broker.issue("txn-revoke", object_arn(DIRTY_BUCKET, dirty_key), "read")
    assert broker.revoke(credential) is None


@pytest.mark.parametrize("Broker", BROKERS)
def test_the_whole_clean_room_runs_on_either_broker(Broker, make_broker, s3, dirty_key, salt, record):
    """
    The import swap.

    process_record() takes an IdentityBroker. It has never cared which one. Swap
    the implementation underneath a working pipeline and the pipeline does not
    notice — that is what programming to the protocol buys you.
    """
    from tutorial.clean_room import CLEAN_BUCKET, process_record

    process_record(dirty_key, make_broker(Broker), salt)

    clean = json.loads(s3.get_object(Bucket=CLEAN_BUCKET, Key=dirty_key)["Body"].read())
    assert clean["name"] != record["name"]
    assert clean["record_id"] == record["record_id"]


def test_session_name_prefix_is_the_only_difference(make_broker, dirty_key):
    """The one deliberate divergence, asserted so nobody wonders."""
    resource = object_arn(DIRTY_BUCKET, dirty_key)

    ours = make_broker(TutorialBroker).issue("txn-x", resource, "read")
    theirs = make_broker(PymayflyBroker).issue("txn-x", resource, "read")

    assert ours.metadata["session_name"] == "tutorial-txn-x"
    assert theirs.metadata["session_name"] == "mayfly-txn-x"
    assert ours.scope == theirs.scope
