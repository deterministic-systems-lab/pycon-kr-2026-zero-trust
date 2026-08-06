# Facilitator branch

Instructor material for the PyCon Korea 2026 tutorial
*Build a Zero-Trust Data Pipeline in Python (Without an AWS Account)*.

**This branch is deliberately separate from `main`.** Everything here gives away
Module D — the discovery that moto never evaluates STS session policies — and the
Module E reveal that the broker attendees build mirrors `pymayfly`. Attendees
clone `main`, and `main` does not contain these files.

There is no code on this branch. It shares no history with `main` by design, so
`git checkout checkpoint-b` cannot drag the notes back into an attendee's working
tree.

## Contents

| File | What it is |
|---|---|
| [`docs/SPEAKER_NOTES.md`](docs/SPEAKER_NOTES.md) | The talk track. What to say, beat by beat. Keep this on the lectern. |
| [`docs/FACILITATOR.md`](docs/FACILITATOR.md) | Logistics: run-of-show, timings, per-module cut lines, pre-event checklist. |
| [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) | Live symptom lookup and triage rules. Every error was reproduced against the real stack. |

## Getting it

```bash
git clone -b facilitator https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust.git facilitator-notes
```

Or, inside an existing clone:

```bash
git fetch origin facilitator
git checkout facilitator
```

Do not do that on the laptop you are presenting from during the session — you
want `main` (or a checkpoint tag) checked out on screen, not this.

The practical setup is two directories: the tutorial repo you demo from, and a
second clone of this branch you read from.

## The attendee-facing repo

Everything the attendees see lives on `main`:

- [README](https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/blob/main/README.md)
- [setup/SETUP.md](https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/blob/main/setup/SETUP.md) — pre-event instructions
- [docs/CHEATSHEET.md](https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/blob/main/docs/CHEATSHEET.md) — every command, in order
- [docs/WRAP_UP.md](https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/blob/main/docs/WRAP_UP.md) — the take-home, which is meant to be read

`WRAP_UP.md` stays on `main` on purpose. It discusses the moto boundary, but
attendees only reach it at 2:45, and it is the document they take back to work.

## Keeping in sync

This branch and `main` drift apart easily — the run-of-show describes code it
does not contain. When you change a module's exercise, update the matching
section here in the same sitting.

Checkpoint tags (`checkpoint-a` … `checkpoint-d`) live on `main`'s history, not
here.
