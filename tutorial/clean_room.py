"""
The clean room.

One record enters the dirty bucket. A tokenized copy lands in the clean bucket.
Nothing in between holds a credential longer than it needs one.

Two transactions, not one: a read scope for the source object and a write scope
for the destination. The read credential cannot write and the write credential
cannot read, so a bug in the tokenizer cannot exfiltrate anything and a leaked
write credential cannot pull the source back out.

Folding both into one broad credential would be less code. It would also be the
thing this tutorial is arguing against.

You complete process_record() in Module C.
"""

from __future__ import annotations

import json
from typing import Any

import boto3

from .broker import IdentityBroker
from .scope import transaction_scope
from .tokenizer import tokenize_record

DIRTY_BUCKET = "dirty-bucket"
CLEAN_BUCKET = "clean-bucket"
REGION = "us-east-1"


def object_arn(bucket: str, key: str) -> str:
    """S3 object ARN. Note there is no region or account ID in an S3 ARN."""
    return f"arn:aws:s3:::{bucket}/{key}"


def build_s3_client(credential: Any, region: str = REGION) -> Any:
    """
    Build an S3 client that uses the issued credential and nothing else.

    This is the step people skip. Issuing a scoped credential and then calling
    boto3.client("s3") with the ambient environment credentials means the scope
    never applied to anything.
    """
    return boto3.client(
        "s3",
        region_name=region,
        aws_access_key_id=credential.token["AccessKeyId"],
        aws_secret_access_key=credential.token["SecretAccessKey"],
        aws_session_token=credential.token["SessionToken"],
    )


def process_record(
    key: str,
    broker: IdentityBroker,
    salt: str,
    region: str = REGION,
) -> dict:
    """
    Move one record from the dirty bucket to the clean bucket, tokenized.

    Args:
        key:    Object key, identical in both buckets.
        broker: Issues the two credentials.
        salt:   Per-run tokenizer salt.

    Returns:
        The tokenized record that was written.
    """
    with transaction_scope(
        broker, resource=object_arn(DIRTY_BUCKET, key), action="read"
    ) as credential:
        s3 = build_s3_client(credential, region)
        raw = s3.get_object(Bucket=DIRTY_BUCKET, Key=key)["Body"].read()

    record = json.loads(raw)
    clean = tokenize_record(record, salt)

    with transaction_scope(
        broker, resource=object_arn(CLEAN_BUCKET, key), action="write"
    ) as credential:
        s3 = build_s3_client(credential, region)
        s3.put_object(
            Bucket=CLEAN_BUCKET,
            Key=key,
            Body=json.dumps(clean).encode(),
            ContentType="application/json",
        )

    return clean
