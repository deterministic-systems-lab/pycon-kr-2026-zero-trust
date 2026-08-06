# wheels/

The offline wheelhouse lands here. It is **not committed** — measured at build
time it is 46 MB unpacked, 45 MB zipped, which is past the point where it belongs
in git history.

## Attendees

Download `wheelhouse.zip` from the Releases page and unzip it into this
directory:

    https://github.com/deterministic-systems-lab/pycon-kr-2026-zero-trust/releases

Then run `setup/install_offline.sh`. Full instructions in
[`../setup/SETUP.md`](../setup/SETUP.md).

If you have working network, you do not need this at all:

    pip install -e .

## Facilitator

Rebuild before the conference, with network:

    ./setup/make_wheelhouse.sh
    cd wheels && zip -r ../wheelhouse.zip . && cd ..
    gh release upload <tag> wheelhouse.zip

Measured 2026-08-05: 41 wheels, 46 MB, covering macOS arm64, macOS x86_64,
manylinux2014 x86_64 and Windows amd64 on Python 3.12. Offline install from a
cold venv took 8.6 seconds; the 60-second budget has plenty of room.

Most of the bulk is `botocore` (15 MB) and four platform builds of
`cryptography` (~5 MB each). Neither is optional — botocore is boto3, and moto
pulls cryptography for STS.
