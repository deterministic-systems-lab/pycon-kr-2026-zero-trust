"""
Checkpoint D — the IAM trap.

    pytest tests/test_d_iam_trap.py

This is the module the tutorial exists for.

You have a broker that builds a tight inline session policy. You have a green
test in Module B proving a scoped credential can read its object. It feels
finished.

Now go and widen the Resource in `_build_policy` to "*" and re-run Module B.

    pytest tests/test_b_broker.py

Still green. Every test. moto took your policy document, stored it, and never
evaluated it. It grants every request from every credential. Your Module B suite
never tested the scope at all — it tested that assume_role returns keys.

So write the obvious negative test. It is the first test below. It does not work
either, and the reason it does not work is the lesson.
"""

from __future__ import annotations

import json

import boto3
import pytest
from botocore.exceptions import ClientError

from tutorial.clean_room import DIRTY_BUCKET, REGION, build_s3_client, object_arn

# ---------------------------------------------------------------------------
# 1. The test you would obviously write. It cannot work here.
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason=(
        "moto does not evaluate STS inline session policies. It hands back "
        "credentials that can do anything, so this cross-object read succeeds "
        "and no AccessDenied is ever raised. Behavioural IAM tests are not weak "
        "against moto — they are unwritable. See Module D."
    ),
)
def test_credential_cannot_read_a_different_object(s3, broker, dirty_key):
    """
    Issue a credential for one object, try to read a different one, expect
    AccessDenied.

    Against real AWS this passes and is the single most valuable test in the
    suite. Against moto it fails even when your policy is perfect.

    strict=True on purpose. If moto ever starts enforcing session policies, this
    test will pass unexpectedly, xfail(strict) will turn that into a failure, and
    whoever runs the suite that day will come and read this docstring. That is a
    canary, not a bug.
    """
    s3.put_object(Bucket=DIRTY_BUCKET, Key="someone-elses-record.json", Body=b"{}")

    credential = broker.issue("txn-trap", object_arn(DIRTY_BUCKET, dirty_key), "read")
    scoped = build_s3_client(credential, REGION)

    with pytest.raises(ClientError) as exc_info:
        scoped.get_object(Bucket=DIRTY_BUCKET, Key="someone-elses-record.json")
    assert exc_info.value.response["Error"]["Code"] == "AccessDenied"


# ---------------------------------------------------------------------------
# 2. The fix, part one: test the document, not the behaviour.
#
# You cannot make moto enforce the policy. You can assert that the policy you
# built is exactly the policy you meant to build. These tests fail loudly the
# moment someone widens the scope — which is the failure you actually needed.
# ---------------------------------------------------------------------------

ONE_OBJECT = "arn:aws:s3:::dirty-bucket/R-002.json"


def test_policy_has_exactly_one_statement(broker):
    policy = broker._build_policy(ONE_OBJECT, "read")
    assert len(policy["Statement"]) == 1, (
        "One transaction, one grant. Extra statements are extra blast radius."
    )


def test_policy_grants_exactly_one_action(broker):
    statement = broker._build_policy(ONE_OBJECT, "read")["Statement"][0]
    assert statement["Effect"] == "Allow"
    assert statement["Action"] == ["s3:GetObject"], (
        f"A read credential gets s3:GetObject and nothing else. Got {statement['Action']}."
    )


def test_policy_grants_exactly_one_resource(broker):
    statement = broker._build_policy(ONE_OBJECT, "read")["Statement"][0]
    assert statement["Resource"] == [ONE_OBJECT], (
        f"Resource must be the one triggering object ARN, not a prefix and not a "
        f"bucket. Got {statement['Resource']}."
    )


@pytest.mark.parametrize("action", ["read", "write", "delete", "tag"])
def test_policy_contains_no_wildcards(broker, action):
    """
    The sabotage detector.

    Widen Resource to "arn:aws:s3:::dirty-bucket/*" or "*" in _build_policy and
    this test fails immediately, for every action, with the offending string in
    the message. This is the test Module B should have had.
    """
    policy = broker._build_policy(ONE_OBJECT, action)
    rendered = json.dumps(policy)
    assert "*" not in rendered, (
        f"Wildcard found in the session policy for action {action!r}:\n"
        f"{json.dumps(policy, indent=2)}\n"
        "A wildcard here means a leaked credential reaches more than the one "
        "object this transaction is about."
    )


def test_policy_resource_is_an_object_not_a_bucket(broker):
    """`arn:aws:s3:::bucket` grants the bucket. `arn:aws:s3:::bucket/key` grants one object."""
    resource = broker._build_policy(ONE_OBJECT, "read")["Statement"][0]["Resource"][0]
    assert "/" in resource.removeprefix("arn:aws:s3:::"), (
        f"{resource!r} is a bucket ARN, not an object ARN."
    )


def test_policy_version_is_pinned(broker):
    assert broker._build_policy(ONE_OBJECT, "read")["Version"] == "2012-10-17"


# ---------------------------------------------------------------------------
# 3. The fix, part two: prove the policy actually reaches STS.
#
# A perfect _build_policy is worthless if a refactor drops the Policy kwarg.
# Nothing else in the suite would notice — moto ignores it either way.
# ---------------------------------------------------------------------------


def test_assume_role_receives_the_policy_document(broker, dirty_key):
    """Spy on the STS call and assert the built policy round-trips into it."""
    captured: dict = {}
    real_client = broker._get_sts_client()
    real_assume_role = real_client.assume_role

    def spy(**kwargs):
        captured.update(kwargs)
        return real_assume_role(**kwargs)

    broker._sts.assume_role = spy

    resource = object_arn(DIRTY_BUCKET, dirty_key)
    broker.issue("txn-spy", resource, "read")

    assert "Policy" in captured, (
        "issue() called assume_role without a Policy kwarg. The session policy "
        "was never sent, so the assumed role's full permissions apply."
    )
    assert json.loads(captured["Policy"]) == broker._build_policy(resource, "read")
    assert captured["DurationSeconds"] == 900
    assert captured["RoleSessionName"].startswith("tutorial-")


def test_assume_role_is_called_once_per_transaction(broker, dirty_key):
    """Credential reuse across transactions defeats the whole protocol."""
    calls = []
    real_assume_role = broker._get_sts_client().assume_role

    def spy(**kwargs):
        calls.append(kwargs["RoleSessionName"])
        return real_assume_role(**kwargs)

    broker._sts.assume_role = spy

    resource = object_arn(DIRTY_BUCKET, dirty_key)
    broker.issue("txn-one", resource, "read")
    broker.issue("txn-two", resource, "read")

    assert len(calls) == 2
    assert len(set(calls)) == 2, "Two transactions must produce two distinct sessions."


# ---------------------------------------------------------------------------
# 4. The honest boundary: the real negative test, against real AWS.
#
# Deselected by default (see addopts in pyproject.toml). In CI it runs only in a
# separate job, gated on secrets being present, so forks and attendee clones
# never attempt it. This is the only place the scoping is actually proven.
# ---------------------------------------------------------------------------


@pytest.mark.aws_integration
def test_cross_object_read_is_denied_on_real_aws():
    """
    The test that could not be written against moto.

    Needs a real account, a real role, and a real bucket with two objects:

        AWS_INTEGRATION_ROLE_ARN=arn:aws:iam::<account>:role/<role>
        AWS_INTEGRATION_BUCKET=<bucket>
        AWS_INTEGRATION_KEY_ALLOWED=allowed.json
        AWS_INTEGRATION_KEY_FORBIDDEN=forbidden.json

    Run it deliberately:  pytest -m aws_integration
    """
    import os

    from tutorial.broker import AWSSTSBroker

    required = (
        "AWS_INTEGRATION_ROLE_ARN",
        "AWS_INTEGRATION_BUCKET",
        "AWS_INTEGRATION_KEY_ALLOWED",
        "AWS_INTEGRATION_KEY_FORBIDDEN",
    )
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        pytest.skip(f"Real-AWS integration not configured. Missing: {', '.join(missing)}")

    role_arn = os.environ["AWS_INTEGRATION_ROLE_ARN"]
    bucket = os.environ["AWS_INTEGRATION_BUCKET"]
    allowed = os.environ["AWS_INTEGRATION_KEY_ALLOWED"]
    forbidden = os.environ["AWS_INTEGRATION_KEY_FORBIDDEN"]
    region = os.environ.get("AWS_REGION", REGION)

    broker = AWSSTSBroker(role_arn=role_arn, ttl=900, region=region)
    credential = broker.issue("integration-check", object_arn(bucket, allowed), "read")
    scoped = build_s3_client(credential, region)

    # In scope: this must work, or the policy is too tight to be useful.
    scoped.get_object(Bucket=bucket, Key=allowed)["Body"].read()

    # Out of scope: this must be refused. On moto it never is.
    with pytest.raises(ClientError) as exc_info:
        scoped.get_object(Bucket=bucket, Key=forbidden)
    assert exc_info.value.response["Error"]["Code"] in ("AccessDenied", "403")


def test_the_mock_is_not_the_territory():
    """
    A summary you can quote in a design review.

    moto verifies your code calls AWS correctly. It does not verify AWS would
    allow the call. Those are different claims, and only one of them is what an
    auditor is asking about.
    """
    with __import__("moto").mock_aws():
        sts = boto3.client("sts", region_name=REGION)
        response = sts.assume_role(
            RoleArn="arn:aws:iam::123456789012:role/AnyRoleAtAll",
            RoleSessionName="deliberately-absurd",
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {"Effect": "Deny", "Action": "*", "Resource": "*"}
                    ],
                }
            ),
            DurationSeconds=900,
        )

    # A policy denying everything. moto issued working credentials anyway, and
    # the role does not even exist.
    assert response["Credentials"]["AccessKeyId"]
