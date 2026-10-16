# 分卷隐写（自动分卷）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 SteganographierGUI 一次操作完成"按上限分卷 → 逐卷隐写 → 清理中间产物"，提供「独立压缩包」（模式 A，默认）与「真分卷 .zip.001」（模式 C）两种可选方式，同时适配 CLI 与 GUI。

**Architecture:** 在 `Steganographier.py`（单文件架构）内新增：纯函数 `plan_volumes()` 做卷规划；`compress_entry_list()` 支持显式条目清单（含跨卷切块片段流式写入）；`hide_file()` 的嵌入段抽成 `_embed_zip_into_video()` 供单卷/分卷共用；`hide_volumized()` 编排逐卷"压缩→隐写→删除临时文件"流水线（模式 C 用捆绑 `tools/7z.exe` 生成真分卷）。未启用分卷的路径行为逐字节不变。

**Tech Stack:** Python 3.8 兼容（CI 用 3.8；本机开发环境用 3.12 venv）、pyzipper 0.3.6（AES zip）、标准库 zipfile、捆绑 `tools/7z.exe` 23.01（模式 C）、`tools/mkvmerge.exe`（mkv 模式）。

**Spec:** `docs/superpowers/specs/2026-10-16-volume-hiding-design.md`（本计划的下游依据；执行者需先通读 spec）

## Global Constraints

- **Python 3.8 兼容**：代码不得使用 3.8 之后的语法（无 `X | Y` 类型联合、无 `match`、无 `dict |` 合并）。CI（`.github/workflows/ci.yml`）在 3.8 上跑全部测试脚本。
- **回归红线**：任何任务完成后，未启用分卷的现有流程行为不变；仓库现有测试全绿：`python scripts/test-cli-temp-archive.py`、`test-mp4-free-atom-format.py`、`test-reveal-keeps-original.py`。
- **风格（AGENTS.md）**：4 空格缩进；`snake_case`/`PascalCase`/`UPPER_SNAKE_CASE`；保留 UTF-8 中文；改动用 `os.path` 而非手拼路径。
- **依赖**：不新增第三方依赖。7z/mkvmerge 一律用 `tools/` 捆绑件（`self._7z_exe`）。
- **变更范围**：只动 `Steganographier.py`、`scripts/`（新增测试）、`.github/workflows/ci.yml`、`README.md`、`CHANGELOG.md`、`VERSION`、`docs/superpowers/specs/2026-10-16-volume-hiding-design.md`（回填实测）。不动 `context-menu/`、`installer/`、`SteganographierGUI.spec`。
- **开发环境**：`D:\SteganographierGUI` 克隆（main）+ 本地 `.venv`（Python 3.12，`C:\Python312\python.exe`）。pip 慢时加 `--proxy http://127.0.0.1:7890`。
- **执行许可**：运行测试、构建安装包前需征得用户同意（用户习惯）；GUI 界面验收由用户亲自操作。git 仅本地提交，不 push；需要网络时走 127.0.0.1:7890。
- **提交信息**：短祈使句英文（仓库历史风格），每个提交单一关注点。

## 文件结构

| 文件 | 操作 | 职责 |
|---|---|---|
| `Steganographier.py` | 修改 | 全部功能代码：常量、`parse_size_to_bytes`、`plan_volumes`、`collect_input_entries`、`compress_entry_list`、`_embed_zip_into_video`、`hide_volumized`、`_create_split_archive_with_7z`、`get_output_file_path` 扩展、CLI/GUI 接线 |
| `scripts/test-volume-plan.py` | 新建 | 纯逻辑测试（解析 + 卷规划），跟随 `test-cli-temp-archive.py` 的脚本模式 |
| `scripts/test-volume-mode.py` | 新建 | e2e：模式 A/C 夹具跑真流程 + 接收端（7z/解压路径）断言 + 回归 |
| `.github/workflows/ci.yml` | 修改 | 尾部新增两行测试调用 |
| `README.md` | 修改 | 「使用说明」补充分卷章节 |
| `CHANGELOG.md` | 修改 | 新增 `v1.3.12（本地构建）` 条目 |
| `VERSION` | 修改 | `1.3.11` → `1.3.12`（本地构建标识） |
| `docs/superpowers/specs/2026-10-16-volume-hiding-design.md` | 修改 | Task 1 回填 §12/§15 实测结果 |

---

### Task 1: 开发环境与首日验证（spike）

**Files:**
- Create: `D:\SteganographierGUI\.venv\`（本地环境，不入库）
- Modify: `docs/superpowers/specs/2026-10-16-volume-hiding-design.md`（§12、§15 回填）

**Interfaces:**
- Consumes: 无
- Produces: 后续所有任务依赖的环境与结论——`7z.exe -tzip -v` 的命名/加密参数事实、pyzipper 流式写入可用性（`compress_entry_list` 的实现方式）、WinRAR 直开 `.zip.001` 的兼容矩阵事实。

- [ ] **Step 0: 向用户确认可运行本地验证命令**（本任务会执行 venv 安装、7z.exe、WinRAR CLI；按用户习惯先获同意）

- [ ] **Step 1: 创建 venv 并装依赖**

```bash
cd "D:\SteganographierGUI"
"/c/Python312/python.exe" -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
# 若下载失败/过慢： 加 --proxy http://127.0.0.1:7890
```

- [ ] **Step 2: 基线冒烟**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe Steganographier.py --help
```
Expected: 编译通过；`--help` 正常打印（含现有参数）。

- [ ] **Step 3: Spike —— 7z 分卷命名与加密参数**

```bash
mkdir -p /tmp/stegspike/src
head -c 3000000 /dev/urandom > /tmp/stegspike/src/a.bin
./tools/7z.exe a -tzip -v1m -mx=0 -p"test123" -mem=AES256 /tmp/stegspike/arc.zip /tmp/stegspike/src
ls /tmp/stegspike/
```
Expected: 生成 `arc.zip.001`、`arc.zip.002`、`arc.zip.003`（命名规律确认）。
继续验证：

```bash
./tools/7z.exe l /tmp/stegspike/arc.zip.001            # 列出内容（应提示输入或需要 -p）
./tools/7z.exe x -o/tmp/stegspike/out -ptest123 /tmp/stegspike/arc.zip.001
cmp /tmp/stegspike/src/a.bin /tmp/stegspike/out/src/a.bin && echo OK
```
记录：`-v{b|k|m|g}` 语法、AES 是否生效、`.001` 命名。若 `-mem=AES256` 报错，改测 `-p` 单独（ZipCrypto）并记录到最后手段。

- [ ] **Step 4: Spike —— 本机 WinRAR 7.23 直开 `.zip.001`**

```bash
"/d/Program Files/WinRAR/WinRAR.exe" x -ibck -inul -o+ -ptest123 /tmp/stegspike/arc.zip.001 /tmp/stegspike/winrar_out/
echo "exit=$?"
```
Expected（设计资料称 7.11+ 支持）：exit=0 且解出内容与源一致；若失败，记录实际报错——兼容矩阵按事实回填（说明文案指引 7-Zip/Bandizip）。

- [ ] **Step 5: Spike —— pyzipper 流式写入（AES + open('w')）**

```bash
./.venv/Scripts/python.exe - <<'EOF'
import pyzipper, os, hashlib, zipfile
p = "/tmp/stegspike/stream_enc.zip"
data = os.urandom(1024 * 512)
with pyzipper.AESZipFile(p, "w", compression=pyzipper.ZIP_STORED, encryption=pyzipper.WZ_AES) as zf:
    zi = zipfile.ZipInfo("part.bin")
    zi.compress_type = pyzipper.ZIP_STORED
    with zf.open(zi, "w", pwd=b"test123") as w:
        for i in range(0, len(data), 65536):
            w.write(data[i:i+65536])
print("hashes", hashlib.sha256(data).hexdigest())
EOF
./tools/7z.exe t -ptest123 /tmp/stegspike/stream_enc.zip && echo STREAM_OK
```
Expected: `7z t` 通过（说明 pyzipper `open(ZipInfo, 'w', pwd=...)` 可流式写 AES 条目）。若失败：记录报错，改用**片段临时文件回退方案**（`compress_entry_list` 先把片段写为临时文件再 `zf.write`，见 Task 4 备注），并把回退写进本 spike 记录。
说明：pyzipper 的 `open(self, name, mode="r", pwd=None, *, force_zip64=False)` 已确认存在于其 vendored zipfile（pyzipper/zipfile.py 第 1968 行），本步只是实测 AES 组合行为。

- [ ] **Step 6: Spike —— 7z 进度输出**

```bash
./tools/7z.exe a -tzip -v1m -bsp1 -mx=5 /tmp/stegspike/prog.zip /tmp/stegspike/src 2>&1 | head -5
```
记录 stdout 中百分比行的格式（供 `_create_split_archive_with_7z` 解析）。

- [ ] **Step 7: 回填设计文档并提交**

把 Step 3–6 结论写入 spec 的 §15（改为"已实测"）与 §12 的 WinRAR 行；若参数组合与设计假设不同（如 AES 需不同写法），同步修正 §5 的生成命令描述。

```bash
git add docs/superpowers/specs/2026-10-16-volume-hiding-design.md
git commit -m "Record day-one verification results for the volume-splitting design"
```

---

### Task 2: parse_size_to_bytes + 纯逻辑测试脚本骨架

**Files:**
- Modify: `Steganographier.py`（顶部 import 区加 `import re`；模块级函数区加解析函数）
- Test: `scripts/test-volume-plan.py`（新建）

**Interfaces:**
- Consumes: 无
- Produces: `parse_size_to_bytes(value) -> int`（`'4G'/'4096M'/'512'`→字节；非法抛 `ValueError`）。Task 6/7 的 CLI/GUI 使用。

- [ ] **Step 1: 写失败测试**

新建 `scripts/test-volume-plan.py`（完整骨架，后续 Task 3 在同文件追加用例）：

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
cd "D:\SteganographierGUI"
./.venv/Scripts/python.exe scripts/test-volume-plan.py
```
Expected: FAIL（`module.parse_size_to_bytes` 不存在，AttributeError）。

- [ ] **Step 3: 最小实现**

在 `Steganographier.py` 顶部 import 区补 `import re`（当前无此导入）。
在模块级函数区（`format_size()` 附近）加入：

```python
def parse_size_to_bytes(value):
    """把 '4G' / '4096M' / '512'（纯数字按 MB）解析为字节数；非法值抛 ValueError。"""
    text = str(value).strip()
    match = re.match(r"^(\d+)\s*([GgMm]?)$", text)
    if not match:
        raise ValueError("无法解析大小: %r（示例: 4G / 4096M / 512）" % value)
    number = int(match.group(1))
    if number <= 0:
        raise ValueError("大小必须大于 0: %r" % value)
    unit = match.group(2).lower()
    if unit == "g":
        return number * 1024 ** 3
    return number * 1024 ** 2
```

- [ ] **Step 4: 运行确认通过**

```bash
./.venv/Scripts/python.exe scripts/test-volume-plan.py
```
Expected: `Volume-plan tests passed.`（exit 0）

- [ ] **Step 5: 提交**

```bash
git add Steganographier.py scripts/test-volume-plan.py
git commit -m "Add size parser and pure-logic test skeleton for volume splitting"
```

---

### Task 3: plan_volumes 卷规划

**Files:**
- Modify: `Steganographier.py`（模块级：分卷常量 + `plan_volumes()`）
- Test: `scripts/test-volume-plan.py`（追加用例）

**Interfaces:**
- Consumes: 无（纯函数）
- Produces: `plan_volumes(entries, volume_budgets, chunk_min_bytes=MIN_VOLUME_CAP_BYTES, budget_offset=0, entry_overhead=None) -> {"volumes": [...], "chunked": {...}}`；`VOLUME_SIZE_MARGIN_BYTES`、`MIN_VOLUME_CAP_BYTES` 常量。Task 4/6/7 使用。

- [ ] **Step 1: 写失败测试（追加用例）**

在 `scripts/test-volume-plan.py` 追加：

```python
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
```

在 `main()` 中追加调用（替换 Task 2 的 main）：

```python
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
```

- [ ] **Step 2: 运行确认失败**

```bash
./.venv/Scripts/python.exe scripts/test-volume-plan.py
```
Expected: FAIL（`plan_volumes` 不存在）。

- [ ] **Step 3: 实现常量与 plan_volumes**

在 `build_temp_archive_path()` 之前加入常量块与函数：

```python
# ==== 自动分卷（volume splitting）====
VOLUME_SIZE_MARGIN_BYTES = 1 * 1024 * 1024  # 每卷固定余量：free 原子头/随机垫/zip 注释/中央目录估算误差
MIN_VOLUME_CAP_BYTES = 16 * 1024 * 1024     # 每卷 zip 预算下限；也是切块件允许占用的最小空间单位


def plan_volumes(entries, volume_budgets, chunk_min_bytes=MIN_VOLUME_CAP_BYTES,
                 budget_offset=0, entry_overhead=None):
    """把条目清单装进卷计划（纯函数，无 IO）。

    entries: [(path, arcname, size), ...]，调用方按期望顺序传入（通常已打乱）。
    volume_budgets: 各卷 zip 预算；按 (budget_offset + 卷序号) % len 周期取用。
    entry_overhead: 单条目打包开销估算（默认按 arcname 长度估算；测试可注入 0）。
    返回 {"volumes": [{"pieces": [...], "estimated_zip_size": int}, ...],
          "chunked": {原始 arcname: [部件 arcname, ...]}}
    """
    if entry_overhead is None:
        def entry_overhead(arcname):
            return 256 + 2 * len(arcname.encode("utf-8"))

    def budget_for(index):
        return volume_budgets[(budget_offset + index) % len(volume_budgets)]

    volumes = []
    remaining = []   # 与 volumes 对齐的剩余预算
    chunked = {}

    def append_piece(piece, volume_index, cost):
        while volume_index >= len(volumes):
            volumes.append({"pieces": [], "estimated_zip_size": 0})
            remaining.append(budget_for(len(volumes) - 1))
        volumes[volume_index]["pieces"].append(piece)
        volumes[volume_index]["estimated_zip_size"] += cost
        remaining[volume_index] -= cost

    for path, arcname, size in entries:
        need = size + entry_overhead(arcname)
        if not volumes:
            volumes.append({"pieces": [], "estimated_zip_size": 0})
            remaining.append(budget_for(0))
        last = len(volumes) - 1

        if need <= remaining[last]:
            append_piece({"kind": "whole", "path": path, "arcname": arcname, "size": size}, last, need)
            continue

        # 当前卷装不下：仅当当前卷非空时允许"滚动整装"（否则会留下空卷）
        if volumes[last]["pieces"] and need <= budget_for(len(volumes)):
            append_piece({"kind": "whole", "path": path, "arcname": arcname, "size": size},
                         len(volumes), need)
            continue

        # 单文件自身超限：按 .001 惯例切块跨卷；起始卷剩余不足下限则从新卷开始
        start_index = last if remaining[last] >= chunk_min_bytes else len(volumes)
        pieces = []
        offset = 0
        left = size
        volume_index = start_index
        while left > 0:
            if volume_index >= len(volumes):
                avail = budget_for(volume_index)
            else:
                avail = remaining[volume_index]
            take = min(avail, left)
            pieces.append((volume_index, offset, take))
            offset += take
            left -= take
            volume_index += 1
        digits = max(3, len(str(len(pieces))))
        part_names = []
        for part_number, (vol_index, part_offset, part_len) in enumerate(pieces, 1):
            part_name = "%s.%0*d" % (arcname, digits, part_number)
            append_piece({"kind": "chunk", "path": path, "arcname": part_name,
                          "offset": part_offset, "length": part_len},
                         vol_index, part_len + entry_overhead(part_name))
            part_names.append(part_name)
        chunked[arcname] = part_names

    return {"volumes": volumes, "chunked": chunked}
```

- [ ] **Step 4: 运行确认全部通过**

```bash
./.venv/Scripts/python.exe scripts/test-volume-plan.py
```
Expected: `Volume-plan tests passed.`（全部 ok 行）

- [ ] **Step 5: 提交**

```bash
git add Steganographier.py scripts/test-volume-plan.py
git commit -m "Add volume planner with whole-file packing and .001 chunking"
```

---

### Task 4: 压缩层——collect_input_entries / compress_entry_list

**Files:**
- Modify: `Steganographier.py`（`compress_files()` 第 1891 行附近；在 `Steganographier` 类内新增）
- Test: `scripts/test-cli-temp-archive.py`（**不修改**，作为回归网）、`scripts/test-volume-mode.py`（Task 6 中创建，本任务后用后置检查）

**Interfaces:**
- Consumes: `plan_volumes()` 的 piece 结构（Task 3）。
- Produces:
  - `collect_input_entries(input_file_path, exclude_path, log=None) -> [(full_path, arcname, size), ...]`（模块级）
  - `Steganographier.compress_entry_list(zip_file_path, pieces, password=None, comment=None, extra_entries=None, progress_callback=None)`——`pieces` 为 piece 列表；`extra_entries` 为 `[(arcname, bytes), ...]`（如说明文件）；`progress_callback(processed, total)`。Task 6/7 使用。

- [ ] **Step 1: 回归基线（重构前）**

```bash
./.venv/Scripts/python.exe scripts/test-cli-temp-archive.py
./.venv/Scripts/python.exe scripts/test-mp4-free-atom-format.py
./.venv/Scripts/python.exe scripts/test-reveal-keeps-original.py
```
Expected: 三个脚本全部通过（这是重构后要复现的基线）。

- [ ] **Step 2: 抽出 collect_input_entries**

把 `compress_files()` 内 `collect_zip_entries()` 闭包（含"排除自身/跳过记录日志"逻辑）挪到模块级：

```python
def collect_input_entries(input_file_path, exclude_path, log=None):
    """收集 (full_path, arcname, size) 列表；exclude_path（正在写入的临时包）必须被排除。

    排除自身是 v1.3.10 事故的教训：临时包若落在输入目录内部，os.walk 会把它列出，
    随后一边读一边追加导致无限膨胀（见 compress_files 顶部注释）。
    """
    input_file_path = os.path.normpath(input_file_path)
    archive_path = os.path.normcase(os.path.abspath(exclude_path)) if exclude_path else None
    entries = []
    if os.path.isdir(input_file_path):
        root_folder = os.path.basename(input_file_path)
        for root, dirs, files in os.walk(input_file_path):
            for file in files:
                full_path = os.path.join(root, file)
                if archive_path and os.path.normcase(os.path.abspath(full_path)) == archive_path:
                    if log:
                        log("跳过临时压缩包自身: %s" % full_path)
                    continue
                arcname = os.path.join(root_folder, os.path.relpath(full_path, start=input_file_path))
                entries.append((full_path, arcname, os.path.getsize(full_path)))
    else:
        entries.append((input_file_path, os.path.basename(input_file_path), os.path.getsize(input_file_path)))
    return entries
```

`compress_files()` 内改为调用它（保持其余逻辑逐行不变）：

```python
        file_list = collect_input_entries(input_file_path, zip_file_path, log=self.log)
        # 原 file_list 元素为 (full_path, arcname)，此处拆出 size 保持后续写法不变
        file_list = [(full, arc) for full, arc, _ in file_list]
```
（`random.shuffle(file_list)` 与两个写入循环保持原样；注意原循环内 `os.path.getsize(file_full_path)` 处可继续保留——行为不变。）

- [ ] **Step 3: 实现 compress_entry_list**

在 `compress_files()` 之后新增（`Steganographier` 类内）：

```python
    def compress_entry_list(self, zip_file_path, pieces, password=None, comment=None,
                            extra_entries=None, progress_callback=None):
        """把卷计划的 pieces 写入 zip（支持跨卷切块片段的流式写入）。

        - whole 片段沿用现有随机化习惯（随机压缩等级/随机时间戳）；
        - chunk 片段一律 ZIP_STORED（大体积快速写入），随机时间戳保留；
        - extra_entries: [(arcname, payload_bytes)]，如《合并说明.txt》。
        """
        total_size = sum(p["size"] if p["kind"] == "whole" else p["length"] for p in pieces)
        total_size += (sum(len(payload) for _, payload in extra_entries)) if extra_entries else 0
        processed_size = 0

        def report():
            if progress_callback:
                progress_callback(processed_size, total_size)

        if password:
            zip_file = pyzipper.AESZipFile(zip_file_path, 'w',
                                           compression=pyzipper.ZIP_DEFLATED,
                                           encryption=pyzipper.WZ_AES)
            zip_file.setpassword(password.encode('utf-8'))
        else:
            zip_file = zipfile.ZipFile(zip_file_path, 'w')

        with zip_file:
            for piece in pieces:
                if piece["kind"] == "whole":
                    if password:
                        zip_file.write(piece["path"], arcname=piece["arcname"],
                                       compress_type=pyzipper.ZIP_STORED)
                    else:
                        zip_file.write(piece["path"], arcname=piece["arcname"],
                                       compress_type=zipfile.ZIP_DEFLATED,
                                       compresslevel=random.randint(1, 9))
                    processed_size += piece["size"]
                    report()
                else:
                    zi = zipfile.ZipInfo(filename=piece["arcname"], date_time=_random_zip_date_time())
                    zi.compress_type = zipfile.ZIP_STORED
                    writer = (zip_file.open(zi, "w", pwd=password.encode("utf-8"))
                              if password else zip_file.open(zi, "w"))
                    with writer:
                        with open(piece["path"], "rb") as source:
                            source.seek(piece["offset"])
                            remaining = piece["length"]
                            while remaining > 0:
                                chunk = source.read(min(4 * 1024 * 1024, remaining))
                                if not chunk:
                                    break
                                writer.write(chunk)
                                remaining -= len(chunk)
                                processed_size += len(chunk)
                                report()
            for arcname, payload in (extra_entries or []):
                zi = zipfile.ZipInfo(filename=arcname, date_time=_random_zip_date_time())
                zi.compress_type = zipfile.ZIP_DEFLATED
                if password:
                    with zip_file.open(zi, "w", pwd=password.encode("utf-8")) as writer:
                        writer.write(payload)
                else:
                    zip_file.writestr(zi, payload)
                processed_size += len(payload)
                report()
            if comment:
                zip_file.comment = comment.encode("utf-8")
```

同时在模块级新增（供 `compress_files()` 的随机时间戳循环复用，Reduce 重复）：

```python
def _random_zip_date_time():
    """生成随机且合法的 zip 时间戳（沿用现有随机化习惯）。"""
    while True:
        try:
            date_time = (random.randint(1980, 2099), random.randint(1, 12), random.randint(1, 28),
                         random.randint(0, 23), random.randint(0, 59), random.randint(0, 59))
            datetime.datetime(*date_time)
            return date_time
        except ValueError:
            continue
```

备注（spike 回退）：若 Task 1 Step 5 判定 pyzipper 流式写不可用，则 chunk 分支改为"先按 4MB 块把片段写到 `tempfile` 临时文件，再 `zip_file.write(tmp, arcname)`，随后删除临时文件"；此回退只影响本函数。

- [ ] **Step 4: 回归验证**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe scripts/test-cli-temp-archive.py
./.venv/Scripts/python.exe scripts/test-mp4-free-atom-format.py
./.venv/Scripts/python.exe scripts/test-reveal-keeps-original.py
```
Expected: 全部通过（与 Step 1 基线一致）。

- [ ] **Step 5: 提交**

```bash
git add Steganographier.py
git commit -m "Extract entry collection and add volume-aware zip writer"
```

---

### Task 5: 嵌入层——_embed_zip_into_video

**Files:**
- Modify: `Steganographier.py`（`hide_file()`，第 2058 行起）

**Interfaces:**
- Consumes: 现有 `hide_file()` 内 4.1/4.2/4.3 三段嵌入逻辑。
- Produces: `Steganographier._embed_zip_into_video(cover_video_path, zip_file_path, output_file, progress_callback=None) -> None`；`progress_callback` 为 `callable(fraction: float)`（None 时沿用 `self.progress_callback(processed, total)`）。Task 6/7 使用。调用前置条件：`self.type_option_var` 已设置（`hide_file` 与 `hide_volumized` 都会先设置）。

- [ ] **Step 1: 抽取方法**

把 `hide_file()` 中 `try:` 块内 "4.1 MP4 / 4.2 MKV / 4.3 zarchiver" 三段（含进度回调与日志）原样移入新方法；`hide_file()` 保留：cover 选择、`build_temp_archive_path`、`compress_files`、`get_output_file_path`、调用新方法、`finally` 删除临时 zip、末尾 `Output file created` 日志。

新方法骨架（进度统一走 helper）：

```python
    def _report_progress(self, progress_callback, processed, total):
        if progress_callback is not None:
            progress_callback(processed / total if total else 1.0)
        elif self.progress_callback:
            self.progress_callback(processed, total)

    def _embed_zip_into_video(self, cover_video_path, zip_file_path, output_file,
                              progress_callback=None):
        """把 cover + free 原子 + zip 写为输出视频（mp4/mkv/zarchiver 三分支）。

        与 hide_file() 的历史实现逐行等价，只是把进度回调经由 _report_progress 转发，
        便于分卷编排器按卷缩放进度。
        """
        if self.type_option_var == 'mp4':
            ...  # 原 4.1 段代码，把 self.progress_callback(...) 替换为 self._report_progress(progress_callback, ...)
        elif self.type_option_var == 'mkv':
            ...  # 原 4.2 段
        elif self.type_option_var == 'mp4(zarchiver)':
            ...  # 原 4.3 段
```

`hide_file()` 内在计算 `output_file` 后改为：

```python
                self.log(f"输出文件: {output_file}")
                self._embed_zip_into_video(cover_video_path, zip_file_path, output_file)
```

- [ ] **Step 2: 回归验证（含一次真实 CLI 冒烟）**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe scripts/test-mp4-free-atom-format.py
./.venv/Scripts/python.exe scripts/test-reveal-keeps-original.py
# 真实 CLI 冒烟（临时目录夹具，获用户同意后执行）：
mkdir -p /tmp/embed_smoke/re
head -c 1048576 /dev/urandom > /tmp/embed_smoke/a.bin
cp /tmp/embed_smoke/a.bin /tmp/embed_smoke/a.bin.orig
./.venv/Scripts/python.exe Steganographier.py -i /tmp/embed_smoke/a.bin --no-log
ls /tmp/embed_smoke/                     # 期望：a_hidden_1.mp4
mv /tmp/embed_smoke/a_hidden_1.mp4 /tmp/embed_smoke/re/
./.venv/Scripts/python.exe Steganographier.py -i /tmp/embed_smoke/re/a_hidden_1.mp4 -r --no-log
cmp /tmp/embed_smoke/a.bin.orig /tmp/embed_smoke/re/a.bin && echo ROUNDTRIP_OK
```
Expected: 现有测试全绿；冒烟解出的 `re/a.bin` 与原文件逐字节一致（`ROUNDTRIP_OK`）。

- [ ] **Step 3: 提交**

```bash
git add Steganographier.py
git commit -m "Extract video embedding into a shared method for volume reuse"
```

---

### Task 6: 模式 A 编排 + CLI 接线 + e2e 测试

**Files:**
- Modify: `Steganographier.py`（`get_output_file_path()`、新增 `hide_volumized()`、`run_cli()`、`__main__` argparse）
- Test: `scripts/test-volume-mode.py`（新建）
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: Task 2/3/4/5 的产物。
- Produces: `Steganographier.hide_volumized(input_file_path, volume_cap_bytes, password=None, processed_files=0, output_option=None, output_cover_video_name_mode=None, type_option_var=None, video_folder_path=None, cover_video_CLI=None, output_dir=None, volume_mode="zip") -> {"volumes": int, "outputs": [paths], "chunked": {...}, "mode": str}`；`build_merge_note(chunked) -> str`；CLI `-vs/--volume-size`、`--volume-mode`。

- [ ] **Step 1: 扩展 get_output_file_path 命名**

签名追加三个参数（默认 None，既有调用零变化）：

```python
    def get_output_file_path(self, input_file_path=None, output_file_path=None, processed_files=0,
                             output_option=None, output_cover_video_name_mode=None, cover_video_path=None,
                             volume_index=None, volume_total=None, output_directory=None):
```

三个类型分支内把 `{processed_files+1}` 统一替换为 `number_text`：

```python
        number_text = ("%dof%d" % (volume_index, volume_total)) if volume_index else str(processed_files + 1)
```

对应替换点（逐处等值替换）：
- `f"_hidden_{processed_files+1}.mp4"` → `f"_hidden_{number_text}.mp4"`（文件夹与文件两个变体）
- `f"_hidden_z{processed_files+1}.mp4"` → `f"_hidden_z{number_text}.mp4"`
- `f"_hidden_{processed_files+1}.mkv"` → `f"_hidden_{number_text}.mkv"`
- `replace('.mp4', f'_{processed_files+1}.mp4')` → `replace('.mp4', f'_{number_text}.mp4')`
- `f'_z{processed_files+1}.mp4'` → `f'_z{number_text}.mp4'`
- 随机名模式同理替换后缀数字段。

在重名处理前追加：

```python
        if output_directory and output_file_path:
            output_file_path = os.path.join(output_directory, os.path.basename(output_file_path))
```

- [ ] **Step 2: 实现 hide_volumized（模式 A）与 build_merge_note**

模块级（`plan_volumes()` 旁）：

```python
def build_merge_note(chunked):
    """为切块文件生成《合并说明.txt》内容（UTF-8 BOM 由写入方负责）。"""
    lines = ["【大文件合并说明】",
             "以下文件因为超过单卷上限被切成了多个片段，解压全部视频后请按顺序合并：", ""]
    for original, parts in chunked.items():
        commands = "+".join('"%s"' % part for part in parts)
        lines.append('copy /b %s "%s"' % (commands, original))
    lines += ["", "也可以用 7-Zip：选中第一个 .00N 片段 → 菜单「文件」→「合并文件」。"]
    return "\n".join(lines) + "\n"
```

`Steganographier` 类内：

```python
    def hide_volumized(self, input_file_path, volume_cap_bytes, password=None, processed_files=0,
                       output_option=None, output_cover_video_name_mode=None, type_option_var=None,
                       video_folder_path=None, cover_video_CLI=None, output_dir=None, volume_mode="zip"):
        input_file_path = os.path.normpath(input_file_path)
        self.type_option_var = type_option_var
        self.output_option = output_option
        self.output_cover_video_name_mode = output_cover_video_name_mode
        self.password = password

        if type_option_var == 'mp4(zarchiver)':
            raise ValueError("mp4(zarchiver) 模式不支持自动分卷（大卷会把整包读入内存）")
        if type_option_var == 'mkv' and volume_cap_bytes > 2 * 1024 ** 3:
            self.log("mkv 模式每卷上限自动收敛到 2GB（原设置 %s）" % format_size(volume_cap_bytes))
            volume_cap_bytes = 2 * 1024 ** 3

        cover_candidates = self._volume_cover_candidates(cover_video_CLI, video_folder_path)
        budgets = []
        for cover in cover_candidates:
            budget = volume_cap_bytes - os.path.getsize(cover) - VOLUME_SIZE_MARGIN_BYTES
            if budget < MIN_VOLUME_CAP_BYTES:
                raise ValueError("上限太小：扣除外壳「%s」与 1MB 余量后仅剩 %s，请调大上限"
                                 % (os.path.basename(cover), format_size(max(budget, 0))))
            budgets.append(budget)

        entries = collect_input_entries(input_file_path, None, log=self.log)
        if not entries:
            raise ValueError("没有可隐写的文件")
        random.shuffle(entries)

        if volume_mode == "split":
            return self._hide_volumized_split(input_file_path, volume_cap_bytes, cover_candidates,
                                              budgets, processed_files, output_option,
                                              output_cover_video_name_mode, output_dir, password)

        plan = plan_volumes(entries, budgets, budget_offset=processed_files % len(budgets))
        volumes = plan["volumes"]
        total = len(volumes)
        if total > 1 and len(cover_candidates) == 1:
            self.log("提示：候选外壳只有 1 个，%d 个卷将重复使用同一外壳" % total)

        if total == 1:
            # 未发生分卷：走现有单卷路径（不加 ofN 后缀）
            output_override = None
            if output_dir:
                output_override = self.get_output_file_path(input_file_path, None, processed_files,
                                                            output_option, output_cover_video_name_mode,
                                                            cover_candidates[0],
                                                            output_directory=output_dir)
            self.hide_file(input_file_path=input_file_path, cover_video_CLI=cover_video_CLI,
                           password=password, processed_files=processed_files,
                           output_file_path=output_override, output_option=output_option,
                           output_cover_video_name_mode=output_cover_video_name_mode,
                           type_option_var=type_option_var, video_folder_path=video_folder_path)
            return {"volumes": 1, "outputs": [output_override] if output_override else [],
                    "chunked": {}, "mode": "zip"}

        note_by_volume = {}
        if plan["chunked"]:
            note_text = build_merge_note(plan["chunked"])
            for first_part in (parts[0] for parts in plan["chunked"].values()):
                for index, volume in enumerate(volumes):
                    if any(p["kind"] == "chunk" and p["arcname"] == first_part for p in volume["pieces"]):
                        note_by_volume[index] = note_text
                        break

        outputs = []
        for index, volume in enumerate(volumes):
            k = index + 1
            cover = cover_candidates[(processed_files + index) % len(cover_candidates)]
            output_file = self.get_output_file_path(
                input_file_path, None, processed_files, output_option,
                output_cover_video_name_mode, cover,
                volume_index=k, volume_total=total, output_directory=output_dir)
            temp_zip = build_temp_archive_path(input_file_path, processed_files + index)
            extra_entries = []
            if index in note_by_volume:
                extra_entries.append(("合并说明.txt", note_by_volume[index].encode("utf-8-sig")))
            volume_comment = (f"Volume {k}/{total} of '{os.path.basename(input_file_path)}'\n"
                              f"Timestamp '{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}'")
            self.log("第 %d/%d 卷：压缩中…" % (k, total))
            try:
                self.compress_entry_list(
                    temp_zip, volume["pieces"], password=password, comment=volume_comment,
                    extra_entries=extra_entries,
                    progress_callback=(lambda p, t, k=k: self.progress_callback(
                        k - 1 + 0.5 * (p / t if t else 1.0), total)) if self.progress_callback else None)
                self.log("第 %d/%d 卷：隐写中…" % (k, total))
                self._embed_zip_into_video(
                    cover, temp_zip, output_file,
                    progress_callback=(lambda frac, k=k: self.progress_callback(
                        k - 1 + 0.5 + 0.5 * frac, total)) if self.progress_callback else None)
                outputs.append(output_file)
                self.log("第 %d/%d 卷：完成 -> %s" % (k, total, output_file))
            finally:
                try:
                    os.remove(temp_zip)
                except OSError as remove_error:
                    self.log("删除临时zip文件失败: %s" % remove_error)

        return {"volumes": total, "outputs": outputs, "chunked": plan["chunked"], "mode": "zip"}

    def _volume_cover_candidates(self, cover_video_CLI, video_folder_path):
        """分卷用的外壳候选序列：-c 指定则固定单件；否则按名称顺序取目录内全部 mp4。"""
        if cover_video_CLI:
            return [cover_video_CLI]
        if not video_folder_path or not os.path.isdir(video_folder_path):
            raise ValueError("找不到外壳视频目录: %s" % video_folder_path)
        candidates = [os.path.join(video_folder_path, item)
                      for item in natsorted([f for f in os.listdir(video_folder_path) if f.endswith(".mp4")],
                                            alg=ns.PATH)]
        if not candidates:
            raise ValueError("%s 文件夹下没有可用的 MP4 外壳" % video_folder_path)
        return candidates

    def _hide_volumized_split(self, input_file_path, volume_cap_bytes, cover_candidates,
                              budgets, processed_files, output_option,
                              output_cover_video_name_mode, output_dir, password):
        """真分卷模式的占位实现；方法体在 Task 7 替换为真实现在。"""
        raise NotImplementedError("真分卷模式将在 Task 7 实现")
```

（`_hide_volumized_split` 的占位实现已包含在上方代码中，保证本任务完成后模块可导入、e2e 测试可跑；真实现在 Task 7 替换方法体。）

- [ ] **Step 3: CLI 接线**

`__main__` argparse 新增（在 `-v/--version` 之前）：

```python
    parser.add_argument('-vs', '--volume-size', default=None,
                        help='启用自动分卷：每个输出视频的上限（如 4G / 4096M / 512=MB）')
    parser.add_argument('--volume-mode', choices=['zip', 'split'], default='zip',
                        help='分卷方式: zip=每卷独立压缩包(默认), split=真分卷(.zip.001)')
```

`parse_known_args()` 之后追加校验：

```python
    if args.volume_size is not None and args.reveal:
        parser.error("--volume-size 仅用于隐写，不能与 -r 同时使用")
    if args.volume_mode != 'zip' and args.volume_size is None:
        parser.error("--volume-mode 需与 --volume-size 一起使用")
```

`run_cli()` 内、`if not args.reveal:` 的 mkv 2GB 检查**之前**插入分卷分支：

```python
            if args.volume_size is not None:
                cap_bytes = parse_size_to_bytes(args.volume_size)
                output_dir = None
                if args.output:
                    looks_like_file = os.path.splitext(args.output)[1] != '' and not os.path.isdir(args.output)
                    if looks_like_file:
                        print("分卷模式下 -o 需要是输出目录（例如 D:\\输出文件夹）")
                        sys.exit(1)
                    output_dir = args.output
                    os.makedirs(output_dir, exist_ok=True)
                cover_candidates_dir = os.path.join(application_path, "cover_video")
                summary = self.hide_volumized(
                    input_file_path=args.input, volume_cap_bytes=cap_bytes, password=args.password,
                    processed_files=0, output_option='原文件名',
                    output_cover_video_name_mode='===============名称顺序模式===============',
                    type_option_var=args.type,
                    video_folder_path=cover_candidates_dir,
                    cover_video_CLI=args.cover, output_dir=output_dir, volume_mode=args.volume_mode)
                print("分卷隐写完成：共 %d 个视频" % summary["volumes"])
                for path in summary["outputs"]:
                    print("  - %s" % path)
                if summary["chunked"]:
                    print("含切块文件（解压后需按《合并说明.txt》合并）：")
                    for original in summary["chunked"]:
                        print("  - %s" % original)
                return
```

注意：CLI 无 `-c` 时的沿用现有"找不到就报错"哲学；`cover_candidates_dir` 不存在时 `_volume_cover_candidates` 抛错（提示清晰）。

- [ ] **Step 4: 写 e2e 测试 `scripts/test-volume-mode.py`**

跟随 `test-cli-temp-archive.py` 模式（importlib 装载模块、函数断言、`main()` 返回 0）。核心内容：

```python
"""End-to-end tests for automatic volume splitting (modes zip / split).

Fixtures are small (cap 32 MB, ~40 MB payload) so a full run takes seconds.
Requires the bundled tools/7z.exe. Runs on Python 3.8+ (CI).
"""

import importlib.util
import os
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
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def extract_video(video_path, dest_dir, password=None):
    """接收端路径：把隐写视频改后缀为 .zip 后交给 7z 解压。"""
    os.makedirs(dest_dir, exist_ok=True)
    renamed = os.path.join(dest_dir, "_in.zip")
    shutil.copy(video_path, renamed)
    cmd = [SEVEN_ZIP, "x", "-y", "-o" + dest_dir, renamed]
    if password:
        cmd.append("-p" + password)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AssertionError("7z failed to extract %s:\n%s" % (video_path, result.stdout + result.stderr))
    os.remove(renamed)
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
    if list(summary["chunked"]) != ["big.bin"]:
        raise AssertionError("expected big.bin chunked, got %r" % summary["chunked"])

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
    for name, size in (("a.bin", 1 << 20), ("b.bin", 2 << 20)):
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
                     if "_1of" in name and name.endswith(".mp4"))
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
               if name.startswith("payload_hidden_") and name.endswith(".mp4")]
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
```

（`Steganographier.__init__` 参数以实际签名为准——`video_folder_path/gui_enabled/password_file/enable_log_file/version`；若实例化有额外前置（如缺 PW.txt），先写一个空 PW.txt 到 `work_root`。Task 7 会往本文件追加 split 用例。）

- [ ] **Step 5: 运行测试**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe scripts/test-volume-plan.py
./.venv/Scripts/python.exe scripts/test-volume-mode.py
./.venv/Scripts/python.exe scripts/test-cli-temp-archive.py
./.venv/Scripts/python.exe scripts/test-mp4-free-atom-format.py
./.venv/Scripts/python.exe scripts/test-reveal-keeps-original.py
```
Expected: 全部通过。

- [ ] **Step 6: 接入 CI**

`.github/workflows/ci.yml` 末尾追加：

```yaml
          python .\scripts\test-volume-plan.py
          python .\scripts\test-volume-mode.py
```

- [ ] **Step 7: 提交**

```bash
git add Steganographier.py scripts/test-volume-mode.py .github/workflows/ci.yml
git commit -m "Add volume-split hiding orchestration (independent-zip mode) with CLI and tests"
```

---

### Task 7: 模式 C——真分卷（.zip.001）

**Files:**
- Modify: `Steganographier.py`（新增 `_create_split_archive_with_7z()`、`build_split_readme()`、`_hide_volumized_split()`；`hide_volumized` 的 split 分支接上）
- Test: `scripts/test-volume-mode.py`（追加 split 用例）

**Interfaces:**
- Consumes: Task 1 spike 结论（7z 参数）、Task 4 的 `compress_entry_list`、Task 5 的 `_embed_zip_into_video`。
- Produces: `hide_volumized(..., volume_mode="split")` 端到端可用；`build_split_readme(part_index, part_total, archive_name) -> str`。

- [ ] **Step 1: 实现 7z 分卷生成与说明文案**

模块级：

```python
def build_split_readme(part_index, part_total, archive_name):
    """模式 C 的《解压说明.txt》（接收端操作指引，逐卷各放一份）。"""
    return (
        "【分卷解压说明】\n"
        "本视频内藏有分卷压缩包「%s」的第 %d 个分卷（共 %d 个），全部内容分散在 %d 个视频里。\n"
        "1. 把每个视频文件的后缀名改为 .zip，用任意解压软件解压，得到 %s.001 ~ %s.%03d。\n"
        "2. 把全部分卷放在同一个文件夹里（解压到同一目录即可）。\n"
        "3. 用 7-Zip、Bandizip 或新版 WinRAR 打开 %s.001，直接解压全部内容。\n"
        "   如果设置了密码，此时输入。\n"
        "注意：分卷必须全部齐全才能解压；旧版 WinRAR 打不开 .001 分卷时，请改用 7-Zip 或 Bandizip。\n"
        % (archive_name, part_index, part_total, part_total,
           archive_name, archive_name, part_total, archive_name)
    )
```

类内：

```python
    def _create_split_archive_with_7z(self, input_file_path, part_size_bytes, password=None):
        """用捆绑 7z.exe 生成真分卷 zip；返回 (分卷路径列表, 临时目录)。

        参数组合以 Task 1 spike 实测为准：-tzip -v{size}b；有密码时 -p + -mem=AES256，
        否则 -mx=5。进度经 -bsp1 的百分比行回调。
        """
        base = os.path.basename(os.path.normpath(input_file_path))
        parent = os.path.dirname(os.path.abspath(os.path.normpath(input_file_path)))
        temp_dir = os.path.join(parent, "%s_hidden_split_%s" % (base, generate_random_filename(8)))
        os.makedirs(temp_dir)
        archive_path = os.path.join(temp_dir, "%s_hidden.zip" % base)
        cmd = [self._7z_exe, "a", "-tzip", "-v%db" % part_size_bytes, "-bsp1"]
        if password:
            cmd += ["-mx=0", "-mem=AES256", "-p%s" % password]
        else:
            cmd += ["-mx=5"]
        cmd += [archive_path, input_file_path]
        self.log("正在生成真分卷: %s" % os.path.basename(archive_path))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            match = re.search(r"(\d+)%", line)
            if match and self.progress_callback:
                self.progress_callback(int(match.group(1)), 100)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError("7z 生成分卷失败，退出码 %d" % returncode)
        prefix = os.path.basename(archive_path) + "."
        parts = [os.path.join(temp_dir, name) for name in sorted(os.listdir(temp_dir))
                 if name.startswith(prefix)]
        if not parts:
            raise RuntimeError("7z 未产出任何分卷: %s" % archive_path)
        return parts, temp_dir

    def _hide_volumized_split(self, input_file_path, volume_cap_bytes, cover_candidates,
                              budgets, processed_files, output_option,
                              output_cover_video_name_mode, output_dir, password):
        part_size = volume_cap_bytes - max(os.path.getsize(c) for c in cover_candidates) \
            - VOLUME_SIZE_MARGIN_BYTES
        if part_size < MIN_VOLUME_CAP_BYTES:
            raise ValueError("上限太小：扣除最大的外壳与 1MB 余量后仅剩 %s，请调大上限"
                             % format_size(max(part_size, 0)))
        parts, temp_dir = self._create_split_archive_with_7z(input_file_path, part_size, password)
        total = len(parts)
        archive_name = os.path.basename(parts[0])[: -len(".001")]
        outputs = []
        try:
            for index, part in enumerate(parts):
                k = index + 1
                cover = cover_candidates[(processed_files + index) % len(cover_candidates)]
                output_file = self.get_output_file_path(
                    input_file_path, None, processed_files, output_option,
                    output_cover_video_name_mode, cover,
                    volume_index=k, volume_total=total, output_directory=output_dir)
                container = build_temp_archive_path(input_file_path, processed_files + index)
                piece = {"kind": "whole", "path": part,
                         "arcname": os.path.basename(part), "size": os.path.getsize(part)}
                extra = [("解压说明.txt",
                          build_split_readme(k, total, archive_name).encode("utf-8-sig"))]
                self.log("第 %d/%d 卷：打包载具…" % (k, total))
                try:
                    self.compress_entry_list(container, [piece], password=None, extra_entries=extra)
                    self.log("第 %d/%d 卷：隐写中…" % (k, total))
                    self._embed_zip_into_video(
                        cover, container, output_file,
                        progress_callback=(lambda frac, k=k: self.progress_callback(
                            k - 1 + frac, total)) if self.progress_callback else None)
                    outputs.append(output_file)
                    self.log("第 %d/%d 卷：完成 -> %s" % (k, total, output_file))
                finally:
                    try:
                        os.remove(container)
                    except OSError as remove_error:
                        self.log("删除临时载具失败: %s" % remove_error)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        return {"volumes": total, "outputs": outputs, "chunked": {}, "mode": "split"}
```

需要 `import shutil`（若顶部未导入则添加）。把 Task 6 里 `_hide_volumized_split` 的占位方法体（`raise NotImplementedError`）整体替换为上面的实现；并在该方法 `total = len(parts)` 之后补一行复用外壳提示：

```python
        if total > 1 and len(cover_candidates) == 1:
            self.log("提示：候选外壳只有 1 个，%d 个卷将重复使用同一外壳" % total)
```

- [ ] **Step 2: e2e 追加 split 用例**

`scripts/test-volume-mode.py` 追加：

```python
def test_mode_split_via_cli(module, work_root):
    payload, covers = make_fixture(work_root, "t4")
    run_cli(["-i", payload, "--volume-size", "32M", "--volume-mode", "split",
             "-p", "pw123", "--no-log", "-c", os.path.join(covers, "c1.mp4")], cwd=work_root)
    base = os.path.dirname(payload)   # 输出落在输入的同级目录
    outputs = sorted(name for name in os.listdir(base) if "_1of" in name and name.endswith(".mp4"))
    if len(outputs) < 2:
        raise AssertionError("split mode produced %r" % outputs)
    collect = os.path.join(work_root, "split_parts")
    os.makedirs(collect, exist_ok=True)
    for index, name in enumerate(outputs, 1):
        dest = os.path.join(work_root, "split_extract_%d" % index)
        extract_video(os.path.join(base, name), dest)
        for dirpath, _dirs, files in os.walk(dest):
            for item in files:
                shutil.move(os.path.join(dirpath, item), os.path.join(collect, item))
    part_001 = sorted(n for n in os.listdir(collect) if ".zip." in n and n.endswith(".001"))
    if len(part_001) != 1:
        raise AssertionError("split parts missing: %r" % os.listdir(collect))
    out_dir = os.path.join(work_root, "split_out")
    result = subprocess.run([SEVEN_ZIP, "x", "-y", "-o" + out_dir, "-ppw123",
                             os.path.join(collect, part_001[0])],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise AssertionError("7z join/extract failed:\n" + result.stdout + result.stderr)
    for name, size in (("a.bin", 1 << 20), ("big.bin", 36 << 20)):
        extracted = os.path.join(out_dir, "payload", name)
        if sha256_of(extracted) != sha256_of(os.path.join(payload, name)):
            raise AssertionError("split content mismatch: %s" % name)
    print("  ok   mode split: %d parts, joined extraction verified" % len(outputs))
```

在 `main()` 中追加 `test_mode_split_via_cli(module, work_root)`。

- [ ] **Step 3: 运行测试**

```bash
./.venv/Scripts/python.exe scripts/test-volume-mode.py
```
Expected: `Volume-mode tests passed.`（含 split 用例）

- [ ] **Step 4: 提交**

```bash
git add Steganographier.py scripts/test-volume-mode.py
git commit -m "Add true-split (.zip.001) volume mode using bundled 7z"
```

---

### Task 8: GUI 接线

**Files:**
- Modify: `Steganographier.py`（`SteganographierGUI.__init__`、`create_widgets()`、`start()`、`load_config()`、`save_config()`）

**Interfaces:**
- Consumes: `hide_volumized()`（Task 6/7）。
- Produces: GUI「自动分卷 / 每卷上限 / 方式」控件与配置持久化；界面验收由用户手测。

- [ ] **Step 1: 状态与配置**

`__init__` 中（`self.auto_rename_hide_on_conflict` 旁）加默认：

```python
        self.volume_enabled = False        # 自动分卷勾选
        self.volume_cap_gb = 4             # 每卷上限（GB，整数输入框）
        self.volume_mode = "zip"           # zip=独立压缩包 / split=真分卷
```

`load_config()`（`auto_rename_hide_on_conflict` 之后）：

```python
                self.volume_enabled = config.get('volume_enabled', False)
                self.volume_cap_gb = max(1, int(round(config.get('volume_cap_mb', 4096) / 1024)))
                self.volume_mode = config.get('volume_mode', 'zip')
```

`save_config()`（写 config dict 处）：

```python
            'volume_enabled': self.volume_enabled_var.get(),
            'volume_cap_mb': int(self.volume_cap_entry.get().strip() or 4) * 1024,
            'volume_mode': "split" if "真分卷" in self.volume_mode_var.get() else "zip",
```

（`volume_cap_mb` 的写入做容错：输入非数字时存回默认 4GB，不影响保存流程。）

- [ ] **Step 2: 控件（`create_widgets()` 中、外壳下拉框之后追加）**

```python
        # 1.3.1 自动分卷（大文件夹按上限拆成多个隐写视频）
        volume_frame = tk.Frame(self.root)
        volume_frame.pack(pady=4)

        self.volume_enabled_var = tk.BooleanVar(value=self.volume_enabled)
        self.volume_enabled_checkbox = tk.Checkbutton(volume_frame, text="自动分卷",
                                                      variable=self.volume_enabled_var)
        self.volume_enabled_checkbox.pack(side=tk.LEFT, padx=8)

        tk.Label(volume_frame, text="每卷上限").pack(side=tk.LEFT)
        self.volume_cap_entry = tk.Entry(volume_frame, width=6)
        self.volume_cap_entry.insert(0, str(self.volume_cap_gb))
        self.volume_cap_entry.pack(side=tk.LEFT, padx=4)
        tk.Label(volume_frame, text="GB").pack(side=tk.LEFT)

        self.volume_mode_var = tk.StringVar(value="真分卷（需 .001 配套工具）"
                                            if self.volume_mode == "split"
                                            else "独立压缩包（推荐）")
        self.volume_mode_menu = ttk.Combobox(volume_frame, textvariable=self.volume_mode_var,
                                             state="readonly", width=24,
                                             values=["独立压缩包（推荐）", "真分卷（需 .001 配套工具）"])
        self.volume_mode_menu.pack(side=tk.LEFT, padx=8)
```

- [ ] **Step 3: `start()` 路由与校验**

`start()` 中、进入隐写循环之前：

```python
        volume_enabled = self.volume_enabled_var.get()
        volume_cap_bytes = 0
        if volume_enabled:
            if self.type_option_var.get() == 'mp4(zarchiver)':
                messagebox.showerror("参数错误", "mp4(zarchiver) 模式不支持自动分卷")
                self.start_button.configure(state=tk.NORMAL)
                self.clear_button.configure(state=tk.NORMAL)
                return
            try:
                cap_gb = int(self.volume_cap_entry.get().strip())
                if cap_gb <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("参数错误", "每卷上限需要是大于 0 的整数（GB）")
                self.start_button.configure(state=tk.NORMAL)
                self.clear_button.configure(state=tk.NORMAL)
                return
            volume_cap_bytes = cap_gb * 1024 ** 3
            if self.type_option_var.get() == 'mkv' and volume_cap_bytes > 2 * 1024 ** 3:
                self.log("提示：mkv 模式每卷上限将自动收敛到 2GB")
```

隐写循环内改为（`else` 分支保留现有 hide_file 调用与其后的 `processed_files += 1`）：

```python
        for input_file_path in hide_file_paths:
            if input_file_path:
                use_volume = volume_enabled and (
                    os.path.isdir(input_file_path)
                    or os.path.getsize(input_file_path) > volume_cap_bytes)
                if use_volume:
                    summary = self.steganographier.hide_volumized(
                        input_file_path=input_file_path,
                        volume_cap_bytes=volume_cap_bytes,
                        password=self.password,
                        processed_files=processed_files,
                        output_option=self.output_option_var.get(),
                        output_cover_video_name_mode=self.output_cover_video_name_mode_var.get(),
                        type_option_var=self.type_option_var.get(),
                        video_folder_path=self.video_folder_path,
                        volume_mode="split" if "真分卷" in self.volume_mode_var.get() else "zip")
                    processed_files += summary["volumes"]
                    if summary["volumes"] > 1:
                        self.log("已生成 %d 个分卷视频（上限 %dGB）"
                                 % (summary["volumes"], volume_cap_bytes // (1024 ** 3)))
                else:
                    self.steganographier.hide_file(
                        input_file_path=input_file_path,
                        password=self.password,
                        processed_files=processed_files,
                        output_option=self.output_option_var.get(),
                        output_cover_video_name_mode=self.output_cover_video_name_mode_var.get(),
                        type_option_var=self.type_option_var.get(),
                        video_folder_path=self.video_folder_path)
                    processed_files += 1
                self.update_progress(processed_files, total_files)
```

- [ ] **Step 4: 语法与 CLI 不回归**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe Steganographier.py --help
```
Expected: 编译通过；帮助正常（GUI 代码改动不影响 CLI 路径）。

- [ ] **Step 5: 提交**

```bash
git add Steganographier.py
git commit -m "Wire automatic volume splitting into the GUI with config persistence"
```

- [ ] **Step 6: 用户手测清单（附给用户，验收后勾）**

1. 勾选「自动分卷」、上限 1 GB，拖入一个 >2GB 的文件夹（或临时用 `--volume-size` 的等价小夹具）→ 进度条分卷推进、日志三行/卷、完成后弹窗汇总。
2. 模式选「真分卷」，重复一次 → 每个视频解出后得到 `.zip.001…` 与《解压说明.txt》。
3. 勾选分卷 + 工作模式选 `mp4(zarchiver)` → 拒绝启动并提示。
4. 不勾选分卷 → 行为与旧版完全一致。
5. 重启程序 → 勾选状态、上限、方式被记住。

---

### Task 9: 文档、全量验证与本地构建

**Files:**
- Modify: `README.md`、`CHANGELOG.md`、`VERSION`
- 产物: `dist` / `artifacts` 下的本地构建包（不入库）

**Interfaces:**
- Consumes: 全部前置任务。
- Produces: 可安装的本地发行包 + 文档。

- [ ] **Step 1: README 使用说明追加**

在「使用说明」CLI 参数列表之后新增一节（实际文案以仓库风格润色，内容含）：

```markdown
#### 自动分卷（大文件夹一次搞定）

内容超过设定上限时，自动按上限拆成多个视频，逐个隐写并即时清理中间文件，
磁盘峰值从"原内容 ×3"降到"原内容 + 输出 + 2×单卷上限"。

- GUI：勾选「自动分卷」，填每卷上限（GB），选择方式：
  - 独立压缩包（默认）：每个视频改后缀即可单独解压，全部解到同一文件夹自动拼回；
  - 真分卷：整套为 .zip.001 分卷，需 7-Zip / Bandizip / 新版 WinRAR 打开 .001 一次性解压（旧版 WinRAR 不支持）。
- CLI：`steg -i "D:\大文件夹" --volume-size 4G [--volume-mode split] [-p 密码]`
- 单个文件本身超过上限时：独立压缩包方式自动切成 .001 片段（附《合并说明.txt》）；真分卷方式直接纳入分卷。
- mkv 模式每卷上限自动收敛到 2GB；`mp4(zarchiver)` 模式不支持自动分卷。
```

- [ ] **Step 2: CHANGELOG 与 VERSION**

`VERSION` → `1.3.12`。`CHANGELOG.md` 顶部新增：

```markdown
## v1.3.12（本地构建）

### 新功能
- 自动分卷：大文件夹/超大单文件按上限（GB）自动拆分为多个隐写视频，逐卷压缩→隐写→清理，磁盘峰值显著降低。
  - 两种方式可选：独立压缩包（每卷可单独解压，默认）／真分卷 `.zip.001`（7-Zip/Bandizip/新版 WinRAR 一次合并解压）。
  - 超大单文件在独立压缩包方式下自动按 `.001` 惯例切块，并附《合并说明.txt》。
  - GUI 新增「自动分卷 / 每卷上限 / 方式」控件（配置持久化）；CLI 新增 `--volume-size`、`--volume-mode`。
```

- [ ] **Step 3: 全量测试（获用户同意后执行）**

```bash
./.venv/Scripts/python.exe -m py_compile Steganographier.py
./.venv/Scripts/python.exe Steganographier.py --help
./.venv/Scripts/python.exe scripts/test-volume-plan.py
./.venv/Scripts/python.exe scripts/test-volume-mode.py
./.venv/Scripts/python.exe scripts/test-cli-temp-archive.py
./.venv/Scripts/python.exe scripts/test-mp4-free-atom-format.py
./.venv/Scripts/python.exe scripts/test-reveal-keeps-original.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/validate-release.ps1
```
Expected: 全部通过。

- [ ] **Step 4: 本地构建（获用户同意后执行）**

```bash
./.venv/Scripts/python.exe -m pip install -r requirements-build.txt   # pyinstaller==6.11.1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/build-release.ps1
# 可选：装有 Inno Setup 6 时加 -BuildInstaller
```
Expected: 便携包构建 + 冒烟通过（脚本自带）；如 Python 3.12 与 pyinstaller 6.11.1 组合有问题，回退：安装 Python 3.8 到本地建专用 venv（与官方发行一致，`build-manifest.json` 记录 Python 3.8.10）再生产。产物验证：运行 exe `--help` 能看到 `--volume-size`；`VERSION` 显示 1.3.12。

- [ ] **Step 5: 提交**

```bash
git add README.md CHANGELOG.md VERSION
git commit -m "Document automatic volume splitting and bump version to 1.3.12"
```

---

## Spec 覆盖对照（写完计划后的自查）

| Spec 章节 | 对应任务 |
|---|---|
| §2 契约 C1/C2/C3 | Task 6（C1：每卷 ≤ 上限断言；C2：回归用例；C3：不改 reveal） |
| §4 模式 A 全部规则 | Task 3（挂包/切块/防碎片）+ Task 6（编排/命名/说明文件） |
| §5 模式 C 全部规则 | Task 1（spike 定参数）+ Task 7 |
| §6 空间/流水线/进度/失败语义 | Task 6（finally 清理、断点日志）+ Task 7 |
| §7 CLI 接口 | Task 6（参数/校验/-o 目录）+ Task 7（split 取值） |
| §8 GUI 接口 | Task 8 |
| §9 配置持久化 | Task 8 |
| §10 错误处理 | Task 3（预算下限）、Task 6（zarchiver/mkv/-o）、Task 8（GUI 校验） |
| §11 说明文案 | Task 6（合并说明）、Task 7（解压说明） |
| §12 兼容矩阵 | Task 1（WinRAR 实测回填） |
| §13 代码结构与重构红线 | Task 4/5（行为保持重构）+ 各任务回归步 |
| §14 测试与验收 | Task 2/3/6/7 测试脚本 + Task 9 全量 + Task 8 手测清单 |
| §15 spike | Task 1 |
| §16 非目标 | 未实现（计划不含 B 方案/续传/接收端合并工具） |
