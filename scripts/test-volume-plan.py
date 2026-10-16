"""Tests for the volume-splitting planner and size parsing.

Pure-logic tests, no archives are produced. Runs on Python 3.8+ (CI).
"""

import importlib.util
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(REPO_ROOT, "Steganographier.py")


def load_module():
    spec = importlib.util.spec_from_file_location("steganographier_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError("%s: got %r, expected %r" % (label, actual, expected))


def test_parse_size_to_bytes(module):
    cases = [
        ("4G", 4 * 1024 ** 3),
        ("4096M", 4096 * 1024 ** 2),
        ("512", 512 * 1024 ** 2),
        (" 4g ", 4 * 1024 ** 3),
        ("1m", 1 * 1024 ** 2),
    ]
    for text, expected in cases:
        assert_equal(module.parse_size_to_bytes(text), expected, "parse %r" % text)
    for bad in ("4X", "", "0", "-1", "abc", "4.5G"):
        try:
            module.parse_size_to_bytes(bad)
        except ValueError:
            continue
        raise AssertionError("parse %r should raise ValueError" % bad)
    print("  ok   parse_size_to_bytes")


def main():
    module = load_module()
    print("parse_size_to_bytes")
    test_parse_size_to_bytes(module)
    print("Volume-plan tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
