#!/usr/bin/env python3
"""打包 Daily Brief 成可上架的 zip。

規則:
- 只打包買家需要的檔案（程式、範例設定、文件、截圖）
- 絕不打包作者的私人 config.toml / state.json / __pycache__
- 固定 timestamp，讓同樣輸入產生 byte-identical 的 zip（方便驗證）

用法:
    python3 scripts/package.py [--out ../daily-brief-v1.0.zip]
"""
import argparse
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# 買家套件包含哪些（相對 ROOT）
INCLUDE_FILES = [
    "README.md",
    "README.zh-TW.md",
    "LICENSE",
    "CHANGELOG.md",
    "src/daily_brief.py",
    "config/config.example.toml",
    "docs/product-page-copy.md",
    "docs/screenshots/sample-output.txt",
    "docs/screenshots/01-terminal-output.png",
    "docs/screenshots/02-setup.png",
    "docs/screenshots/03-before-after.png",
]

EXCLUDE_PARTS = {"__pycache__", ".git", ".github", "config.toml", "state.json"}
FIXED_TIME = (2026, 10, 25, 0, 0, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "daily-brief-v1.0.zip"))
    a = ap.parse_args()

    missing = [f for f in INCLUDE_FILES if not (ROOT / f).exists()]
    if missing:
        print("缺少檔案:", missing, file=sys.stderr)
        return 1

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prefix = ROOT.name

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in INCLUDE_FILES:
            src = ROOT / f
            info = zipfile.ZipInfo(f"{prefix}/{f}", date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, src.read_bytes())

    # 自我檢查：包裡不能有私人檔案
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        for n in names:
            if any(p in n for p in EXCLUDE_PARTS) or n.endswith(".pyc"):
                print("!! 不該出現在套件裡:", n, file=sys.stderr)
                return 1
        if f"{prefix}/config/config.example.toml" not in names:
            print("!! 缺少範例設定檔", file=sys.stderr)
            return 1

    size = out.stat().st_size
    print(f"wrote {out}  ({len(names)} files, {size} bytes)")
    for n in names:
        print("  ", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
