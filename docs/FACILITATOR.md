# Facilitator guide

PyCon Korea 2026 · 180 minutes · ~30 attendees · Seoul

Everything here is for the person at the front of the room. Attendees do not read
this file.

---

## Run of show

| Time | Segment | Checkpoint |
|------|---------|------------|
| 0:00–0:10 | Setup smoke test | `test_00_smoke.py` green |
| 0:10–0:30 | Concepts: per-user vs per-transaction, the clean room, why testing AWS code is miserable, one moto demo | — |
| 0:30–1:00 | **Module A — the harness** | `test_a_harness.py` |
| 1:00–1:10 | Break | — |
| 1:10–1:50 | **Module B — the broker** | `test_b_broker.py` |
| 1:50–2:10 | **Module C — the clean room** | `test_c_clean_room.py` |
| 2:10–2:45 | **Module D — the IAM trap** | `test_d_iam_trap.py` |
| 2:45–3:00 | Wrap: the import swap, where moto stops, Q&A | `test_e_finale.py` |

---

## Delivery notes

**Speak slower than you would at a US PyCon.** The session is in English to a
largely Korean-speaking audience. Slow, plain sentences beat idiom and jokes. Cut
every "kind of", "sort of", "you know". Pause after each instruction instead of
filling the gap.

**Every command appears three times:** on a slide, in `docs/CHEATSHEET.md`, and
spoken. Nobody should ever have to catch a command by ear.

**Announce the escape hatch out loud at the start of every module**, and leave it
on screen:

> If you are stuck, `git stash` then `git checkout checkpoint-a`. You lose
> nothing. Rejoin us.

Say it in Module A even though nobody needs it yet. The first person to fall
behind will not ask.

**Walk the room during exercises.** A stuck attendee in this audience is more
likely to sit quietly than to raise a hand. Look at screens, not faces.

**Korean translation of the slides and cheat sheet is an open ask to the
organizers.** If it happens, the cheat sheet matters most — it is all commands and
translates cleanly. This guide does not need translating.

---

## Before the session

- [ ] Rebuild the wheelhouse: `./setup/make_wheelhouse.sh` (needs network)
- [ ] Zip it, attach to the GitHub Release as `wheelhouse.zip`
- [ ] Put the same zip on **three USB sticks**. Someone's download will fail.
- [ ] Verify all four tags exist: `git tag` → `checkpoint-a` … `checkpoint-d`
- [ ] Run the full suite at each tag once, on the laptop you will present from
- [ ] `pip install -e ".[finale]"` on **your** machine only — you need pymayfly
      for the 2:45 reveal and attendees must not have it before then
- [ ] Send the SETUP.md pre-work email at least ten days out
- [ ] Confirm the room has power at every seat. This is a laptop tutorial.

---

## 0:00–0:10 — Setup gate

**Goal:** every laptop shows three green dots.

```bash
source .venv/bin/activate
pytest tests/test_00_smoke.py
```

Expected: `3 passed`.

Ask for a show of hands for anything not green. Handle red laptops in this order:

1. **Wrong Python** — the failure message names the version. Rebuild the venv.
2. **Missing packages** — USB stick, `setup/install_offline.sh`. 9 seconds.
3. **Something else** — pair them with a neighbour who is green and move on.

**Do not** spend more than 10 minutes here. Two people on one laptop is a fine
outcome and better than losing the room.

**Cut line:** none. This segment cannot be cut. If you are behind at 0:10, take it
out of the concepts block, not here.

---

## 0:10–0:30 — Concepts

**Goal:** attendees can say what "identity per transaction" means and why the
alternative is worse.

Beats, in order:

1. **The long-lived key.** One IAM user, one access key, in a Lambda env var since
   2021. What does it reach? Nobody in the room knows for their own systems.
   That is the point — ask them.
2. **Blast radius as the unit.** Not "is it secure" but "what does one leaked
   credential reach, for how long". Both numbers should be small enough to say
   out loud.
3. **Identity per transaction.** One record, one credential, one object, 15
   minutes. The credential is worthless before the attacker finishes reading the
   log line that leaked it.
4. **The clean room.** Dirty bucket in, tokenized out, and nothing in the middle
   holds broad access.
5. **Why testing this is miserable.** You cannot run IAM locally. You cannot get
   an AWS account for a tutorial room. Enter moto.

Live demo, 3 minutes, typed not pasted:

```python
import boto3
from moto import mock_aws

with mock_aws():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="demo")
    s3.put_object(Bucket="demo", Key="a.txt", Body=b"hello")
    print(s3.get_object(Bucket="demo", Key="a.txt")["Body"].read())
```

Say the line that Module D pays off: *"moto is very good at pretending to be AWS.
Hold on to the word pretending."*

**Cut line:** drop beats 1 and 2 to eight minutes of "here is a leaked key story",
keep 3, 4, 5. Never cut the moto demo — it is the mental model for the next hour.

---

## Module A — the harness (0:30–1:00)

**Goal:** attendees can test S3 code with no account and no network.

**Files touched:** `tests/conftest.py` — the `s3` fixture only.

**What they write:** `mock_aws()`, create both buckets, yield the client. About
six lines.

```bash
pytest tests/test_a_harness.py
```

Expected: `6 passed`.

**Teach while they work:**

- `mock_aws()` patches botocore in-process. Every client built inside the block is
  intercepted, including ones built deep inside library code.
- The autouse `aws_credentials` fixture is not ceremony. In a room of 30 laptops
  at least one has live production credentials configured. Fake env vars mean a
  test that escapes the mock reaches nothing.
- Fixture scope is per-test, so state cannot leak between tests. That is what
  `test_clean_bucket_starts_empty` is checking.

**Common failure modes:**

| Symptom | Cause |
|---|---|
| `NoSuchBucket` | Forgot `create_bucket`, or created only one of the two |
| Tests pass then fail in a different order | `mock_aws()` at module level instead of inside the fixture |
| `Could not connect to the endpoint` | Client built outside the `with` block |
| `KeyCount` assertion fails | Reusing one bucket across tests instead of a fresh fixture |

**Cut line:** if you are 10 minutes behind at 0:30, put the finished fixture on
screen at 0:45 and have them copy it. The fixture is not the lesson; the broker
is. Do not let Module A eat Module B.

---

## Module B — the broker (1:10–1:50)

**Goal:** a working `AWSSTSBroker` that issues one credential scoped to one
object.

**Files touched:** `tutorial/broker.py` — `__init__` TTL guard, `_build_policy`,
`issue`, `revoke`, `blast_radius`.

```bash
pytest tests/test_b_broker.py
```

Expected: `15 passed`.

**Order matters.** Tell them to work top-down and run the tests constantly:

1. TTL guard — two minutes, gets a green test immediately
2. `_build_policy` — the core of the exercise
3. `issue` — assemble and call `assume_role`
4. `blast_radius`, `revoke` — one line each

**Teach while they work:**

- The 900-second minimum is an AWS constraint, not a design choice. People always
  ask for 30 seconds. STS says no. That is why the error message says what to do
  instead.
- `revoke()` being a no-op is the honest beat of this module. **Spend a minute on
  it.** STS cannot take a credential back. Once `assume_role` returns, those keys
  work until they expire. The controls you have are the TTL, the scope, and
  deleting the source object afterwards. Ask the room which of the three is
  strongest — the answer is deleting the object, and almost nobody says it.
- Session name is truncated at 32 characters because AWS caps `RoleSessionName`
  at 64. It is a small thing that fails in production at 3am.

**Common failure modes:**

| Symptom | Cause |
|---|---|
| `ParamValidationError: Invalid length for parameter RoleSessionName` | Empty transaction ID |
| `Policy` rejected | Passing the dict, not `json.dumps(policy)` |
| `credential.ttl` is 0 | Using `DurationSeconds` as expiry instead of reading `Expiration` from the response |
| `test_action_mapping` fails on `s3:ListBucket` | Raising on unknown actions instead of passing them through |
| Everything green suspiciously fast | They wrote `Resource: ["*"]`. **Say nothing.** This is Module D and it is better if they arrive there by their own hand. |

**Cut line:** if you are behind at 1:30, give them `issue()` on screen and have
them write only `_build_policy` and the TTL guard. Those two are what Module D
needs.

---

## Module C — the clean room (1:50–2:10)

**Goal:** one record flows dirty → tokenized → clean, with two separate
credentials.

**Files touched:** `tutorial/clean_room.py` — the body of `process_record`.

```bash
pytest tests/test_c_clean_room.py
```

Expected: `12 passed`.

**What they write:** roughly ten lines. Two `transaction_scope` blocks with the
tokenizer between them.

**Teach while they work:**

- **Two scopes, not one.** A read credential for the source, a write credential
  for the destination. Ask why. The answer: a bug in the tokenizer cannot
  exfiltrate anything, and a leaked write credential cannot pull the source back
  out. Folding them into one credential would be less code and is exactly what
  this tutorial argues against.
- `build_s3_client` is the step people skip in real life. Issuing a scoped
  credential and then calling `boto3.client("s3")` with ambient credentials means
  the scope applied to nothing. It is a one-line bug and it is invisible in
  review.
- The last test in the file asserts that the patient's name **leaks** through the
  free-text note. Read it out. A test that documents a known gap is worth more
  than a test that pretends there isn't one. That is the Presidio hook for the
  wrap-up.

**Common failure modes:**

| Symptom | Cause |
|---|---|
| `NoSuchKey` on the clean bucket | Wrote to `DIRTY_BUCKET` |
| Name still in the clear | Tokenized after writing, or passed the wrong dict |
| `TypeError: Object of type bytes is not JSON serializable` | Forgot `json.loads` on the body |
| Tokens differ between runs of the same test | Calling `new_salt()` inside the loop instead of taking the fixture |

**Cut line:** this module is already the shortest. If you are behind at 2:00, put
the read scope on screen and have them write only the write scope. Under no
circumstances let Module C run past 2:15 — Module D needs its full 35 minutes.

---

## Module D — the IAM trap (2:10–2:45)

**This is the module the tutorial exists for.** Everything before it is setup.
Protect this time.

**Files touched:** `tutorial/broker.py` (sabotage, then restore),
`tests/test_d_iam_trap.py`.

### Beat 1 — the false comfort (5 min)

Everyone has a green Module B. Now have them sabotage their own broker. On
screen, in `_build_policy`:

```python
"Resource": ["*"],          # was: [resource]
```

Then:

```bash
pytest tests/test_b_broker.py
```

`15 passed`. Every test. With a policy that grants every object in the account.

**Let the silence sit.** Do not explain yet. Ask: *"What did your Module B tests
actually prove?"* Wait for someone to say it. The answer is: that `assume_role`
returns keys. Nothing about scope.

### Beat 2 — the unwritable test (10 min)

So write the obvious guard. Have them try it themselves before showing the
pre-written one — read a *different* object with the scoped credential and expect
`AccessDenied`.

```bash
pytest tests/test_d_iam_trap.py::test_credential_cannot_read_a_different_object
```

It does not raise. The read succeeds. Have them restore the correct `Resource`
line and run it again — **it still does not raise**.

This is the beat that lands. The test fails *with a correct policy*. moto grants
everything to any credential, so a behavioural IAM test against moto is not weak,
it is unwritable. There is no version of it that works.

That is why the test in the repo is marked `xfail(strict=True)`. Walk through the
`reason` string.

### Beat 3 — structural tests (12 min)

You cannot make moto enforce the policy. You can assert the policy is what you
meant to build.

They fill in the structural tests: call `_build_policy` directly, assert exactly
one statement, exactly one action, `Resource` equal to exactly the one ARN, and no
`*` anywhere in the rendered document.

```bash
pytest tests/test_d_iam_trap.py
```

Expected: `12 passed, 1 xfailed, 1 deselected`.

Then the payoff — sabotage it again:

```bash
pytest tests/test_d_iam_trap.py -k wildcard
```

Six failures naming the wildcard. **This is the mechanism working.** Have them do
it themselves rather than watching you.

Do not skip the spy test. A perfect `_build_policy` is worthless if a refactor
drops the `Policy` kwarg, and nothing else in the suite would notice, because moto
ignores it either way.

### Beat 4 — the gated integration job (8 min)

Slides only, no typing.

Show `@pytest.mark.aws_integration` and the `addopts` line that deselects it. Show
the CI job in `.github/workflows/ci.yml` gated on `secrets.AWS_ROLE_ARN`.

Make the point about gating: a job that **fails** on forks trains everyone to
ignore red CI. A job that **skips** keeps red meaningful.

Land it: *"That one test is the only place in this repository where scope
enforcement is actually proven. Everything else is a proxy. Say that out loud in
your design review."*

**Common failure modes:**

| Symptom | Cause |
|---|---|
| `XPASS(strict)` on the naive test | They restored the policy and expected the negative test to pass. It never passes under moto. That is the lesson. |
| Wildcard test passes with `Resource: ["*"]` | Checking the dict instead of `json.dumps(policy)` |
| Spy test fails with `AttributeError` | Patched `broker._sts` before it was created — call `_get_sts_client()` first |
| `1 deselected` looks like a failure | It is the integration test. Correct behaviour. |

**Cut line:** if you reach 2:30 and are still in beat 2, skip attendees writing
beat 3 themselves — put the structural tests on screen, run the sabotage live,
and keep beat 4. Beats 1 and 2 without beat 3 leaves the room with a problem and
no fix, which is worse than not starting.

---

## 2:45–3:00 — Wrap and the reveal

```bash
git checkout checkpoint-d
pip install -e ".[finale]"
pytest tests/test_e_finale.py
```

Expected: `15 passed`.

**The reveal.** Every test in that file runs twice — once against the broker they
wrote, once against `pymayfly.AWSSTSBroker` from PyPI. Same constructor, same
methods, byte-identical policy document. The only difference is the session-name
prefix, and there is a test asserting that too.

Say it plainly: *"You were not shown this library. You derived it. Once you know
what identity-per-transaction has to do, the shape of the code is forced."*

Then, without softening it:

- pymayfly is **pilot-validated. Penetration test pending.** Used in a pilot under
  FedRAMP constraints. Not FedRAMP-authorized. Version 0.2.0 is early. Read the
  source before adopting it — it is small, and they just rebuilt most of it.
- Presidio is the production answer for the free-text gap. Out of scope today
  because it costs 20 minutes of install and teaches nothing about zero trust.
- Point at `docs/WRAP_UP.md` for all of it, including the Monday checklist.

**Q&A.** Questions this audience reliably asks:

- *"Why not just use IAM roles per service?"* — Because the blast radius is the
  service's whole lifetime, not one record.
- *"Isn't 900 seconds a long time?"* — Yes. It is the floor STS gives you. Scope
  and source deletion are the other two controls.
- *"Does this work with Lambda?"* — Yes, that is pymayfly's `IPTEnforcer`. Same
  shape.
- *"What about cost?"* — `assume_role` is free. The per-record call volume is the
  thing to watch, not the price.

**Cut line:** if you are at 2:55, run the finale, say the two sentences about
deriving the library, point at `WRAP_UP.md`, and stop. Do not start Q&A you cannot
finish. Offer the hallway.

---

## After

- Push any fixes discovered live to `main` the same evening, while you remember
- Open an issue for anything a cut line hid — those are the real curriculum bugs
- The pre-event email is written from `setup/SETUP.md`; keep them in sync
