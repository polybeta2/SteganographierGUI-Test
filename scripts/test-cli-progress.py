"""Tests for the CLI progress reporter.

Covers: TTY single-line rendering on a fake stream, non-TTY 10% fallback,
phase switches, and log echo through a real CLI subprocess run.
Runs on Python 3.8+ (CI).
"""

import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_PATH = os.path.join(REPO_ROOT, "Steganographier.py")


def load_module():
    spec = importlib.util.spec_from_file_location("steganographier_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.application_path = REPO_ROOT
    return module


class FakeTty(io.StringIO):
    def isatty(self):
        return True


def test_tty_single_line_rendering(module):
    stream = FakeTty()
    reporter = module.CliProgressReporter(stream=stream)
    reporter.THROTTLE_SECONDS = 0  # 测试中去掉节流，保证每次 update 都渲染
    reporter.set_phase("压缩中")
    reporter.update(1 << 20, 4 << 20)
    reporter.update(4 << 20, 4 << 20)
    out = stream.getvalue()
    if "\r" not in out:
        raise AssertionError("TTY 模式应使用 \\r 原地刷新: %r" % out)
    if "压缩中" not in out or "25%" not in out:
        raise AssertionError("缺少阶段标签或百分比: %r" % out)
    if "100%" not in out:
        raise AssertionError("缺少 100%% 收尾渲染: %r" % out)
    if "/s" not in out:
        raise AssertionError("缺少速度显示: %r" % out)
    reporter.set_phase("隐写中")  # 阶段切换应收束当前行（写一个换行）
    if "\n" not in stream.getvalue()[len(out):] and not out.endswith("\n"):
        # set_phase 之后应至少出现一个换行（行已收束）
        raise AssertionError("阶段切换未收束进度行")
    print("  ok   tty single-line rendering")


def test_non_tty_percent_lines(module):
    stream = io.StringIO()  # StringIO.isatty() 返回 False
    reporter = module.CliProgressReporter(stream=stream)
    reporter.set_phase("压缩中")
    for done in range(1, 11):
        reporter.update(done, 10)
    out = stream.getvalue()
    if "\r" in out:
        raise AssertionError("非 TTY 模式不应写 \\r: %r" % out)
    if out.count("\n") != 10:
        raise AssertionError("非 TTY 应每 10%% 打一行（共 10 行）: %r" % out)
    if "50%" not in out or "100%" not in out:
        raise AssertionError("缺少百分比行: %r" % out)
    print("  ok   non-tty 10%% lines")


def make_fixture(root):
    payload = os.path.join(root, "payload")
    os.makedirs(payload)
    for name, size in (("a.bin", 1 << 20), ("b.bin", 2 << 20)):
        with open(os.path.join(payload, name), "wb") as handle:
            handle.write(os.urandom(size))
    cover = os.path.join(root, "cover.mp4")
    with open(cover, "wb") as handle:
        handle.write(os.urandom(64 * 1024))
    return payload, cover


def test_cli_echo_and_progress_via_subprocess(module, work_root):
    payload, cover = make_fixture(work_root)
    result = subprocess.run([sys.executable, MODULE_PATH, "-i", payload, "--no-log", "-c", cover],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", cwd=work_root)
    if result.returncode != 0:
        raise AssertionError("CLI failed:\n%s" % (result.stdout + result.stderr))
    out = result.stdout
    if "压缩中" not in out:
        raise AssertionError("缺少阶段标签回显: %r" % out)
    if "要压缩的文件总大小" not in out:
        raise AssertionError("log 回显缺失: %r" % out)
    if not re.search(r"100%", out):
        raise AssertionError("缺少 100% 收尾: %r" % out)
    if "\r" in out:
        raise AssertionError("管道输出不应含 \\r: %r" % out)
    print("  ok   cli echo + progress via subprocess")


def main():
    module = load_module()
    work_root = tempfile.mkdtemp(prefix="steg-cli-progress-test-")
    try:
        test_tty_single_line_rendering(module)
        test_non_tty_percent_lines(module)
        test_cli_echo_and_progress_via_subprocess(module, work_root)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)
    print("CLI-progress tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
