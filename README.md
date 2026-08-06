# Build a Zero-Trust Data Pipeline in Python (Without an AWS Account)

PyCon Korea 2026 · 180-minute hands-on tutorial · Seoul

You will hand-build an **Identity-Per-Transaction (IPT) credential broker** and a minimal
clean-room data pipeline, then discover why the tests you just wrote do not prove what you
think they prove.

Everything runs offline against [moto](https://github.com/getmoto/moto). No AWS account. No
network at runtime.

## What you build

| Module | You write | Checkpoint test |
|--------|-----------|-----------------|
| A | A moto + pytest harness: mocked S3, dirty and clean buckets | `tests/test_a_harness.py` |
| B | `AWSSTSBroker` — issues STS credentials scoped to one S3 object | `tests/test_b_broker.py` |
| C | The clean room — one record flows dirty → tokenized → clean | `tests/test_c_clean_room.py` |
| D | The IAM trap — why your Module B tests were lying to you | `tests/test_d_iam_trap.py` |

Module D is the point of the tutorial. moto accepts an STS inline session policy and never
evaluates it, so a broker that grants `"Resource": "*"` passes the same tests as a broker
that grants exactly one object. You will watch that happen, fail to write a test that
catches it, and then fix it properly.

## Quickstart

Requires Python 3.12.

```bash
git clone https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust.git
cd pycon-kr-2026-zero-trust
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
pytest tests/test_00_smoke.py
```

Three passing tests means you are ready. If it is not green, see
[`setup/SETUP.md`](setup/SETUP.md) — it covers the offline install from the bundled
wheelhouse, which is what you want on conference wifi.

**Do this before you arrive.** The first ten minutes of the session are a smoke-test gate,
not an install window.

## If you fall behind

Each module has a tag holding the finished state:

```bash
git checkout checkpoint-b        # start Module C with a working broker
git checkout main                # go back to your own work
```

Your work is safe — commit it first, or `git stash`.

## Layout

```
tutorial/     the code you complete (broker, scope, tokenizer, clean room)
tests/        checkpoint tests, one per module
docs/         CHEATSHEET.md (every command you will type), WRAP_UP.md (where moto stops)
              FACILITATOR.md, SPEAKER_NOTES.md, TROUBLESHOOTING.md (for the instructor)
setup/        SETUP.md and the offline install scripts
data/         20 fake clinical records
```

## Scope, honestly

This is a teaching repo. The tokenizer is a deterministic hash, which is **not**
de-identification to a HIPAA standard — it is a stand-in so the pipeline shape is real while
the NLP problem stays out of scope. [`docs/WRAP_UP.md`](docs/WRAP_UP.md) covers what you
would use in production and where moto stops being able to help you.

The broker you build mirrors [`pymayfly`](https://pypi.org/project/pymayfly/), a library by
the same author. pymayfly is pilot-validated; a penetration test is pending. It has been
used in a pilot under FedRAMP constraints. It is not FedRAMP-authorized and neither is
anything in this repo.

## License

Apache-2.0. See [LICENSE](LICENSE).

Tristan McKinnon, Deterministic Systems Lab.
