"""
Shared test fixtures.

You write the `s3` fixture in Module A. The rest is provided so later modules
have something to stand on.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from tutorial.broker import AWSSTSBroker
from tutorial.clean_room import CLEAN_BUCKET, DIRTY_BUCKET, REGION
from tutorial.tokenizer import new_salt

# Any role ARN works under moto — it never checks the role exists. Against real
# AWS this would have to be a role whose trust policy allows you to assume it.
ROLE_ARN = "arn:aws:iam::123456789012:role/TutorialProcessor"

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "records.jsonl"


@pytest.fixture(autouse=True)
def aws_credentials(monkeypatch):
    """
    Fake credentials in the environment, for every test.

    This is a safety belt, not a formality. Without it, a bug in a mock — or a
    test that runs outside one — reaches whatever real AWS profile happens to be
    configured on the machine running the suite. In a room of 30 laptops, at
    least one has live production credentials in it.
    """
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def s3():
    """
    A mocked S3 with both buckets, and a client to talk to it.

    MODULE A — this is the exercise.

    Everything inside `with mock_aws()` is intercepted in-process. No network,
    no account, no charges. Every boto3 client created inside this block —
    including ones created deep inside tutorial code — hits the mock.

    Four lines of body. Take your time on where the `with` block starts and
    ends, because that boundary is the whole trick.
    """
    # TODO(you): open a `with mock_aws():` block. Everything below goes inside it.
    # TODO(you): build a boto3 S3 client for REGION.
    # TODO(you): create DIRTY_BUCKET and CLEAN_BUCKET.
    # TODO(you): `yield` the client — yield, not return, so the mock stays open
    #            for the duration of the test and closes cleanly afterwards.
    raise NotImplementedError(
        "Module A: write the moto fixture in tests/conftest.py.\n"
        "Run `pytest tests/test_a_harness.py` as you go — six tests, and they "
        "tell you what is missing.\n"
        "Stuck? `git stash && git checkout checkpoint-a` shows the answer."
    )


@pytest.fixture
def records() -> list[dict]:
    """The 20 fake clinical records, parsed."""
    with DATA_FILE.open() as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture
def record(records) -> dict:
    """One record. R-002, because its note contains the patient name."""
    return records[1]


@pytest.fixture
def dirty_key(s3, record) -> str:
    """Seed one record into the dirty bucket and return its key."""
    key = f"{record['record_id']}.json"
    s3.put_object(Bucket=DIRTY_BUCKET, Key=key, Body=json.dumps(record).encode())
    return key


@pytest.fixture
def role_arn() -> str:
    return ROLE_ARN


@pytest.fixture
def broker(s3) -> AWSSTSBroker:
    """
    A broker wired to the mocked STS.

    Depends on `s3` so the broker is always built inside the mock. Build one
    outside and its lazy boto3 client points at real AWS.
    """
    return AWSSTSBroker(role_arn=ROLE_ARN, ttl=900, region=REGION)


@pytest.fixture
def salt() -> str:
    return new_salt()
