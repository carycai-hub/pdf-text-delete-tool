#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 批量删除指定文字工具（图形界面版 · 深色玻璃拟态）

双击运行后，会弹出一个深色玻璃质感的窗口：
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

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import tkinter.font as tkfont
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


# ==================== 配色（深色玻璃拟态）====================
BG = "#1c1c1e"          # 窗口背景（深黑）
CARD = "#2c2c2e"        # 卡片背景（深灰）
CARD_EDGE = "#3a3a3c"   # 卡片描边
FIELD = "#3a3a3c"       # 输入框背景
FIELD_EDGE = "#48484a"  # 输入框描边
FG = "#ffffff"          # 主文字（白）
FG_SUB = "#d8d8dc"      # 次级文字
FG_HINT = "#8e8e93"     # 提示文字
ACCENT = "#0a84ff"      # 强调色（macOS 系统蓝）
ACCENT_HOVER = "#3395ff"
FONT = "PingFang SC"


def rrect(cvs, x0, y0, x1, y1, r, **kw):
    """在 canvas 上画圆角矩形。"""
    cvs.create_arc(x0, y0, x0 + 2 * r, y0 + 2 * r, start=90, extent=90, style="pieslice", **kw)
    cvs.create_arc(x1 - 2 * r, y0, x1, y0 + 2 * r, start=0, extent=90, style="pieslice", **kw)
    cvs.create_arc(x0, y1 - 2 * r, x0 + 2 * r, y1, start=180, extent=90, style="pieslice", **kw)
    cvs.create_arc(x1 - 2 * r, y1 - 2 * r, x1, y1, start=270, extent=90, style="pieslice", **kw)
    cvs.create_rectangle(x0 + r, y0, x1 - r, y1, **kw)
    cvs.create_rectangle(x0, y0 + r, x1, y1 - r, **kw)


def run_gui():
    root = tk.Tk()
    root.title("PDF 批量删除文字工具")
    W, H = 700, 580
    root.geometry(f"{W}x{H}")
    root.resizable(False, False)
    root.configure(bg=BG)

    # 主画布
    cvs = tk.Canvas(root, width=W, height=H, bg=BG, highlightthickness=0, bd=0)
    cvs.pack(fill="both", expand=True)

    # ===== 标题 =====
    cvs.create_text(28, 40, text="删除 PDF 中的指定文字", anchor="w",
                    fill=FG, font=(FONT, 20, "bold"))
    cvs.create_text(28, 68, text="三步即可清理文档中的目标文本，其余内容保持不变",
                    anchor="w", fill=FG_HINT, font=(FONT, 11))

    # ===== 布局常量 =====
    MARGIN = 28           # 左右边距
    CARD_W = W - 2 * MARGIN   # 卡片宽度 644
    CARD_X = MARGIN
    CARD_H = 82
    CARD_R = 14
    GAP = 12

    # 卡片起始 Y
    y_cards = 92

    def draw_card(y, num, title, hint):
        """画一张卡片，返回 (内容区左上 x, 内容区左上 y)。"""
        rrect(cvs, CARD_X, y, CARD_X + CARD_W, y + CARD_H, CARD_R,
              fill=CARD, outline=CARD_EDGE)
        # 编号徽章
        cvs.create_oval(CARD_X + 16, y + 16, CARD_X + 16 + 22, y + 16 + 22,
                        fill=ACCENT, outline=ACCENT)
        cvs.create_text(CARD_X + 16 + 11, y + 16 + 11, text=str(num),
                        fill="#ffffff", font=(FONT, 11, "bold"))
        # 标题
        cvs.create_text(CARD_X + 50, y + 18, text=title, anchor="w",
                        fill=FG, font=(FONT, 12, "bold"))
        cvs.create_text(CARD_X + 50, y + 38, text=hint, anchor="w",
                        fill=FG_HINT, font=(FONT, 9))
        return CARD_X + 50, y + 46

    # ===== 卡片 1：选择文件 =====
    y1 = y_cards
    cx, cy = draw_card(y1, 1, "选择 PDF 文件", "拖入或点击选择需要处理的 PDF")

    file_var = tk.StringVar()
    file_entry = tk.Entry(root, textvariable=file_var, font=(FONT, 11),
                          bg=FIELD, fg=FG, insertbackground=FG,
                          relief="flat", highlightthickness=0)
    file_win = cvs.create_window(cx, cy, width=400, height=26, anchor="nw", window=file_entry)

    # 浏览按钮（自绘）
    browse_w, browse_h = 70, 30
    browse_bx = CARD_X + CARD_W - 20 - browse_w
    browse_by = y1 + 42
    rrect(cvs, browse_bx, browse_by, browse_bx + browse_w, browse_by + browse_h,
          browse_h // 2, fill=ACCENT, outline=ACCENT)
    browse_txt = cvs.create_text(browse_bx + browse_w // 2, browse_by + browse_h // 2,
                                 text="浏览", fill="#ffffff", font=(FONT, 11))

    def on_browse(e):
        path = filedialog.askopenfilename(filetypes=[("PDF 文件", "*.pdf")])
        if path:
            file_var.set(path)

    cvs.tag_bind(browse_txt, "<Button-1>", on_browse)

    # ===== 卡片 2：要删除的文字 =====
    y2 = y1 + CARD_H + GAP
    cx2, cy2 = draw_card(y2, 2, "要删除的文字", "一字不差，含空格、逗号、句点")
    target_var = tk.StringVar()
    target_entry = tk.Entry(root, textvariable=target_var, font=(FONT, 11),
                            bg=FIELD, fg=FG, insertbackground=FG,
                            relief="flat", highlightthickness=0)
    cvs.create_window(cx2, cy2, width=568, height=26, anchor="nw", window=target_entry)

    # ===== 卡片 3：保留前缀 =====
    y3 = y2 + CARD_H + GAP
    cx3, cy3 = draw_card(y3, 3, "保留前缀（可选）", "只删前缀后面的部分，前缀本身保留")
    prefix_var = tk.StringVar(value="FBA: ")
    prefix_entry = tk.Entry(root, textvariable=prefix_var, font=(FONT, 11),
                            bg=FIELD, fg=FG, insertbackground=FG,
                            relief="flat", highlightthickness=0)
    cvs.create_window(cx3, cy3, width=568, height=26, anchor="nw", window=prefix_entry)

    # 示例说明
    cvs.create_text(CARD_X + 2, y3 + CARD_H + 8, anchor="w",
                    text="示例：文字是“FBA: 某公司”，前缀填“FBA: ”，则只删“某公司”保留“FBA: ”",
                    fill=FG_HINT, font=(FONT, 9))

    # ===== 状态栏 =====
    status_y = y3 + CARD_H + 38
    status_var = tk.StringVar(value="就绪，请选择文件并填写要删除的文字")
    status_id = cvs.create_text(MARGIN, status_y, anchor="w", text=status_var.get(),
                                fill=FG_HINT, font=(FONT, 10))

    # ===== 进度条 =====
    prog_y = status_y + 22
    cvs.create_rectangle(MARGIN, prog_y, W - MARGIN, prog_y + 6, fill=FIELD_EDGE, outline="")
    prog_rect = cvs.create_rectangle(MARGIN, prog_y, MARGIN, prog_y + 6, fill=ACCENT, outline="")
    prog_running = [False]

    def start_progress():
        prog_running[0] = True
        _animate()

    def _animate():
        if not prog_running[0]:
            return
        step = getattr(_animate, "step", -200)
        step += 8
        if step > (W - 2 * MARGIN) + 200:
            step = -200
        _animate.step = step
        cvs.coords(prog_rect, MARGIN + max(step, 0), prog_y,
                   MARGIN + min(step + 200, W - 2 * MARGIN), prog_y + 6)
        root.after(30, _animate)

    def stop_progress():
        prog_running[0] = False
        cvs.coords(prog_rect, MARGIN, prog_y, MARGIN, prog_y + 6)

    # ===== 主按钮 =====
    btn_y = prog_y + 30
    btn_w, btn_h = 180, 46
    btn_x = (W - btn_w) // 2
    rrect(cvs, btn_x, btn_y, btn_x + btn_w, btn_y + btn_h, btn_h // 2,
          fill=ACCENT, outline=ACCENT)
    btn_txt = cvs.create_text(btn_x + btn_w // 2, btn_y + btn_h // 2,
                              text="开始处理", fill="#ffffff", font=(FONT, 14))

    def on_btn_enter(e):
        rrect(cvs, btn_x, btn_y, btn_x + btn_w, btn_y + btn_h, btn_h // 2,
              fill=ACCENT_HOVER, outline=ACCENT_HOVER)
        cvs.tag_raise(btn_txt)

    def on_btn_leave(e):
        rrect(cvs, btn_x, btn_y, btn_x + btn_w, btn_y + btn_h, btn_h // 2,
              fill=ACCENT, outline=ACCENT)
        cvs.tag_raise(btn_txt)

    def do_work(e=None):
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

        start_progress()
        status_var.set("正在处理……")
        cvs.itemconfigure(status_id, text=status_var.get())

        def _run():
            try:
                total, matched, out = delete_text(input_path, target, prefix)
                msg = f"处理完成！\n\n总页数：{total}\n命中删除：{matched} 页"
                if matched < total:
                    msg += f"\n\n⚠️ 有 {total - matched} 页未找到目标文字（可能文字不一致）"
                msg += f"\n\n输出文件：\n{out}"
                root.after(0, lambda: messagebox.showinfo("完成", msg))
            except Exception as ex:
                root.after(0, lambda: messagebox.showerror("出错", str(ex)))
            finally:
                def _finish():
                    stop_progress()
                    status_var.set("就绪，可再次处理")
                    cvs.itemconfigure(status_id, text=status_var.get())
                root.after(0, _finish)

        threading.Thread(target=_run, daemon=True).start()

    cvs.tag_bind(btn_txt, "<Button-1>", do_work)
    cvs.tag_bind(btn_txt, "<Enter>", on_btn_enter)
    cvs.tag_bind(btn_txt, "<Leave>", on_btn_leave)

    # 让状态文字实时刷新（通过 trace）
    def on_status_change(*_):
        cvs.itemconfigure(status_id, text=status_var.get())
    status_var.trace_add("write", on_status_change)

    root.mainloop()


def main():
    if HAS_TK:
        run_gui()
        return

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
