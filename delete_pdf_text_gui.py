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


def run_gui():
    root = tk.Tk()
    root.title("PDF 批量删除文字工具")
    root.geometry("640x480")
    root.resizable(False, False)

    pad = {"padx": 16, "pady": 6}

    # 标题
    tk.Label(root, text="PDF 批量删除指定文字", font=("Microsoft YaHei", 16, "bold")).pack(anchor="w", **pad)

    # 文件选择
    tk.Label(root, text="1. 选择 PDF 文件", font=("Microsoft YaHei", 10)).pack(anchor="w", **pad)
    file_frame = tk.Frame(root)
    file_frame.pack(fill="x", padx=16)
    file_var = tk.StringVar()
    file_entry = tk.Entry(file_frame, textvariable=file_var, width=50)
    file_entry.pack(side="left", fill="x", expand=True)
    tk.Button(file_frame, text="浏览…", command=lambda: file_var.set(
        filedialog.askopenfilename(filetypes=[("PDF 文件", "*.pdf")])
    )).pack(side="left", padx=(8, 0))

    # 要删除的文字
    tk.Label(root, text="2. 要删除的文字（一字不差，含空格/逗号/句点）", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=16, pady=(12, 0))
    target_var = tk.StringVar()
    tk.Entry(root, textvariable=target_var, width=60).pack(fill="x", padx=16)

    # 保留前缀
    tk.Label(root, text="3. 保留前缀（可选）：只删前缀后面的部分，前缀本身保留", font=("Microsoft YaHei", 10)).pack(anchor="w", padx=16, pady=(12, 0))
    prefix_var = tk.StringVar(value="FBA: ")
    tk.Entry(root, textvariable=prefix_var, width=60).pack(fill="x", padx=16)
    tk.Label(root, text="   示例：文字是“FBA: 某公司”，前缀填“FBA: ”，则只删“某公司”保留“FBA: ”", font=("Microsoft YaHei", 8), fg="#888").pack(anchor="w", **pad)

    # 状态栏
    status_var = tk.StringVar(value="请选择文件并填写要删除的文字")
    status = tk.Label(root, textvariable=status_var, fg="#333")
    status.pack(anchor="w", padx=16, pady=(16, 0))

    # 进度条
    progress = ttk.Progressbar(root, mode="indeterminate", length=600)
    progress.pack(padx=16, pady=8)

    # 按钮
    btn = tk.Button(root, text="开始处理", font=("Microsoft YaHei", 12, "bold"), bg="#1677ff", fg="white",
                    activebackground="#0f5fd6", activeforeground="white", width=16, height=1)
    btn.pack(pady=16)

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

        btn.config(state="disabled")
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
                root.after(0, lambda: (progress.stop(), btn.config(state="normal"), status_var.set("就绪，可再次处理")))

        threading.Thread(target=_run, daemon=True).start()

    btn.config(command=do_work)

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
