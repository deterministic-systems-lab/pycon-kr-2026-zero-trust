# Speaker notes

The talk track. What to *say*, beat by beat.

`FACILITATOR.md` is the logistics — timings, cut lines, what to do when things go
wrong. This file is the words. Keep this one open on the lectern.

**Everything in quote blocks is meant to be said out loud.** Not read verbatim —
you will sound like a robot — but the shape and the specific numbers matter. The
lines marked **⚑ LAND THIS** are the ones the whole tutorial hangs on. Slow down,
stop moving, and let them finish.

**Register.** Short sentences. One idea per sentence. Define every acronym the
first time, including IAM and STS. No idioms, no sports metaphors, no jokes that
need cultural context. When you ask the room a question, count to five in your
head before you fill the silence — in this room, five seconds is not awkward, it
is someone translating.

---

## 0:00–0:10 — Setup gate

Do not open with a story. Open with the command.

> Good morning. Before anything else: activate your virtual environment and run
> this one command. It is on the slide and on your cheat sheet.
>
> `pytest tests/test_00_smoke.py`
>
> You want to see "3 passed". Put your hand up if you see anything else.

Then walk the room. While you walk, keep talking — dead air makes people think
they are the problem.

> If you are red, you are not behind. This is exactly why we do this first.

At about 0:07:

> If you are still red, work with the person next to you. Two people on one
> laptop is completely fine for today. You will not miss anything.

Close it:

> Everyone has a green dot or a neighbour with one. That is the last time today
> we will care about installation.

---

## 0:10–0:30 — Concepts

### The long-lived key (4 min)

> I want to start with a question. Think about a data pipeline you work on. It
> has credentials somewhere — an environment variable, a secrets manager, a
> config file.
>
> Here is the question: **what can that credential reach?**
>
> Not what does it use. What *can* it reach.

Pause. Count to five.

> Most of us cannot answer that. I could not answer it for my own systems. That
> is not a criticism of anyone in this room. It is a property of how we build
> these things.

> The usual shape is one identity per service. The service starts, it picks up a
> key, and it holds that key until someone rotates it. Which is to say: for
> years.

### Blast radius (4 min)

> So let us change the question. Instead of "is it secure", ask two questions
> with numbers in them.
>
> **What does one leaked credential reach? And for how long?**
>
> For a long-lived service identity the answers are "everything that service was
> ever allowed to do" and "until somebody notices". Both of those are bad
> answers, and the second one is worse than the first.

**⚑ LAND THIS:**

> If you cannot say both numbers out loud, you do not have a security posture.
> You have a hope.

### Identity per transaction (5 min)

> Here is the alternative. It is one idea, and the whole tutorial is this one
> idea.
>
> **One transaction gets one credential. That credential reaches one object. It
> expires in fifteen minutes.**
>
> That is it. That is identity per transaction.

> Now answer the two questions again. What does a leaked credential reach? One
> object. For how long? Fifteen minutes, maximum.
>
> The credential is worthless before the attacker has finished reading the log
> file they stole it from.

### The clean room (3 min)

> The pipeline we are building today is a clean room. Sensitive records arrive in
> a bucket we will call dirty. A de-identified copy goes into a bucket we will
> call clean.
>
> The rule is that nothing in between ever holds broad access. Not the reader,
> not the writer, not the thing in the middle.

### Why testing this is miserable (4 min)

> Now the practical problem, and it is the reason this is a three-hour tutorial
> and not a fifteen-minute talk.
>
> You cannot run IAM on your laptop. IAM — Identity and Access Management — is
> the AWS service that decides who is allowed to do what. It only exists inside
> AWS. There is no local version.
>
> So how do you test code that depends on it? You cannot give thirty people AWS
> accounts for a tutorial. And most of you cannot get a test account at work
> either.

> The answer the Python community reached for is moto. moto pretends to be AWS,
> inside your test process. No network. No account. No bill.

Demo — **type it, do not paste it**:

```python
import boto3
from moto import mock_aws

with mock_aws():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="demo")
    s3.put_object(Bucket="demo", Key="a.txt", Body=b"hello")
    print(s3.get_object(Bucket="demo", Key="a.txt")["Body"].read())
```

> No network. No account. That ran in about a hundred milliseconds.

**⚑ LAND THIS** — plant the seed for Module D. Say it lightly, then move on
immediately. Do not explain it.

> moto is very good at pretending to be AWS.
>
> Hold on to the word *pretending*. We will come back to it.

---

## Module A — the harness (0:30–1:00)

### Setting up (3 min)

> Open `tests/conftest.py`. You are writing one fixture, called `s3`. It is about
> four lines of body.
>
> It does three things. It opens the moto mock. It creates two buckets, dirty and
> clean. It yields a client.
>
> The word `yield` is doing real work there. Not `return`. I will explain why in
> a moment — and if you use `return`, you will find out on your own in about
> ninety seconds.

Announce the escape hatch. Every module. Starting now, even though nobody needs
it yet:

> If you get stuck at any point today: `git stash`, then
> `git checkout checkpoint-a`. That gives you the finished version. Nothing you
> wrote is lost. Then rejoin us. Nobody has to sit here stuck.

### While they work (walk the room)

Talk over the silence every few minutes:

> `mock_aws` patches at the botocore layer. That means every client built inside
> that block goes to the mock — including clients built deep inside library code
> that you did not write and cannot see.

When the first person hits `InvalidAccessKeyId` — someone will, and it is the
best teaching moment in Module A — **stop the room**:

> Come and look at this error. It says: *the AWS Access Key Id you provided does
> not exist in our records.*
>
> Where did that message come from?

Wait. Let them work it out.

**⚑ LAND THIS:**

> That came back from **real AWS**. Over the internet. Their mock closed early —
> `return` instead of `yield` — and boto3 did what boto3 always does, which is
> talk to Amazon.
>
> A closed mock does not fail safe. It fails *outward*.
>
> The only reason nothing bad happened is the `aws_credentials` fixture at the
> top of the file, which puts the fake string "testing" in the environment. That
> is why it is there. In a room of thirty laptops, at least one has real
> production credentials configured. Maybe yours.

### Closing Module A (2 min)

> You can now test S3 code with no account, no network, and no bill, in under a
> second. That is genuinely useful and you can take it back to work on Monday
> regardless of anything else we do today.

---

## Module B — the broker (1:10–1:50)

### Setting up (4 min)

> Open `tutorial/broker.py`. You are building the thing that issues credentials.
>
> Work top to bottom and run the tests constantly. The TTL guard first — that is
> two minutes and gets you a green test straight away. Then `_build_policy`,
> which is the real exercise. Then `issue`. Then two one-line methods at the
> bottom.

On the session policy, before they start:

> The important idea is the **inline session policy**. When you assume a role,
> you can hand AWS a policy document that applies to that session only. The role
> might be broad. The session policy is a ceiling on top of it. What you actually
> get is the intersection.
>
> So we assume a role that can read the bucket, and we hand it a policy that says
> "one object". The session can reach one object.

### While they work

On the 900-second floor:

> Somebody always asks: why fifteen minutes? Why not thirty seconds?
>
> Because AWS says no. Nine hundred seconds is the STS minimum. STS is the
> Security Token Service — it is the thing that issues temporary credentials. You
> cannot go below it. That is not a design choice in our code, it is a constraint
> we inherit.

### The revoke beat (4 min) — do not rush this

Stop the room for this one.

> Look at `revoke`. Read what it does.
>
> It does nothing. It writes a log line and returns.

**⚑ LAND THIS:**

> AWS STS cannot revoke a credential. Once `assume_role` has returned, those keys
> work until they expire, and there is no API call that takes them back. None.
>
> So we have a method called `revoke` that cannot revoke. And the honest thing —
> the only honest thing — is to write that in the docstring in plain language,
> where the next person will see it.
>
> The dangerous version of this code is the one where `revoke` is empty and
> nobody wrote down why. Then somebody reads the method name, believes it, and
> designs a system around a control that does not exist.

Then ask the room:

> If you cannot revoke, what have you actually got? There are three controls.
> Two of them are on the slide. Give me the third.

Expected answers: the TTL, the scope. The one they miss:

> Delete the source object after you process it. Then the credential points at
> something that no longer exists for the rest of its life.
>
> That is the strongest of the three, and it is the one almost nobody says.

### Closing Module B (3 min)

> You have a working broker. It issues a credential scoped to one object.
>
> And you have a green test proving that credential can read its object.

Set the trap. Say this flatly, with no emphasis, and move straight to the break:

> Hold on to that. We are going to look at it again after Module C.

---

## Module C — the clean room (1:50–2:10)

### Setting up (3 min)

> `tutorial/clean_room.py`. About ten lines. Two `transaction_scope` blocks with
> the tokenizer in between.
>
> Read a record using a read credential. Tokenize it. Write it using a *different*
> credential — a write credential.

Pre-empt the obvious objection:

> Somebody is about to ask why we do not just use one credential for both. It
> would be less code. It would work.
>
> Because a read credential that can also write is a credential that can
> exfiltrate. And a write credential that can also read is a credential that can
> pull the source back out. Two credentials, two blast radii, both tiny.

### The tokenizer (2 min)

> The tokenizer is twenty lines of standard library. It hashes the name, the
> medical record number, and the date of birth.
>
> It is not de-identification. I want to be precise about that, because in a
> healthcare context the word matters. It is a stand-in, so the *shape* of the
> pipeline is real while the hard problem stays out of the room.

### The beat most facilitators would skip (4 min) — do not skip it

Around 2:05, once most people are green:

> Everyone with green tests — I want to show you something about your green
> tests.
>
> Suppose you had opened the transaction scope, got your credential, and then
> ignored it. Suppose you built a plain `boto3.client("s3")` instead and used
> that.

**⚑ LAND THIS:**

> Every single one of your twelve tests would still pass.
>
> I checked. The record gets tokenized, it lands in the clean bucket, the suite
> is green. The credential you carefully scoped is sitting there unused.
>
> That is a one-line bug, it is invisible in code review, and your tests do not
> see it.

Then hand straight over to Module D:

> Hold that thought. Take a two minute stretch, and then we are going to find out
> why.

---

## Module D — the IAM trap (2:10–2:45)

This is the module the tutorial exists for. Everything before it was setup.

### Beat 1 — the false comfort (5 min)

> I want you to break your own code. On purpose. Everybody, at the same time.
>
> Open `tutorial/broker.py`, find `_build_policy`, and find the line that says
> `"Resource": [resource]`.
>
> Change it to `"Resource": ["*"]`.
>
> A star. That policy now grants access to every object in the account.

Wait for the room.

> Now run your Module B tests again. `pytest tests/test_b_broker.py`.

Wait. Let them see it themselves. Do not narrate.

> Fifteen passed.

**Now stop.** Do not explain. Ask:

> So what did your Module B tests actually prove?

Count to ten this time. Someone will get there. The answer you are steering to:

> They proved that `assume_role` returns keys. That is all they proved. Not one
> of those fifteen tests said anything about scope.

### Beat 2 — the unwritable test (10 min)

> Fine. Let us write the test that catches it. It is obvious, right? Issue a
> credential for one object. Try to read a *different* object. Expect
> AccessDenied.
>
> Try it. Genuinely try it, before you look at the file.

Let them fail for a few minutes. Then:

> Nobody can make it pass. Now put your `Resource` line back — fix the policy,
> make it correct again — and run it one more time.

**⚑ LAND THIS** — this is the peak of the tutorial:

> It still fails.
>
> The test fails **with a correct policy**. moto hands out credentials that can
> do anything, so the cross-object read succeeds and AccessDenied never happens.
>
> There is no version of that test that works. Not a better assertion, not a
> different fixture. Behavioural IAM tests against moto are not weak.
>
> **They are unwritable.**

Then, immediately, so nobody leaves demoralised:

> Which is why that test is in your repository marked `xfail`, permanently, with
> a paragraph explaining why. It is documentation that runs.

Mention the canary — it takes fifteen seconds and it is good engineering:

> It is marked `strict`. If moto ever starts enforcing session policies, that
> test passes, strict mode turns the unexpected pass into a failure, and whoever
> runs the suite that day is forced to come and read the explanation. That beats
> a comment nobody re-reads.

### Beat 3 — the fix (12 min)

> You cannot make moto enforce the policy. So stop trying to test the behaviour.
> **Test the document.**
>
> Call `_build_policy` directly. Assert exactly one statement. Exactly one
> action. The resource is exactly the one ARN. And no star anywhere in the
> document.

Once they are green, the payoff — make them do it, do not demo it:

> Now break it again. Put the star back, and run Module D.

> Six failures. By name. Telling you exactly what you widened.
>
> **That is the test Module B should have had.**

Then the spy test:

> One more. A perfect `_build_policy` is worthless if somebody refactors `issue`
> and drops the `Policy` argument. Nothing else in your suite would notice,
> because moto ignores it either way. So we spy on the call and assert the
> document actually arrives.

Now close the Module C loop:

> And this is the answer to what I showed you at the end of Module C. The reason
> your tests could not catch an unused credential is the same reason they could
> not catch a wildcard. moto does not evaluate authorization. It never did.

### Beat 4 — the honest boundary (8 min)

Slides only. No typing.

> There is one test in this repository that actually proves the scope works. It
> is marked `aws_integration`, it needs a real account, and it is deselected by
> default. In CI it runs in a separate job, gated on secrets.
>
> On a fork, or on your clone, that job **skips**. It does not fail.

> That distinction matters more than it looks. A job that fails on forks trains
> everybody to ignore red CI. A job that skips keeps red meaningful.

**⚑ LAND THIS** — the sentence you want them to repeat at work:

> moto verifies that your code calls AWS correctly. It does not verify that AWS
> would allow the call.
>
> Those are different claims. Only one of them is what an auditor is asking
> about.
>
> Say that out loud in your next design review.

---

## 2:45–3:00 — The finale

### The swap (5 min)

> Last thing. Run this.
>
> `git checkout checkpoint-d`
> `pip install -e ".[finale]"`
> `pytest tests/test_e_finale.py`

> Fifteen passed. Every test ran twice.
>
> Once against the broker you wrote this afternoon. Once against a library on
> PyPI called pymayfly.

**⚑ LAND THIS:**

> Same constructor. Same methods. The policy document is identical, byte for
> byte. The only difference in the entire API is that its session names start
> with "mayfly" and yours start with "tutorial" — and there is a test asserting
> even that.
>
> I did not show you that library. You derived it.
>
> That is the actual lesson. Once you know what identity per transaction has to
> do, the shape of the code is forced. There was only one reasonable answer and
> you all found it.

### Honest status (2 min)

Do not soften any of this:

> Since I wrote that library, I should tell you what it is and is not.
>
> It is pilot-validated. A penetration test is pending. It has been used in a
> pilot under FedRAMP constraints. It is **not** FedRAMP-authorized. It is
> version 0.2.0, which is early.
>
> If you adopt it, read the source first. It is small enough to read in an
> afternoon — you just rebuilt most of it.

### What to do on Monday (2 min)

> Four steps, in this order, and the order matters.
>
> One: find one pipeline holding a long-lived key. Two: write the structural
> tests against the policy you already have — that is an hour, and it will find
> something. Three: add one gated integration test for the negative case. Four:
> *then* swap in per-transaction credentials.
>
> Tests before refactor. Otherwise you will not know which change broke it.

> Everything is in `docs/WRAP_UP.md`, including where moto stops and what
> Presidio would do for the free-text problem we skipped.
>
> Thank you. Questions.

---

## Q&A — prepared answers

**"Why not just use IAM roles per service?"**
> Because the blast radius is the service's whole lifetime and everything it was
> ever allowed to do. Per-transaction makes it one object and fifteen minutes.

**"Isn't 900 seconds still a long time?"**
> Yes. It is the floor STS gives you, and I would take thirty seconds if I could.
> That is why scope and source deletion are the other two controls. If you truly
> need shorter, you need a provider with revocable leases — Vault, for example.

**"Does this work with Lambda?"**
> Yes. Same shape. pymayfly wraps it in a decorator for handlers, but there is
> nothing magic in it.

**"What about cost?"**
> `assume_role` is free. Watch your call volume for rate limits, not your bill.

**"Isn't a hash reversible if you guess the value?"**
> Yes, if you have the salt. A token is a pseudonym, not anonymity. That is in
> the tokenizer docstring, and it is why the salt is a secret.

**"Why not Presidio?"**
> Because it needs spaCy and a model download, and it would have cost us twenty
> minutes of installation to teach nothing about zero trust. It is the right
> answer in production. `WRAP_UP.md` has the path.

**Anything you do not know:**
> I do not know. Find me in the hallway and we will look it up together.

Do not guess in front of the room. This is a security topic and a confident
wrong answer travels further than a correct one.
