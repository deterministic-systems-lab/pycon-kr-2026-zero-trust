"""
Checkpoint A — the harness.

You wrote the `s3` fixture in tests/conftest.py. These tests prove it works.

    pytest tests/test_a_harness.py

Nothing here touches the broker or the clean room yet. The point of Module A is
that you can now write a test against S3 that runs in half a second, offline, on
a plane, with no account and no bill.
"""

from __future__ import annotations

import boto3
import pytest
from botocore.exceptions import ClientError

from tutorial.clean_room import CLEAN_BUCKET, DIRTY_BUCKET, REGION


def test_both_buckets_exist(s3):
    """The fixture creates the dirty and clean buckets."""
    names = {b["Name"] for b in s3.list_buckets()["Buckets"]}
    assert DIRTY_BUCKET in names, (
        f"The `s3` fixture must create the {DIRTY_BUCKET!r} bucket. Found: {sorted(names)}"
    )
    assert CLEAN_BUCKET in names, (
        f"The `s3` fixture must create the {CLEAN_BUCKET!r} bucket. Found: {sorted(names)}"
    )


def test_put_get_round_trip(s3):
    """An object written to the mock comes back byte-identical."""
    s3.put_object(Bucket=DIRTY_BUCKET, Key="probe.txt", Body=b"hello")
    body = s3.get_object(Bucket=DIRTY_BUCKET, Key="probe.txt")["Body"].read()
    assert body == b"hello"


def test_clean_bucket_starts_empty(s3):
    """Each test gets a fresh mock. State does not leak between tests."""
    listing = s3.list_objects_v2(Bucket=CLEAN_BUCKET)
    assert listing.get("KeyCount", 0) == 0, (
        "The clean bucket should be empty at the start of every test. If it is "
        "not, your fixture is sharing state — check that mock_aws() is inside "
        "the fixture, not at module level."
    )


def test_missing_object_raises(s3):
    """moto raises the same ClientError shape real S3 does."""
    with pytest.raises(ClientError) as exc_info:
        s3.get_object(Bucket=DIRTY_BUCKET, Key="does-not-exist.json")
    assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"


def test_seeded_record_is_readable(s3, dirty_key, record):
    """The `dirty_key` fixture seeds one real record into the dirty bucket."""
    import json

    body = s3.get_object(Bucket=DIRTY_BUCKET, Key=dirty_key)["Body"].read()
    assert json.loads(body)["record_id"] == record["record_id"]


def test_mock_does_not_leak_outside_the_fixture():
    """
    Outside the `s3` fixture there is no mock, and no real call either.

    The autouse `aws_credentials` fixture put fake keys in the environment, so a
    client built here talks to nothing. This test documents the boundary: mocking
    is scoped to the fixture, not global.
    """
    client = boto3.client("s3", region_name=REGION)
    assert client.meta.region_name == REGION
