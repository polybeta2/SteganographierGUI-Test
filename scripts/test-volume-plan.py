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


def test_single_volume_pack(module):
    entries = [("p1", "root/a.bin", 400), ("p2", "root/b.bin", 500)]
    plan = module.plan_volumes(entries, [10000], chunk_min_bytes=100, entry_overhead=lambda n: 0)
    assert_equal(len(plan["volumes"]), 1, "volume count")
    kinds = [p["kind"] for p in plan["volumes"][0]["pieces"]]
    assert_equal(kinds, ["whole", "whole"], "piece kinds")
    assert_equal(plan["chunked"], {}, "no chunked files")
    assert_equal(plan["volumes"][0]["estimated_zip_size"], 900, "estimated size")
    print("  ok   single volume pack")


def test_roll_whole_file_to_next_volume(module):
    # 当前卷剩余 40，文件 80 装不下当前卷但装得下新卷 -> 整装滚动
    entries = [("p1", "root/a.bin", 60), ("p2", "root/b.bin", 80)]
    plan = module.plan_volumes(entries, [100], chunk_min_bytes=50, entry_overhead=lambda n: 0)
    assert_equal(len(plan["volumes"]), 2, "volume count")
    assert_equal([p["arcname"] for p in plan["volumes"][1]["pieces"]], ["root/b.bin"], "rolled whole")
    assert_equal(plan["chunked"], {}, "nothing chunked")
    print("  ok   roll whole file to next volume")


def test_chunk_oversized_file(module):
    entries = [("p1", "big.bin", 250)]
    plan = module.plan_volumes(entries, [100], chunk_min_bytes=10, entry_overhead=lambda n: 0)
    volumes = plan["volumes"]
    assert_equal(len(volumes), 3, "volume count")
    parts = [volumes[i]["pieces"][0]["arcname"] for i in range(3)]
    assert_equal(parts, ["big.bin.001", "big.bin.002", "big.bin.003"], "part names")
    lengths = [volumes[i]["pieces"][0]["length"] for i in range(3)]
    assert_equal(lengths, [100, 100, 50], "part lengths")
    offsets = [volumes[i]["pieces"][0]["offset"] for i in range(3)]
    assert_equal(offsets, [0, 100, 200], "part offsets")
    assert_equal(plan["chunked"], {"big.bin": ["big.bin.001", "big.bin.002", "big.bin.003"]}, "chunked map")
    print("  ok   chunk oversized file")


def test_chunk_skips_dust_remainder(module):
    # A 占掉 90/100，剩 10 < chunk_min=50：B 不应从残区开始切，改从新卷开始
    entries = [("p1", "root/a.bin", 90), ("p2", "big.bin", 150)]
    plan = module.plan_volumes(entries, [100], chunk_min_bytes=50, entry_overhead=lambda n: 0)
    volumes = plan["volumes"]
    assert_equal(len(volumes), 3, "volume count")
    assert_equal([p["arcname"] for p in volumes[0]["pieces"]], ["root/a.bin"], "volume 1 only A")
    assert_equal(volumes[1]["pieces"][0]["length"], 100, "B.001 fills volume 2")
    assert_equal(volumes[2]["pieces"][0]["length"], 50, "B.002 tail in volume 3")
    print("  ok   chunk skips dust remainder")


def test_periodic_budgets(module):
    entries = [("p1", "big.bin", 500)]
    plan = module.plan_volumes(entries, [100, 200], chunk_min_bytes=10, entry_overhead=lambda n: 0)
    lengths = [vol["pieces"][0]["length"] for vol in plan["volumes"]]
    assert_equal(lengths, [100, 200, 100, 100], "periodic budgets")
    print("  ok   periodic budgets")


def test_budget_offset_rotates_cycle(module):
    entries = [("p1", "big.bin", 300)]
    plan = module.plan_volumes(entries, [100, 200], chunk_min_bytes=10, budget_offset=1, entry_overhead=lambda n: 0)
    lengths = [vol["pieces"][0]["length"] for vol in plan["volumes"]]
    assert_equal(lengths, [200, 100], "rotated budgets")
    print("  ok   budget offset rotates cycle")


def test_first_file_oversized_starts_in_first_volume(module):
    entries = [("p1", "big.bin", 250)]
    plan = module.plan_volumes(entries, [100, 100, 100], chunk_min_bytes=10, entry_overhead=lambda n: 0)
    assert_equal(plan["volumes"][0]["pieces"][0]["arcname"], "big.bin.001", "first chunk in first volume")
    print("  ok   first file oversized starts in volume 1")


def main():
    module = load_module()
    print("parse_size_to_bytes")
    test_parse_size_to_bytes(module)
    print("plan_volumes")
    test_single_volume_pack(module)
    test_roll_whole_file_to_next_volume(module)
    test_chunk_oversized_file(module)
    test_chunk_skips_dust_remainder(module)
    test_periodic_budgets(module)
    test_budget_offset_rotates_cycle(module)
    test_first_file_oversized_starts_in_first_volume(module)
    print("Volume-plan tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
