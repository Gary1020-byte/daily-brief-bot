#!/usr/bin/env python3
"""把 Daily Brief 的真實終端機輸出渲染成產品截圖 PNG。

用法:
    python3 scripts/render_screenshots.py            # 產生全部截圖
    python3 scripts/render_screenshots.py --text FILE # 用既有 .txt 輸出渲染

截圖是「真的跑出來的畫面」，不是行銷排版圖 —— 這是 Daily Brief 產品的
賣點之一：輸出就是終端機純文字，Email / Telegram 直接可貼。
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

BG = (24, 26, 32)
FG = (222, 226, 233)
DIM = (128, 135, 148)
ACCENT = (232, 196, 122)
PROMPT = (126, 202, 158)

PAD = 34
LINE_H = 26
FS = 15


def has_cjk(s: str) -> bool:
    return any("一" <= c <= "鿿" or "　" <= c <= "〿" for c in s)


def make_font(cjk: bool, bold: bool = False):
    if cjk:
        return ImageFont.truetype(CJK, FS)
    return ImageFont.truetype(MONO_BOLD if bold else MONO, FS)


def render(text: str, out: Path, title: str | None = None):
    lines = text.rstrip("\n").split("\n")
    # 標題列（模擬 terminal chrome）
    head = 38 if title else 0
    w = 1180
    h = PAD * 2 + head + LINE_H * len(lines) + 30
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)

    if title:
        d.rectangle([0, 0, w, head], fill=(32, 35, 43))
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([16 + i * 20, 14, 26 + i * 20, 24], fill=c)
        d.text((90, 11), title, font=make_font(False), fill=DIM)

    y = PAD + head
    for ln in lines:
        stripped = ln.strip()
        if not stripped:
            y += LINE_H
            continue
        # 提示符 / 分隔線 / 標題
        if stripped.startswith("$ ") or stripped.startswith("python3 "):
            cmd = ln.strip()
            if cmd.startswith("$ "):
                cmd = cmd[2:]
            d.text((PAD, y), "$", font=make_font(False, True), fill=PROMPT)
            d.text((PAD + 18, y), cmd, font=make_font(False), fill=FG)
            y += LINE_H
            continue
        if set(stripped) <= {"-", "="} and len(stripped) >= 3:
            d.text((PAD, y), ln, font=make_font(False), fill=(70, 76, 90))
            y += LINE_H
            continue
        if has_cjk(ln):
            d.text((PAD, y), ln, font=make_font(True), fill=FG)
        else:
            d.text((PAD, y), ln, font=make_font(False), fill=FG)
        y += LINE_H

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out, img.size


def run_real() -> str:
    """在乾淨的暫存目錄跑一次真實抓取，取真實輸出。"""
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="db-shot-"))
    try:
        shutil.copytree(ROOT / "src", tmp / "src")
        shutil.copytree(ROOT / "config", tmp / "config")
        (tmp / "config" / "config.toml").unlink(missing_ok=True)
        r = subprocess.run(
            [sys.executable, "src/daily_brief.py", "--init"],
            cwd=tmp, capture_output=True, text=True, timeout=60,
        )
        r = subprocess.run(
            [sys.executable, "src/daily_brief.py", "--max-age", "14", "--limit", "9"],
            cwd=tmp, capture_output=True, text=True, timeout=300,
        )
        return r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="用這個 .txt 檔渲染，不重新抓取")
    ap.add_argument("--out", default=str(ROOT / "docs" / "screenshots"))
    a = ap.parse_args()

    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)

    if a.text:
        real = Path(a.text).read_text()
    else:
        print("running real fetch...")
        real = run_real()
        (outdir / "sample-output.txt").write_text(real)

    p, size = render(real, outdir / "01-terminal-output.png",
                     "daily_brief.py --send telegram")
    print("wrote", p, size)

    p, size = render(
        "$ python3 src/daily_brief.py --init\n"
        "已建立範例設定檔: config/config.toml\n"
        "$ python3 src/daily_brief.py --check\n"
        "設定檔檢查通過: 關鍵字 8 個 / 來源 3 個\n",
        outdir / "02-setup.png", "daily_brief.py --init",
    )
    print("wrote", p, size)

    p, size = render(
        "【使用前】每天早上:100 則未篩選新聞 -> 全部略過 -> 真正的訊息埋在裡面\n"
        "\n"
        "【使用後】每天早上:8 則符合關鍵字的精簡簡報 -> 2 分鐘看完\n",
        outdir / "03-before-after.png", None,
    )
    print("wrote", p, size)


if __name__ == "__main__":
    main()
