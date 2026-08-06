# Wrap-up: where this stops

You built a working Identity-Per-Transaction broker and a clean room, and you
tested both offline. This page is the honest accounting of what you have and what
you do not.

---

## 1. Where moto stops

moto verifies **your code calls AWS correctly**. It does not verify **AWS would
allow the call**. Those are different claims and only one of them is what an
auditor is asking about.

Specifically, moto does not evaluate:

- STS inline session policies (Module D)
- IAM role and identity policies
- Resource policies — bucket policies, KMS key policies
- SCPs, permission boundaries, VPC endpoint policies

Everything on that list is authorization. moto's job is API shape, not
authorization. That is a reasonable design decision by the moto maintainers, and
it becomes a problem only when someone reads a green test suite as evidence that
their permissions are tight.

**The rule to take home:** a green moto suite proves your integration works. It
proves nothing whatsoever about your blast radius.

### What to do instead

| Question | Tool |
|---|---|
| Is the policy document what I meant to write? | Structural unit tests (Module D) |
| Did the policy reach the API call? | Spy test on `assume_role` (Module D) |
| Would AWS actually deny this? | Real AWS, gated integration job |
| Would AWS deny this, before I deploy? | [IAM Access Analyzer policy validation](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html), `iam simulate-custom-policy` |

`simulate-custom-policy` is worth knowing about: it evaluates a policy document
against a request without performing the request. It needs an account but not a
real object, and it is much cheaper than a full integration environment.

---

## 2. The gated integration job

`test_cross_object_read_is_denied_on_real_aws` is marked
`@pytest.mark.aws_integration` and deselected by default in `pyproject.toml`:

```toml
addopts = "-m 'not aws_integration'"
```

In CI it runs in a separate job that is gated on secrets being present. Forks and
attendee clones have no secrets, so the job is skipped, not failed. See
`.github/workflows/ci.yml`.

This matters more than it looks. A gate that *fails* on forks trains everybody to
ignore red CI. A gate that *skips* keeps red meaningful.

That one test is the only place in this repository where scope enforcement is
actually proven. Everything else is a proxy for it. Be honest about that when you
write the design doc.

---

## 3. The xfail canary

The naive negative test stays in the suite permanently, marked
`xfail(strict=True)`. It documents a fact about the tooling, in executable form.

If moto ever starts enforcing session policies, that test will pass, `strict=True`
turns an unexpected pass into a failure, and whoever runs the suite that day is
forced to come and read the docstring. An `xfail` you can delete when the world
changes is worth more than a comment nobody re-reads.

---

## 4. The tokenizer is not de-identification

`tutorial/tokenizer.py` replaces `name`, `mrn` and `dob` with salted SHA-256
tokens. Two gaps, both deliberate, both asserted by tests in
`test_c_clean_room.py`:

**Free text is untouched.** Record R-002's note says "Bramble Voss tolerating
current antihistamine well." The `name` field is tokenized. The name in the note
went to the clean bucket in the clear. `test_free_text_leaks_the_name_and_that_is_the_known_gap`
asserts exactly that, on purpose.

**A token is a pseudonym, not anonymity.** Anyone holding the salt can confirm any
value they can guess. The salt is the secret. Under HIPAA this is
limited-data-set territory at best, not Safe Harbor.

### The production path

[Microsoft Presidio](https://microsoft.github.io/presidio/) is the usual answer
for the free-text half: entity recognition over prose, with pluggable
anonymization. It brings spaCy and a model download, which is why it is not in
this repo — it would have cost 20 minutes of install time and taught nothing about
zero trust.

If you go that way, the shape stays the same. Presidio replaces
`tokenize_record`, and the broker, the scope and the clean room do not change.
That is the payoff of keeping de-identification behind one function.

---

## 5. pymayfly

The broker you wrote mirrors [`pymayfly`](https://pypi.org/project/pymayfly/)
0.2.0. Same constructor, same `issue`/`revoke`/`blast_radius`, same policy
document byte for byte. The only difference is the session-name prefix —
`tutorial-` versus `mayfly-` — and `test_e_finale.py` asserts that too.

You were not shown the library first. You derived it. The point is that once you
know what IPT has to do, the shape of the code is forced.

What pymayfly adds beyond what you built today:

- An audit ledger and provenance records per transaction — `transaction_scope`
  takes a `ledger` argument this tutorial dropped
- `IPTEnforcer` and the `@protect` decorator, for wrapping Lambda handlers
- GCS and Azure Blob brokers behind the same `IdentityBroker` interface
- Typed exceptions (`IPTBrokerError`, `IPTExpiredCredentialError`)

### Status, stated plainly

pymayfly is **pilot-validated. A penetration test is pending.** It has been used
in a pilot under FedRAMP constraints. It is not FedRAMP-authorized, it is not
certified, and neither is anything in this tutorial. Version 0.2.0 is early.

If you adopt it, read the source. It is small enough to read in an afternoon —
you just rebuilt most of it.

---

## 6. What to actually do on Monday

1. Find one pipeline holding a long-lived IAM user key. That is the highest-value
   target in your estate.
2. Write the structural tests first, against the policy you already have. They
   take an hour and they will find something.
3. Add one gated integration test for the negative case. One is enough to make
   the boundary real.
4. Only then swap in per-transaction credentials. Ordering matters: tests before
   refactor, or you will not know which change broke it.

---

## Links

- pymayfly — https://pypi.org/project/pymayfly/
- moto — https://github.com/getmoto/moto
- Presidio — https://microsoft.github.io/presidio/
- IAM session policies — https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session
- IAM Access Analyzer — https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html

Questions after the conference: open an issue on this repo.
