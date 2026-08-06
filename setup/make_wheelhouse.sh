#!/usr/bin/env bash
# Build the offline wheelhouse.
#
# Facilitator runs this before the conference, with network. Attendees never do.
#
#   ./setup/make_wheelhouse.sh
#
# Collects wheels for every platform in the room: macOS arm64 (Apple Silicon),
# macOS x86_64 (Intel), manylinux x86_64, and Windows amd64. Everything in this
# stack ships pure-Python or universal wheels, so the result is small.
#
# If wheels/ comes out under 30 MB, commit it. If it is larger, zip it and
# attach it to a GitHub Release as wheelhouse.zip — setup/SETUP.md covers both.

set -euo pipefail

PYTHON_VERSION="3.12"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEEL_DIR="${REPO_ROOT}/wheels"

# Keep this list in step with [project.dependencies] in pyproject.toml.
# pymayfly is deliberately absent — it is the finale, and needs network on purpose.
PACKAGES=(
  "boto3==1.43.65"
  "botocore==1.43.65"
  "moto[s3,sts]==5.2.2"
  "pytest==9.1.1"
)

PLATFORMS=(
  "macosx_11_0_arm64"
  "macosx_10_9_x86_64"
  "manylinux2014_x86_64"
  "win_amd64"
)

rm -rf "${WHEEL_DIR}"
mkdir -p "${WHEEL_DIR}"

echo "Building wheelhouse for Python ${PYTHON_VERSION}"

# Pass 1: platform-specific binary wheels.
for platform in "${PLATFORMS[@]}"; do
  echo "  -> ${platform}"
  pip download "${PACKAGES[@]}" \
    --dest "${WHEEL_DIR}" \
    --python-version "${PYTHON_VERSION}" \
    --platform "${platform}" \
    --only-binary=:all: \
    --quiet
done

# Pass 2: anything that ships sdist-only. --only-binary above skips those, so a
# second unconstrained pass catches them for the local platform. If this pass
# downloads a .tar.gz, that dependency will need a compiler on the attendee's
# machine — investigate before the conference, do not ship it.
pip download "${PACKAGES[@]}" --dest "${WHEEL_DIR}" --quiet

if compgen -G "${WHEEL_DIR}/*.tar.gz" > /dev/null; then
  echo
  echo "WARNING: source distributions in the wheelhouse:"
  ls -1 "${WHEEL_DIR}"/*.tar.gz
  echo "These need a build toolchain on the attendee's laptop. Fix before shipping."
fi

echo
echo "Wheels:  $(find "${WHEEL_DIR}" -type f | wc -l | tr -d ' ')"
echo "Size:    $(du -sh "${WHEEL_DIR}" | cut -f1)"
echo
echo "Now verify offline: disable networking, then"
echo "  rm -rf .venv && python3.12 -m venv .venv"
echo "  ./setup/install_offline.sh"
echo "  .venv/bin/pytest tests/test_00_smoke.py"
