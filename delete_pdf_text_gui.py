#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 批量删除指定文字工具（图形界面版）

双击运行后，会弹出一个窗口：
  - 选择/拖入 PDF 文件
  - 输入要删除的文字
  - （可选）输入要保留的前缀，例如 "FBA: "
  - 点击「开始处理」即可生成新 PDF

原理：不重新排版，只替换 PDF 内容流里的文字指令，
除目标文字外，其余内容一个字节都不变。
"""

import os
import sys
import threading

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# 尝试导入 tkinter（Python 标准库自带）
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    HAS_TK = True
except ImportError:
    HAS_TK = False


def delete_text(input_path, target_text, keep_prefix=""):
    """删除 PDF 每一页中的 target_text，返回 (总页数, 命中页数)。"""
    if fitz is None:
        raise RuntimeError("缺少 pymupdf 依赖，请先安装：pip install pymupdf")

    doc = fitz.open(input_path)
    total = doc.page_count
    matched = 0

    full_text = keep_prefix + target_text
    old = f"({full_text})Tj".encode("latin-1", "replace")
    new = f"({keep_prefix})Tj".encode("latin-1", "replace")

    for i in range(total):
        page = doc[i]
        xrefs = page.get_contents()
        replaced = False
        for xref in xrefs:
            stream = doc.xref_stream(xref)
            if stream is None:
                continue
            if old in stream:
                stream = stream.replace(old, new)
                doc.update_stream(xref, stream)
                replaced = True
        if replaced:
            matched += 1

    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_deleted{ext}"
    doc.save(output_path)
    doc.close()
    return total, matched, output_path


def make_button(parent, text, command, bg="#1677ff", fg="#ffffff", hover="#0f5fd6",
                font=("PingFang SC", 13, "bold"), padx=24, pady=10, disabled=False):
    """用 Canvas 绘制自定义按钮，解决 macOS 上 tk 按钮不显示 bg 颜色的问题。"""
    cvs = tk.Canvas(parent, highlightthickness=0, bd=0)
    # 先测量文字宽度来确定按钮宽度
    import tkinter.font as tkfont
    f = tkfont.Font(family=font[0], size=font[1], weight="bold")
    tw = f.measure(text)
    th = f.metrics("linespace")
    w = tw + padx * 2
    h = th + pady * 2
    cvs.configure(width=w, height=h)

    radius = h // 2
    x0, y0, x1, y1 = 0, 0, w, h
    color = bg if not disabled else "#b0b0b0"

    def draw(c=color):
        cvs.delete("all")
        cvs.create_oval(x0, y0, x0 + 2 * radius, y0 + 2 * radius, fill=c, outline=c)
        cvs.create_oval(x1 - 2 * radius, y0, x1, y0 + 2 * radius, fill=c, outline=c)
        cvs.create_rectangle(x0 + radius, y0, x1 - radius, y1, fill=c, outline=c)
        cvs.create_text(w // 2, h // 2, text=text, fill=fg, font=font)

    draw()

    def on_enter(e):
        if not disabled:
            draw(hover)

    def on_leave(e):
        if not disabled:
            draw(bg)

    def on_click(e):
        if not disabled:
            command()

    cvs.bind("<Enter>", on_enter)
    cvs.bind("<Leave>", on_leave)
    cvs.bind("<Button-1>", on_click)
    cvs.configure(cursor="hand2" if not disabled else "arrow")
    return cvs


def run_gui():
    root = tk.Tk()
    root.title("PDF 批量删除文字工具")
    root.geometry("680x520")
    root.resizable(False, False)

    # 固定使用浅色主题配色，保证文字在任何系统主题下都清晰可读
    BG = "#f5f6f8"        # 窗口背景（浅灰）
    CARD = "#ffffff"      # 卡片/输入框背景
    FG = "#1a1a1a"        # 主文字（深黑）
    FG_SUB = "#555555"    # 次级文字
    FG_HINT = "#888888"   # 提示文字
    ACCENT = "#1677ff"    # 强调色（蓝）
    BORDER = "#d0d3d8"    # 边框

    root.configure(bg=BG)

    pad = {"padx": 20, "pady": 6}

    # 标题
    tk.Label(root, text="PDF 批量删除指定文字", font=("PingFang SC", 17, "bold"),
             bg=BG, fg=FG).pack(anchor="w", padx=20, pady=(18, 4))

    def section_label(text, top=14):
        tk.Label(root, text=text, font=("PingFang SC", 11),
                 bg=BG, fg=FG_SUB).pack(anchor="w", padx=20, pady=(top, 4))

    # 1. 文件选择
    section_label("1. 选择 PDF 文件", top=10)
    file_frame = tk.Frame(root, bg=BG)
    file_frame.pack(fill="x", padx=20)
    file_var = tk.StringVar()
    file_entry = tk.Entry(file_frame, textvariable=file_var, width=50,
                          font=("PingFang SC", 11), bg=CARD, fg=FG,
                          relief="solid", bd=1, highlightthickness=0)
    file_entry.pack(side="left", fill="x", expand=True, ipady=5)
    browse_btn = make_button(
        file_frame, "浏览…",
        command=lambda: file_var.set(
            filedialog.askopenfilename(filetypes=[("PDF 文件", "*.pdf")])),
        font=("PingFang SC", 11, "bold"), padx=18, pady=6)
    browse_btn.pack(side="left", padx=(10, 0))

    # 2. 要删除的文字
    section_label("2. 要删除的文字（一字不差，含空格/逗号/句点）")
    target_var = tk.StringVar()
    tk.Entry(root, textvariable=target_var, width=60, font=("PingFang SC", 11),
             bg=CARD, fg=FG, relief="solid", bd=1).pack(fill="x", padx=20, ipady=5)

    # 3. 保留前缀
    section_label("3. 保留前缀（可选）：只删前缀后面的部分，前缀本身保留")
    prefix_var = tk.StringVar(value="FBA: ")
    tk.Entry(root, textvariable=prefix_var, width=60, font=("PingFang SC", 11),
             bg=CARD, fg=FG, relief="solid", bd=1).pack(fill="x", padx=20, ipady=5)
    tk.Label(root, text="示例：文字是“FBA: 某公司”，前缀填“FBA: ”，则只删“某公司”保留“FBA: ”",
             font=("PingFang SC", 9), bg=BG, fg=FG_HINT).pack(anchor="w", padx=20, pady=(4, 0))

    # 状态栏
    status_var = tk.StringVar(value="请选择文件并填写要删除的文字")
    status = tk.Label(root, textvariable=status_var, font=("PingFang SC", 10), bg=BG, fg=FG_SUB)
    status.pack(anchor="w", padx=20, pady=(18, 4))

    # 进度条
    progress = ttk.Progressbar(root, mode="indeterminate", length=640)
    progress.pack(padx=20, pady=(0, 4))

    # 按钮（用 Canvas 自定义，确保蓝色底白字在任何系统都清晰可见）
    btn = make_button(root, "开始处理", command=None, font=("PingFang SC", 14, "bold"),
                      padx=36, pady=12)
    btn.pack(pady=14)

    def do_work():
        input_path = file_var.get().strip().strip('"')
        target = target_var.get().strip()
        prefix = prefix_var.get()

        if not input_path:
            messagebox.showwarning("提示", "请先选择 PDF 文件")
            return
        if not target:
            messagebox.showwarning("提示", "请输入要删除的文字")
            return
        if not os.path.exists(input_path):
            messagebox.showerror("错误", f"文件不存在：\n{input_path}")
            return

        progress.start(12)
        status_var.set("正在处理……")

        def _run():
            try:
                total, matched, out = delete_text(input_path, target, prefix)
                msg = f"处理完成！\n\n总页数：{total}\n命中删除：{matched} 页"
                if matched < total:
                    msg += f"\n\n⚠️ 有 {total - matched} 页未找到目标文字（可能文字不一致）"
                msg += f"\n\n输出文件：\n{out}"
                root.after(0, lambda: messagebox.showinfo("完成", msg))
            except Exception as e:
                root.after(0, lambda: messagebox.showerror("出错", str(e)))
            finally:
                root.after(0, lambda: (progress.stop(), status_var.set("就绪，可再次处理")))

        threading.Thread(target=_run, daemon=True).start()

    # 将 do_work 绑定到按钮的点击事件
    btn.bind("<Button-1>", lambda e: do_work())

    root.mainloop()


def main():
    # 图形界面模式
    if HAS_TK:
        run_gui()
        return

    # 无 tkinter 时的命令行兜底
    if len(sys.argv) < 3:
        print("用法：python delete_pdf_text.py 输入.pdf \"要删除的文字\" [--keep-prefix \"前缀\"]")
        sys.exit(1)

    input_path = sys.argv[1]
    target = sys.argv[2]
    prefix = ""
    if "--keep-prefix" in sys.argv:
        idx = sys.argv.index("--keep-prefix")
        if idx + 1 < len(sys.argv):
            prefix = sys.argv[idx + 1]

    total, matched, out = delete_text(input_path, target, prefix)
    print(f"处理完成：总 {total} 页，命中 {matched} 页")
    print(f"输出：{out}")


if __name__ == "__main__":
    main()
