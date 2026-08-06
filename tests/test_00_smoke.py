"""
Environment smoke test. Run this before the session starts.

Three tests. All three green means your machine is ready and you can ignore the
first ten minutes of setup. Any red means fix it now, not on conference wifi.

    pytest tests/test_00_smoke.py

Every failure message below names the exact command that fixes it.
"""

from __future__ import annotations

import sys

import pytest


def test_python_version():
    """This tutorial pins Python 3.12."""
    major, minor = sys.version_info[:2]
    assert (major, minor) == (3, 12), (
        f"This tutorial needs Python 3.12. You are running {major}.{minor} "
        f"({sys.executable}).\n"
        "Fix: install Python 3.12, then rebuild the virtual environment:\n"
        "  python3.12 -m venv .venv\n"
        "  source .venv/bin/activate      (Windows: .venv\\Scripts\\activate)\n"
        "  pip install -e ."
    )


def test_imports():
    """boto3, moto and pytest are installed at the pinned major versions."""
    try:
        import boto3
        import moto
    except ImportError as exc:
        pytest.fail(
            f"A required package is missing: {exc.name}\n"
            "Fix: activate your virtual environment, then:\n"
            "  pip install -e .\n"
            "Offline: see setup/SETUP.md and run setup/install_offline.sh"
        )

    assert boto3.__version__.startswith("1."), (
        f"boto3 must be 1.x. You have {boto3.__version__}.\n"
        "Fix: pip install -e . --force-reinstall"
    )
    assert moto.__version__.startswith("5."), (
        f"moto must be 5.x — this tutorial uses the mock_aws decorator, which "
        f"moto 4 does not have. You have {moto.__version__}.\n"
        "Fix: pip install -e . --force-reinstall"
    )
    assert pytest.__version__.startswith("9."), (
        f"pytest must be 9.x. You have {pytest.__version__}.\n"
        "Fix: pip install -e . --force-reinstall"
    )


def test_moto_round_trip():
    """moto intercepts S3 in-process: create, put, get, compare."""
    import boto3
    from moto import mock_aws

    payload = b"pycon-korea-2026"

    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="smoke-test-bucket")
        s3.put_object(Bucket="smoke-test-bucket", Key="hello.txt", Body=payload)
        body = s3.get_object(Bucket="smoke-test-bucket", Key="hello.txt")["Body"].read()

    assert body == payload, (
        "moto stored an object but returned something different. That should be "
        "impossible.\n"
        "Fix: rebuild the environment from scratch:\n"
        "  rm -rf .venv && python3.12 -m venv .venv\n"
        "  source .venv/bin/activate && pip install -e .\n"
        "If it still fails, email the facilitator with this output."
    )
