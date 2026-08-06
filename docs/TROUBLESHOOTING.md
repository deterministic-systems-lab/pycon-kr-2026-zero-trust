# Troubleshooting

Live-session lookup. Symptom on the left, what to actually do on the right.

**Every error message in this file was reproduced against the real stack** —
Python 3.12.13, boto3 1.43.65, moto 5.2.2, pytest 9.1.1. The text is what the
attendee will see, not a paraphrase.

Attendee-facing install problems live in [`../setup/SETUP.md`](../setup/SETUP.md).
This file is for you, during the session.

---

## Triage rules

Read these before the session. You will not have time to think during it.

1. **Ninety seconds per laptop, maximum.** Longer than that and you have stopped
   running a tutorial for thirty people in order to debug for one.
2. **Any environment problem gets the same answer: the escape hatch.**
   `git stash && git checkout checkpoint-<x>`. Fix it at the break, not now.
3. **If three or more people have the same symptom, stop the room and fix it
   once, out loud.** Same symptom on three laptops means it is on all thirty.
4. **A laptop that cannot be fixed pairs with a neighbour.** Say it warmly and
   without hesitation — hesitation is what makes people feel like a failure.
5. **Never take the keyboard without asking.** In this room people will let you
   and resent it.

---

## Room-wide failures

The ones that end a tutorial. Rehearse these.

### Nobody can install anything (venue wifi is gone)

USB sticks. `setup/install_offline.sh` takes about ten seconds and needs no
network at all. This is exactly what the wheelhouse is for. Carry three sticks.

### The projector dies

Everything on the slides is also in `docs/CHEATSHEET.md`, in the repo they
already have. Say: *"Open docs slash cheatsheet dot M D. Everything I would have
shown you is in that file."* Then keep going.

### You are 20+ minutes behind at 2:10

Skip attendees writing Module D themselves. Put the structural tests on screen,
run the sabotage live, keep beat 4. Beats 1 and 2 without beat 3 leaves the room
with a problem and no solution, which is worse than never starting Module D.

### `main` is somehow broken on your own laptop

```bash
git stash && git checkout checkpoint-d && pytest
```

Present from the solution. Nobody will know.

---

## Setup gate (0:00–0:10)

| Symptom | Cause | Fix |
|---|---|---|
| `pytest: command not found` | venv not active | `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`) |
| `test_python_version` fails | venv built with the wrong Python | `rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e .` |
| `ModuleNotFoundError: No module named 'tutorial'` | running pytest from inside `tests/` | `cd` to the repo root |
| `test_imports` says moto must be 5.x | old moto in the environment | `pip install -e . --force-reinstall` |
| PowerShell refuses to activate | execution policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` |
| pip blocked by corporate proxy | locked-down laptop | USB stick + `setup/install_offline.sh` |

---

## Module A — the harness

### `InvalidAccessKeyId: The AWS Access Key Id you provided does not exist in our records`

**This is the most important error in Module A. Stop the room for it.**

The mock has already closed and boto3 went to **real AWS over the internet**.

Almost always `return client` instead of `yield client` — the `with mock_aws()`
block exits the instant the fixture returns. Also caused by starting `mock_aws()`
at module level instead of inside the fixture.

Fix: `yield client`, inside the `with` block.

Use it as a teaching moment. The call only failed because the autouse
`aws_credentials` fixture put fake keys in the environment. Without it, that call
would have hit whatever real account the laptop is configured for.

### `NoSuchBucket`

Forgot `create_bucket`, or created only one of the two. Both `dirty-bucket` and
`clean-bucket` are needed.

### Tests pass alone but fail together

`mock_aws()` at module level, so state leaks between tests. It belongs inside the
fixture body.

### For your own confidence

A client built *outside* the `with` block but *called* inside works fine — moto
patches at the botocore layer, so pre-existing clients are intercepted too. If an
attendee asks, the answer is: what matters is *when the call happens*, not where
the client was built. Do not repeat the folk wisdom that the client must be
constructed inside the block.

---

## Module B — the broker

| Error | Cause | Fix |
|---|---|---|
| `ParamValidationError: Invalid type for parameter Policy, value: {...}, type: <class 'dict'>, valid types: <class 'str'>` | passed the policy dict straight through | `Policy=json.dumps(policy)` |
| `ParamValidationError: Invalid length for parameter RoleSessionName, value: 0, valid min length: 2` | empty `transaction_id` | AWS needs 2–64 characters. The `tutorial-` prefix covers it once the ID is non-empty. |
| `ParamValidationError: Invalid value for parameter DurationSeconds, value: 60, valid min value: 900` | skipped the TTL guard | Add the guard. Note botocore enforces the floor anyway — the guard exists to fail earlier with a better message. |
| `TypeError: unsupported operand type(s) for -: 'datetime.datetime' and 'int'` | put `Expiration` into `expiry` | `expiry=int(creds["Expiration"].timestamp())` |
| `credential.ttl` is `0` | used `DurationSeconds` (900) as the expiry | `expiry` is an absolute unix timestamp, not a duration |
| `test_session_name_is_prefixed_and_bounded` fails | did not truncate the transaction ID | `f"tutorial-{transaction_id[:32]}"` — AWS caps the name at 64 |
| `test_action_mapping` fails on `s3:ListBucket` | raising on unknown actions | Unknown strings pass through unchanged: `ACTION_MAP.get(action, action)` |
| `NotImplementedError: Module B: ...` | that method is still a stub | Expected. Keep going. |

### They finished suspiciously fast and everything is green

Look at their `_build_policy`. If `Resource` is `["*"]` or a bucket-level ARN,
**say nothing**. That is Module D, and it is far better if they arrive there by
their own hand in twenty minutes.

---

## Module C — the clean room

| Error | Cause | Fix |
|---|---|---|
| `NoSuchKey: The specified key does not exist` | read from the wrong bucket, or wrote to `DIRTY_BUCKET` | Read dirty, write clean, same key |
| `TypeError: cannot convert dictionary update sequence element #0 to a sequence` | forgot `json.loads` — raw bytes reached `tokenize_record` | `record = json.loads(raw)` |
| Name still in the clear in the clean bucket | tokenized after writing, or wrote the original dict | Tokenize, then write the result |
| Tokens change between assertions in one test | called `new_salt()` inside the loop | Take the `salt` fixture and reuse it |
| `test_free_text_leaks_the_name...` fails | somebody "fixed" the tokenizer to scrub the note | That test asserts the gap on purpose. Revert, and use it as the Presidio hook. |

### The failure the tests do not catch

**Verified:** an attendee who opens `transaction_scope`, ignores the credential,
and uses a plain `boto3.client("s3")` **passes all twelve Module C tests.** The
record tokenizes, lands in the clean bucket, suite green.

That is not a bug in the tests. It is the same hole as Module D — moto does not
evaluate authorization, so it cannot tell a scoped client from an ambient one.

If you spot it while walking the room, do not correct it privately. Save it for
the Module C closing beat at 2:05 and show the whole room. It is the best
possible on-ramp to Module D.

---

## Module D — the trap

| Symptom | Meaning |
|---|---|
| `1 xfailed` on the naive negative test | **Correct.** That is the lesson, not a failure. |
| `XPASS(strict)` on the naive negative test | The test unexpectedly passed. Either moto changed, or the attendee edited the test into something that is not a cross-object read. Check their edit first. |
| Wildcard test still passes with `Resource: ["*"]` | They checked the dict instead of the rendered string. `json.dumps(policy)` catches a star anywhere. |
| `AttributeError` in the spy test | Patched `broker._sts` before the lazy client existed. Call `broker._get_sts_client()` first. |
| `1 deselected` | The `aws_integration` test. Correct and expected — it needs a real account. |
| Module B still green after sabotage | **Correct, and the entire point.** Do not "fix" it. |
| Module D shows 6 failures after sabotage | **Correct.** The mechanism is working. |

### "My structural tests pass but I do not understand why they help"

Have them sabotage and re-run, themselves, right then. Watching six named
failures appear does the explaining. Arguing about it does not.

---

## Module E — the finale

| Symptom | Cause | Fix |
|---|---|---|
| `1 skipped` — pymayfly not installed | expected on attendee machines | `pip install -e ".[finale]"` — needs network. If the venue has none, demo from your laptop. |
| `ModuleNotFoundError: No module named 'pymayfly'` after installing | installed into a different environment | Check the venv is active; `pip -V` should point inside `.venv` |
| pymayfly parametrization fails, tutorial passes | their broker diverged from the mirrored API | Not worth debugging live. `git checkout checkpoint-d`. |

**If there is no network at 2:45, do not fight it.** Run the finale on your own
machine on the projector. The reveal is the same. Attendees can run it at home —
it is in `WRAP_UP.md`.

---

## moto quirks worth knowing

Things that look like attendee bugs and are not.

- **moto does not check that the IAM role exists.** `assume_role` against
  `arn:aws:iam::123456789012:role/AnythingAtAll` returns working credentials.
  This is why Module A needs no IAM setup.
- **moto accepts any session policy, including `Deny *`,** and issues working
  credentials anyway. This is the premise of the whole tutorial.
- **`create_bucket` outside `us-east-1` needs `CreateBucketConfiguration`.**
  Someone who changes the region to `ap-northeast-2` because they are in Seoul
  gets: `IllegalLocationConstraintException: The unspecified location constraint
  is incompatible for the region specific endpoint this request was sent to.`
  Tell them to leave the region alone today.
- **`RoleSessionName` must be 2–64 characters.** botocore validates it before the
  request leaves the process.
- **A closed mock does not fail safe.** Calls go to real AWS. The fake-credential
  fixture is the only thing standing between a fixture bug and someone's
  production account.

---

## After the session

Anything that bit more than two people is a curriculum bug, not an attendee
mistake. Open an issue the same evening while you still remember the exact
wording of what confused them.
