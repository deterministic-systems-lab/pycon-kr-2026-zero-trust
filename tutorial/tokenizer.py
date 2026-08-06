"""
Deterministic hash tokenizer.

Replaces direct identifiers with salted SHA-256 tokens. The same input and the
same salt always produce the same token, so you can still join records inside
the clean room. A new salt per run means tokens do not survive across runs.

Provided complete. You do not modify this file.

WHAT THIS IS NOT
----------------
This is not de-identification to a HIPAA Safe Harbor standard, and calling it
that in a real project would be a compliance finding, not a shortcut.

Two specific gaps, both deliberate:

  1. It only touches the fields you name. The `note` field is free text, and a
     patient's name sitting in the middle of a sentence goes straight through
     untouched. Finding identifiers inside prose is an NLP problem. That is
     what Microsoft Presidio is for, and it is out of scope today — see
     docs/WRAP_UP.md.

  2. A deterministic token is still a pseudonym, not anonymity. Anyone holding
     the salt can rebuild the mapping for any value they can guess. The salt is
     the secret. Treat it like one.

It is here so the pipeline has the right shape while the hard part stays out of
the room.
"""

from __future__ import annotations

import hashlib
import secrets

# Structured identifiers we replace. Free-text fields are not in this list, and
# that omission is the point — see the module docstring.
DEFAULT_FIELDS: tuple[str, ...] = ("name", "mrn", "dob")

TOKEN_LENGTH = 12


def new_salt() -> str:
    """Fresh per-run salt. Tokens from different runs never match."""
    return secrets.token_hex(16)


def tokenize(value: str, salt: str) -> str:
    """Salted SHA-256 of one value, truncated to 12 hex characters."""
    digest = hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()
    return digest[:TOKEN_LENGTH]


def tokenize_record(
    record: dict,
    salt: str,
    fields: tuple[str, ...] = DEFAULT_FIELDS,
) -> dict:
    """
    Return a copy of `record` with the named fields tokenized.

    Fields missing from the record are skipped. Everything else — including
    free text — is copied through unchanged.
    """
    clean = dict(record)
    for name in fields:
        if name in clean:
            clean[name] = tokenize(str(clean[name]), salt)
    return clean
