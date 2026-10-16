"""End-to-end tests for automatic volume splitting (independent-zip mode).

Fixtures are small (cap 32 MB, ~40 MB payload) so a full run takes seconds.
Requires the bundled tools/7z.exe (with its 7z.dll). Runs on Python 3.8+ (CI).
"""

import importlib.util
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(REPO_ROOT, "Steganographier.py")
SEVEN_ZIP = os.path.join(REPO_ROOT, "tools", "7z.exe")
CAP_BYTES = 32 * 1024 * 1024


def load_module():
    spec = importlib.util.spec_from_file_location("steganographier_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.application_path = REPO_ROOT  # __main__ 之外的装载方式需要手动补给
    return module


def make_fixture(root, case_name):
    """每个用例使用独立子目录，避免共享 work_root 时互相污染。"""
    base = os.path.join(root, case_name)
    payload = os.path.join(base, "payload")
    os.makedirs(payload)
    for name, size in (("a.bin", 1 << 20), ("b.bin", 2 << 20), ("big.bin", 36 << 20)):
        with open(os.path.join(payload, name), "wb") as handle:
            handle.write(os.urandom(size))
    covers = os.path.join(base, "covers")
    os.makedirs(covers)
    for name in ("c1.mp4", "c2.mp4", "c3.mp4"):
        with open(os.path.join(covers, name), "wb") as handle:
            handle.write(os.urandom(64 * 1024))
    return payload, covers


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_video(video_path, dest_dir, password=None):
    """接收端路径：改后缀为 .zip 后两步解压（与程序 reveal 的 7z-#号模式 流程一致）。

    第一步 `x -t#` 扫描式识别，把内嵌的 `<N>.zip` 原样倒到暂存区；
    第二步解压该 zip 得到真实内容。
    """
    os.makedirs(dest_dir, exist_ok=True)
    renamed = os.path.join(dest_dir, "_in.zip")
    shutil.copy(video_path, renamed)
    stage = os.path.join(dest_dir, "_stage")
    os.makedirs(stage, exist_ok=True)
    cmd = [SEVEN_ZIP, "x", "-y", "-t#", "-o" + stage, renamed]
    if password:
        cmd.append("-p" + password)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AssertionError("7z #-scan failed for %s:\n%s" % (video_path, result.stdout + result.stderr))
    os.remove(renamed)
    embedded = [os.path.join(stage, name) for name in os.listdir(stage)
                if name.lower().endswith(".zip")]
    if not embedded:
        raise AssertionError("no embedded .zip recovered from %s: %r" % (video_path, os.listdir(stage)))
    cmd = [SEVEN_ZIP, "x", "-y", "-o" + dest_dir, embedded[0]]
    if password:
        cmd.append("-p" + password)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AssertionError("7z failed to extract embedded zip of %s:\n%s" % (video_path, result.stdout + result.stderr))
    shutil.rmtree(stage, ignore_errors=True)
    return dest_dir


def run_cli(args, cwd):
    result = subprocess.run([sys.executable, MODULE_PATH] + args,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=cwd)
    if result.returncode != 0:
        raise AssertionError("CLI failed: %s\n%s" % (args, result.stdout + result.stderr))
    return result


def test_mode_zip_chunks_big_file(module, work_root):
    payload, covers = make_fixture(work_root, "t1")
    steg = module.Steganographier(video_folder_path=covers, gui_enabled=False,
                                  password_file=os.path.join(work_root, "PW.txt"),
                                  enable_log_file=False, version="test")
    summary = steg.hide_volumized(payload, CAP_BYTES, password="pw123",
                                  type_option_var="mp4", video_folder_path=covers)
    if summary["volumes"] < 2:
        raise AssertionError("expected >=2 volumes, got %d" % summary["volumes"])
    if list(summary["chunked"]) != [os.path.join("payload", "big.bin")]:
        raise AssertionError("expected payload/big.bin chunked, got %r" % summary["chunked"])

    merged = {}
    seen_notes = 0
    for index, output in enumerate(summary["outputs"], 1):
        if os.path.getsize(output) > CAP_BYTES:
            raise AssertionError("volume %d exceeds cap: %d" % (index, os.path.getsize(output)))
        dest = os.path.join(work_root, "extract_%d" % index)
        extract_video(output, dest, password="pw123")
        for dirpath, _dirs, files in os.walk(dest):
            for name in files:
                if name == "合并说明.txt":
                    seen_notes += 1
                    continue
                merged[name] = os.path.join(dirpath, name)
    for name, _size in (("a.bin", 1 << 20), ("b.bin", 2 << 20)):
        if sha256_of(merged[name]) != sha256_of(os.path.join(payload, name)):
            raise AssertionError("%s content mismatch" % name)
    part_files = sorted(n for n in merged if n.startswith("big.bin."))
    if part_files != ["big.bin.001", "big.bin.002"]:
        raise AssertionError("unexpected parts: %r" % part_files)
    with open(merged["big.bin.001"], "ab") as out:
        with open(merged["big.bin.002"], "rb") as src:
            out.write(src.read())
    if sha256_of(merged["big.bin.001"]) != sha256_of(os.path.join(payload, "big.bin")):
        raise AssertionError("merged big.bin mismatch")
    if seen_notes == 0:
        raise AssertionError("合并说明.txt missing")
    print("  ok   mode zip: %d volumes, big.bin split + merge verified" % summary["volumes"])


def test_mode_zip_via_cli_and_reveal(module, work_root):
    payload, covers = make_fixture(work_root, "t2")
    base = os.path.dirname(payload)   # 输出落在输入的同级目录
    run_cli(["-i", payload, "--volume-size", "32M", "--no-log", "-c", os.path.join(covers, "c1.mp4")],
            cwd=work_root)
    outputs = sorted(name for name in os.listdir(base)
                     if re.search(r"_\d+of\d+\.mp4$", name))
    if len(outputs) < 2:
        raise AssertionError("CLI produced %r" % outputs)
    # 卷内文件顺序是随机打乱的，a.bin 不一定在第一卷：逐卷移位后解除隐写，取并集断言
    found = None
    for index, name in enumerate(outputs, 1):
        target = os.path.join(work_root, "t2reveal%d" % index)
        os.makedirs(target)
        shutil.move(os.path.join(base, name), os.path.join(target, name))
        run_cli(["-i", os.path.join(target, name), "-r", "--no-log"], cwd=work_root)
        for dirpath, _dirs, files in os.walk(target):
            if "a.bin" in files:
                found = os.path.join(dirpath, "a.bin")
    if not found:
        raise AssertionError("a.bin was not revealed from any volume")
    if sha256_of(found) != sha256_of(os.path.join(payload, "a.bin")):
        raise AssertionError("revealed a.bin mismatch")
    print("  ok   mode zip via CLI + reveal roundtrip")


def test_without_volume_flags_unchanged(module, work_root):
    payload, covers = make_fixture(work_root, "t3")
    base = os.path.dirname(payload)
    run_cli(["-i", payload, "--no-log", "-c", os.path.join(covers, "c1.mp4")], cwd=work_root)
    outputs = [name for name in os.listdir(base)
               if name.startswith("payload_hidden") and name.endswith(".mp4")]
    expected = [name for name in outputs if "_1of" not in name]
    if not expected:
        raise AssertionError("expected a single non-volume output, got %r" % outputs)
    print("  ok   regression: single-volume path unchanged")


def main():
    module = load_module()
    work_root = tempfile.mkdtemp(prefix="steg-volume-test-")
    try:
        test_mode_zip_chunks_big_file(module, work_root)
        test_mode_zip_via_cli_and_reveal(module, work_root)
        test_without_volume_flags_unchanged(module, work_root)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    print("Volume-mode tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
