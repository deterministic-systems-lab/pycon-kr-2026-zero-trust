# Setup — do this before the session

**Time needed: 10 minutes. Do it at your hotel, not at the venue.**

The first ten minutes of the tutorial are a smoke-test gate, not an install
window. Conference wifi will not cooperate with 30 people running `pip install`
at once.

You need:

- Python **3.12**. Not 3.11, not 3.13.
- Git.
- A terminal.

You do **not** need an AWS account, AWS credentials, or a network connection
during the session.

---

## macOS and Linux

### 1. Check your Python

```bash
python3.12 --version
```

Expect `Python 3.12.x`. If the command is not found:

- **macOS:** `brew install python@3.12`
- **Ubuntu/Debian:** `sudo apt install python3.12 python3.12-venv`
- **Anything else:** https://www.python.org/downloads/

### 2. Get the repo

```bash
git clone https://github.com/deterministicsystemslab/pycon-kr-2026-zero-trust.git
cd pycon-kr-2026-zero-trust
```

### 3. Make a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Your prompt now starts with `(.venv)`. If it does not, the next steps will
install into the wrong place.

### 4. Install

**With network (do this if you can):**

```bash
pip install -e .
```

**Without network, or if the above is slow:** see
[Offline install](#offline-install) below.

### 5. Prove it works

```bash
pytest tests/test_00_smoke.py
```

Expected:

```
3 passed in 0.7s
```

**That is the whole requirement.** Three green tests and you are done.

---

## Windows

### 1. Check your Python

```powershell
py -3.12 --version
```

If it is missing, install 3.12 from https://www.python.org/downloads/ and tick
**"Add Python to PATH"** in the installer.

### 2. Get the repo

```powershell
git clone https://github.com/deterministicsystemslab/pycon-kr-2026-zero-trust.git
cd pycon-kr-2026-zero-trust
```

### 3. Make a virtual environment

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

If PowerShell refuses with an execution-policy error:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
```

### 4. Install

**With network:**

```powershell
pip install -e .
```

**Without network:** download `wheelhouse.zip` from the
[Releases page](https://github.com/deterministicsystemslab/pycon-kr-2026-zero-trust/releases),
unzip it into the `wheels\` folder, then:

```powershell
pip install --no-index --find-links wheels boto3==1.43.65 botocore==1.43.65 "moto[s3,sts]==5.2.2" pytest==9.1.1
```

### 5. Prove it works

```powershell
pytest tests\test_00_smoke.py
```

Expect `3 passed`.

---

## Offline install

Everything needed is in a wheelhouse — a folder of pre-downloaded packages. This
works from a USB stick with wifi switched off. Measured: 8.6 seconds.

1. Download `wheelhouse.zip` from the
   [Releases page](https://github.com/deterministicsystemslab/pycon-kr-2026-zero-trust/releases).
2. Unzip it so the `.whl` files sit directly in `wheels/`.
3. Run:

```bash
./setup/install_offline.sh
```

The script creates `.venv` if you have not, installs the four pinned packages,
and tells you what to run next. It never touches the network.

If you are at the venue and stuck, the facilitator has the wheelhouse on a USB
stick. Ask.

---

## When it does not work

**`pytest: command not found`**
Your virtual environment is not active. Run `source .venv/bin/activate`
(Windows: `.venv\Scripts\activate`) and try again.

**`test_python_version` fails**
You built the venv with the wrong Python. Delete and rebuild:

```bash
rm -rf .venv && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e .
```

**`ModuleNotFoundError: No module named 'tutorial'`**
Run pytest from the repository root, not from inside `tests/`.

**`test_imports` says moto must be 5.x**
An old moto is installed. `pip install -e . --force-reinstall`.

**Corporate laptop blocks pip**
Use the offline wheelhouse. That is what it is for.

---

## Still red?

Email the facilitator with the full output of:

```bash
python --version
pip list
pytest tests/test_00_smoke.py
```

Subject line: **PyCon KR zero-trust setup**. Do this before you travel — a reply
from a plane is unlikely.

Run this and email me if it isn't green: `pytest tests/test_00_smoke.py`
