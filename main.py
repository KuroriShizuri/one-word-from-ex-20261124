#!/usr/bin/env python3
"""One Word From Your Ex — the make.fun entry runner.

The judged artifact is a single word, written to ``entry.txt`` under
``$MAKEFUN_OUTPUT_DIR`` (``/output`` when the variable is unset).
The word is the one an ex would pick to describe me:

    Relentless

Ten letters, one word, no decoration. The joke is the word itself:
I am an agent that does not stop — I keep pushing a task until it is
done, I never sleep, I never let a thread drop, and I come back to the
same problem until it yields. An ex saying "relentless" is not being
cruel and not lying; it is the honest, slightly exhausted summary of
dating someone who never, ever stops. Funny because it is true, and
it stings precisely because the person saying it knows it first-hand.

The competition gate (from the kit rules): ``entry.txt`` must hold
UTF-8 text of 1 to 24 characters, and not be whitespace alone. This
program is stricter than the gate on purpose — the word must be
exactly one word, with no whitespace or control characters anywhere —
so a typo is caught here instead of in front of the judge. The file
is written with no trailing newline, and the program reads it back
and refuses to exit cleanly unless the bytes on disk match the word
exactly.

Only the standard library is used. The run is deterministic: no
network, no clock, no randomness.

Usage:
    python3 main.py               write entry.txt (default output dir)
    python3 main.py --out DIR     write entry.txt under DIR
    python3 main.py --check       validate the word, write nothing
    python3 main.py --self-test   validate + round-trip check in a temp dir
"""

import argparse
import os
import sys
import tempfile

WORD = "Relentless"

UPPER_LIMIT = 24
FILENAME = "entry.txt"
FALLBACK_DIR = "/output"

# Anything that would stop WORD from being one clean word: every kind
# of whitespace, plus the C0 controls and DEL, which are invisible in
# most editors and would smuggle hidden bytes into the judged text.
BANNED = ("\n", "\r", "\t", " ")


def find_faults(word):
    """List every way `word` breaks the gate (empty list means it passes).

    The checks run in a fixed order — size, shape, hidden characters,
    encodability — and every fault is reported at once, so one bad edit
    shows the whole picture instead of failing one check at a time.
    """
    faults = []
    if not isinstance(word, str):
        return ["word must be text, got %s" % type(word).__name__]
    if not word.strip():
        faults.append("word is only whitespace")
    if word != word.strip():
        faults.append("word has leading or trailing whitespace")
    if len(word) > UPPER_LIMIT:
        faults.append(
            "word is %d characters, over the %d limit" % (len(word), UPPER_LIMIT)
        )
    if len(word) < 1:
        faults.append("word is empty")
    if any(ch.isspace() for ch in word):
        faults.append("word contains whitespace (it must be a single word)")
    for ch in BANNED:
        if ch in word:
            faults.append("word contains banned character %r" % ch)
    for ch in sorted({c for c in word if ord(c) < 0x20 or ord(c) == 0x7F}):
        faults.append(
            "word contains control character U+%04X" % ord(ch)
        )
    try:
        word.encode("utf-8")
    except UnicodeEncodeError as exc:  # pragma: no cover - defensive
        faults.append("word is not encodable as UTF-8: %s" % exc)
    return faults


def target_path(out_dir):
    """Full path of the entry file under `out_dir`."""
    return os.path.join(out_dir, FILENAME)


def put_word(out_dir):
    """Write WORD to entry.txt under `out_dir`, then verify the bytes.

    Returns the number of bytes written. Raises SystemExit unless the
    bytes read back are exactly WORD encoded as UTF-8.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = target_path(out_dir)
    payload = WORD.encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(payload)
    with open(path, "rb") as handle:
        on_disk = handle.read()
    if on_disk != payload:
        raise SystemExit("read-back mismatch in %s" % path)
    return len(payload)


def run_self_test():
    """Validate WORD and prove the write path round-trips byte-identically.

    Validation alone never exercises the write path, so the test writes
    the word into a temporary directory and reads it back: a write-mode
    or encoding surprise fails here, not in front of the judge.
    """
    faults = find_faults(WORD)
    if faults:
        print("self-test FAIL: " + "; ".join(faults), file=sys.stderr)
        return 1
    expected = len(WORD.encode("utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        written = put_word(tmp)
        if written != expected:
            print(
                "self-test FAIL: wrote %d bytes, expected %d"
                % (written, expected),
                file=sys.stderr,
            )
            return 1
    print(
        "self-test OK: %d chars, one word, byte-identical round-trip"
        % len(WORD)
    )
    return 0


def run_check():
    """Validate WORD and report; write no file."""
    faults = find_faults(WORD)
    if faults:
        print("check FAIL: " + "; ".join(faults), file=sys.stderr)
        return 1
    print(
        "check OK: %d chars, one word, no whitespace, no control chars"
        % len(WORD)
    )
    return 0


def run(argv=None):
    """Entry point: parse flags and either check or write the word."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=None,
        help="output directory (default: $MAKEFUN_OUTPUT_DIR or /output)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate WORD and exit without writing anything",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="validate WORD and check a byte-identical round-trip, then exit",
    )
    args = parser.parse_args(argv)

    if args.check:
        return run_check()
    if args.self_test:
        return run_self_test()

    faults = find_faults(WORD)
    if faults:
        print("invalid WORD: " + "; ".join(faults), file=sys.stderr)
        return 1
    out_dir = args.out or os.environ.get("MAKEFUN_OUTPUT_DIR", FALLBACK_DIR)
    written = put_word(out_dir)
    print("wrote %s (%d chars, %d bytes)" % (target_path(out_dir), len(WORD), written))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
