# Cheat sheet

Every command you will type today, in order. This page is on screen the whole
session. You never need to type anything that is not on it.

---

## Before anything

```bash
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

Your prompt should start with `(.venv)`.

---

## 0:00 — Setup gate

```bash
pytest tests/test_00_smoke.py
```

Want: `3 passed`

---

## Module A — the harness (0:30)

Edit: `tests/conftest.py`

```bash
pytest tests/test_a_harness.py
```

Want: `6 passed`

Stuck?

```bash
git stash                        # save your work
git checkout checkpoint-a        # see the answer
git checkout main                # go back to yours
git stash pop
```

---

## Module B — the broker (1:10)

Edit: `tutorial/broker.py`

```bash
pytest tests/test_b_broker.py
```

Want: `15 passed`

Escape hatch: `git checkout checkpoint-b`

---

## Module C — the clean room (1:50)

Edit: `tutorial/clean_room.py`

```bash
pytest tests/test_c_clean_room.py
```

Want: `12 passed`

Escape hatch: `git checkout checkpoint-c`

---

## Module D — the IAM trap (2:10)

### The sabotage

In `tutorial/broker.py`, inside `_build_policy`, change:

```python
"Resource": [resource],
```

to:

```python
"Resource": ["*"],
```

Then:

```bash
pytest tests/test_b_broker.py
```

Want: `15 passed` — **still green, with a policy that grants everything.**

### The trap

```bash
pytest tests/test_d_iam_trap.py::test_credential_cannot_read_a_different_object
```

Want: `1 xfailed` — the test you would obviously write cannot work here.

### The fix

Put the `Resource` line back. Edit: `tests/test_d_iam_trap.py`

```bash
pytest tests/test_d_iam_trap.py
```

Want: `12 passed, 1 xfailed, 1 deselected`

Now sabotage it again and watch the structural tests fail:

```bash
pytest tests/test_d_iam_trap.py -k wildcard
```

Escape hatch: `git checkout checkpoint-d`

---

## Module E — the finale (2:45)

```bash
git checkout checkpoint-d
pip install -e ".[finale]"
pytest tests/test_e_finale.py
```

Want: `15 passed`

---

## Everything, any time

```bash
pytest                           # the whole suite
pytest -v                        # one line per test
pytest -x                        # stop at the first failure
pytest -k policy                 # only tests with "policy" in the name
pytest --lf                      # only what failed last time
```

---

## Never run this today

```bash
pytest -m aws_integration        # hits real AWS. Needs an account. Not today.
```

---

## Undo everything

```bash
git checkout main
git checkout -- .                # throw away all your edits
```
