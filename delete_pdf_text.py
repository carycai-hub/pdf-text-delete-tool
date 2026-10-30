#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 批量删除指定文字工具

功能：从 PDF 的每一页中，精确删除指定的文字片段，其余内容保持原样不动。

原理：不重新排版，不重新导出，只替换 PDF 内容流里的文字指令，
因此除目标文字外，其余所有内容（排版、字体、条码、其他文字）一个字节都不会变。

用法一（命令行，灵活指定）：
    python delete_pdf_text.py 输入.pdf "要删除的文字"

用法二（交互式，双击运行）：
    直接双击本脚本，按提示输入即可。

可选参数：
    -o 输出文件名（默认：原文件名_deleted.pdf）
    --keep-prefix 前缀：只删除前缀后面的部分，保留前缀本身
        例如原文字 "FBA: 某公司", 加 --keep-prefix "FBA: " 会只删 "某公司" 保留 "FBA: "

示例：
    # 删除整段文字
    python delete_pdf_text.py 标签.pdf "Shenzhen One Green Vegetable Technology Co., Ltd."

    # 只删公司名，保留前面的 "FBA: "
    python delete_pdf_text.py 标签.pdf "Shenzhen One Green Vegetable Technology Co., Ltd." --keep-prefix "FBA: "

依赖：pip install pymupdf
"""

import sys
import os

try:
    import fitz  # PyMuPDF
except ImportError:
    print("缺少依赖 pymupdf，正在尝试安装……")
    os.system(f"{sys.executable} -m pip install pymupdf")
    try:
        import fitz
    except ImportError:
        print("安装失败，请手动执行：pip install pymupdf")
        sys.exit(1)


def delete_text(input_path, target_text, output_path=None, keep_prefix=""):
    """删除 PDF 每一页中的 target_text，返回处理的页数统计。"""
    if not os.path.exists(input_path):
        print(f"❌ 文件不存在：{input_path}")
        sys.exit(1)

    if not target_text or not target_text.strip():
        print("❌ 要删除的文字不能为空")
        sys.exit(1)

    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_deleted{ext}"

    doc = fitz.open(input_path)
    total_pages = doc.page_count
    matched_pages = 0

    # 目标：完整的一段文字（含可选前缀）
    full_text = keep_prefix + target_text

    for i in range(total_pages):
        page = doc[i]
        xrefs = page.get_contents()
        replaced = False

        for xref in xrefs:
            stream = doc.xref_stream(xref)
            if stream is None:
                continue

            # 直接在内容流里查找并替换文字指令 (....)Tj
            old = f"({full_text})Tj".encode("latin-1", "replace")
            new = f"({keep_prefix})Tj".encode("latin-1", "replace")

            if old in stream:
                stream = stream.replace(old, new)
                doc.update_stream(xref, stream)
                replaced = True

        if replaced:
            matched_pages += 1

    doc.save(output_path)
    doc.close()

    return total_pages, matched_pages, output_path


def main():
    args = sys.argv[1:]

    # 解析 --keep-prefix 和 -o
    keep_prefix = ""
    output_path = None
    positional = []
    i = 0
    while i < len(args):
        if args[i] == "--keep-prefix":
            if i + 1 < len(args):
                keep_prefix = args[i + 1]
                i += 2
            else:
                print("❌ --keep-prefix 后面需要跟内容")
                sys.exit(1)
        elif args[i] == "-o":
            if i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
            else:
                print("❌ -o 后面需要跟输出文件名")
                sys.exit(1)
        else:
            positional.append(args[i])
            i += 1

    # 交互式模式：没有命令行参数时，提示输入
    if not positional:
        print("=" * 50)
        print("  PDF 批量删除指定文字工具")
        print("=" * 50)
        input_path = input("请输入 PDF 文件路径（可直接拖入）：").strip().strip('"').strip("'")
        target_text = input("请输入要删除的文字：").strip()
        keep_prefix = input(
            "是否保留文字前面的某段前缀？\n"
            "  - 留空：删除整段文字\n"
            "  - 例如输入 'FBA: ' 则只删 'FBA: ' 后面的部分\n"
            "请输入前缀（留空则直接回车）："
        ).strip()
        output_path = input(
            "请输入输出文件名（留空则自动生成「原文件名_deleted.pdf」）："
        ).strip() or None
    else:
        input_path = positional[0]
        target_text = positional[1] if len(positional) > 1 else None

        if target_text is None:
            target_text = input("请输入要删除的文字：").strip()

    if not target_text:
        print("❌ 要删除的文字不能为空")
        sys.exit(1)

    print("\n开始处理……")
    total, matched, out = delete_text(input_path, target_text, output_path, keep_prefix)

    print("\n" + "=" * 50)
    print("✅ 处理完成！")
    print(f"   总页数：{total}")
    print(f"   命中并删除的页数：{matched}")
    if matched < total:
        print(f"   ⚠️ 有 {total - matched} 页未找到目标文字（可能文字不同或已删除）")
    print(f"   输出文件：{out}")
    print("=" * 50)


if __name__ == "__main__":
    main()
