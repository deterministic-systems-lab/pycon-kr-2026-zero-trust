"""
Checkpoint C — the clean room.

    pytest tests/test_c_clean_room.py

One record goes in dirty, one record comes out tokenized. The last two tests in
this file are the honest ones: they assert what the tokenizer does *not* do.
"""

from __future__ import annotations

import json
import re

import pytest

from tutorial.clean_room import CLEAN_BUCKET, DIRTY_BUCKET, process_record
from tutorial.tokenizer import TOKEN_LENGTH, new_salt, tokenize, tokenize_record

TOKEN_RE = re.compile(rf"^[0-9a-f]{{{TOKEN_LENGTH}}}$")


def read_clean(s3, key: str) -> dict:
    return json.loads(s3.get_object(Bucket=CLEAN_BUCKET, Key=key)["Body"].read())


def test_record_lands_in_the_clean_bucket(s3, broker, dirty_key, salt):
    process_record(dirty_key, broker, salt)
    assert read_clean(s3, dirty_key)["record_id"].startswith("R-")


def test_identifiers_are_replaced_with_tokens(s3, broker, dirty_key, salt, record):
    process_record(dirty_key, broker, salt)
    clean = read_clean(s3, dirty_key)

    for field in ("name", "mrn", "dob"):
        assert clean[field] != record[field], f"{field} was written through in the clear"
        assert TOKEN_RE.match(clean[field]), (
            f"{field} should be a {TOKEN_LENGTH}-character hex token, got {clean[field]!r}"
        )


def test_non_identifier_fields_survive(s3, broker, dirty_key, salt, record):
    """The clean room is not a shredder. Analysts still need the data."""
    process_record(dirty_key, broker, salt)
    clean = read_clean(s3, dirty_key)
    assert clean["record_id"] == record["record_id"]
    assert clean["note"] == record["note"]


def test_source_object_is_untouched(s3, broker, dirty_key, salt, record):
    """Read-only means read-only. The dirty bucket is the system of record."""
    process_record(dirty_key, broker, salt)
    original = json.loads(s3.get_object(Bucket=DIRTY_BUCKET, Key=dirty_key)["Body"].read())
    assert original == record


def test_process_record_returns_what_it_wrote(s3, broker, dirty_key, salt):
    returned = process_record(dirty_key, broker, salt)
    assert returned == read_clean(s3, dirty_key)


def test_tokens_are_stable_within_a_run(salt):
    """Same value, same salt, same token — so joins still work in the clean room."""
    assert tokenize("Bramble Voss", salt) == tokenize("Bramble Voss", salt)


def test_tokens_differ_across_runs():
    """A fresh salt per run means yesterday's tokens do not match today's."""
    value = "Bramble Voss"
    assert tokenize(value, new_salt()) != tokenize(value, new_salt())


def test_distinct_values_get_distinct_tokens(salt):
    assert tokenize("Alder Quill", salt) != tokenize("Bramble Voss", salt)


def test_missing_fields_are_skipped(salt):
    assert tokenize_record({"record_id": "R-999"}, salt) == {"record_id": "R-999"}


def test_all_twenty_records_flow_through(s3, broker, salt, records):
    """The whole batch, one transaction per record."""
    for rec in records:
        key = f"{rec['record_id']}.json"
        s3.put_object(Bucket=DIRTY_BUCKET, Key=key, Body=json.dumps(rec).encode())
        process_record(key, broker, salt)

    assert s3.list_objects_v2(Bucket=CLEAN_BUCKET)["KeyCount"] == len(records)


def test_free_text_leaks_the_name_and_that_is_the_known_gap(s3, broker, dirty_key, salt, record):
    """
    The tokenizer replaces structured fields. It does not read prose.

    Record R-002's note contains the patient's name in a sentence. After
    tokenization the `name` field is a token and the name is still sitting in
    `note`, in the clean bucket, in the clear.

    This test asserts the gap exists, on purpose. A test that pretends the
    pipeline is safe is worse than no test. Fixing this needs entity recognition
    over free text — Presidio, spaCy, a human — and that is out of scope today.
    See docs/WRAP_UP.md.
    """
    assert record["name"] in record["note"], "Fixture drift: R-002 should name the patient."

    process_record(dirty_key, broker, salt)
    clean = read_clean(s3, dirty_key)

    assert clean["name"] != record["name"]
    assert record["name"] in clean["note"], (
        "If this fails, someone taught the tokenizer to read prose. Good — now "
        "update this test and docs/WRAP_UP.md."
    )


def test_tokenizing_is_not_reversible_without_the_salt(salt):
    """
    A token is a pseudonym, not anonymity. Anyone with the salt and a guess can
    confirm it. That is the threat model you are accepting.
    """
    token = tokenize("Alder Quill", salt)
    assert tokenize("Alder Quill", salt) == token  # holder of the salt confirms a guess
    assert tokenize("Alder Quill", new_salt()) != token  # without it, nothing
