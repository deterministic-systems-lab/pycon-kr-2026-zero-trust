#!/usr/bin/env bash
# Install everything from the local wheelhouse. No network needed.
#
#   ./setup/install_offline.sh
#
# Works from a USB stick copy of this repo with wifi off. That is the point.
# Windows: use setup/SETUP.md, which gives the PowerShell equivalent.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL_DIR="${REPO_ROOT}/wheels"

if [ ! -d "${WHEEL_DIR}" ] || [ -z "$(ls -A "${WHEEL_DIR}" 2>/dev/null)" ]; then
  cat >&2 <<'MSG'
No wheels found.

The wheelhouse ships either inside the repo (wheels/) or as wheelhouse.zip on
the GitHub Releases page. If you cloned and wheels/ is empty, download
wheelhouse.zip, unzip it into wheels/, and run this again.

  https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/releases

With network, you do not need any of this:  pip install -e .
MSG
  exit 1
fi

# Use the active venv if there is one, otherwise the repo's .venv.
#
# Always address pip by its absolute path inside the target environment. Calling
# a bare `pip` here would resolve through PATH, and on a laptop with conda or a
# system Python earlier in PATH that installs into the wrong environment — which
# is how you upgrade botocore underneath somebody's unrelated project.
if [ -n "${VIRTUAL_ENV:-}" ]; then
  VENV="${VIRTUAL_ENV}"
else
  VENV="${REPO_ROOT}/.venv"
  if [ ! -d "${VENV}" ]; then
    echo "Creating ${VENV}"
    python3.12 -m venv "${VENV}"
  fi
fi

PIP="${VENV}/bin/pip"
[ -x "${PIP}" ] || PIP="${VENV}/Scripts/pip.exe"   # Git Bash on Windows

if [ ! -x "${PIP}" ]; then
  echo "No pip found in ${VENV}. Recreate it: python3.12 -m venv ${VENV}" >&2
  exit 1
fi

echo "Target environment: ${VENV}"

# Pinned, and identical to [project.dependencies] in pyproject.toml. Bare package
# names would let pip call an older already-installed version "satisfied", and
# then the smoke test fails on a machine that looked like it installed fine.
echo "Installing from ${WHEEL_DIR} (no network)"
"${PIP}" install --no-index --find-links "${WHEEL_DIR}" --quiet \
  "boto3==1.43.65" "botocore==1.43.65" "moto[s3,sts]==5.2.2" "pytest==9.1.1"

# The tutorial package needs no install. pyproject.toml sets pythonpath = ["."]
# so pytest imports tutorial/ from the repo root — which keeps a build backend
# out of the offline path entirely.

echo
echo "Done. Now run:"
echo "  ${REPO_ROOT}/.venv/bin/pytest tests/test_00_smoke.py"
echo
echo "Three green tests means you are ready for the session."
