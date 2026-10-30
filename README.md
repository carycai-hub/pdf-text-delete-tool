# PDF 批量删除文字工具

一个轻量脚本，用来**从 PDF 每一页精确删除指定文字**，其余内容原封不动。

适合场景：FBA 箱贴标签、抬头纸、批量合同等需要「去掉某个固定文字」的 PDF。

---

## 一、给完全不懂技术的同事：双击运行

1. 先安装一次依赖（只需一次）：
   - **Mac**：打开「终端」，粘贴这行回车：
     ```
     pip3 install pymupdf
     ```
   - **Windows**：打开「命令提示符」，粘贴这行回车：
     ```
     pip install pymupdf
     ```

2. 以后每次使用时：
   - 双击 `delete_pdf_text.py`
   - 按提示依次输入：PDF 文件路径（可直接把文件拖进窗口）、要删除的文字、是否保留前缀
   - 完成后会在同目录生成新文件

---

## 二、给稍懂命令行的同事：一条命令搞定

```bash
# 删除整段文字
python delete_pdf_text.py 标签.pdf "Shenzhen One Green Vegetable Technology Co., Ltd."

# 只删公司名，保留前面的 "FBA: "
python delete_pdf_text.py 标签.pdf "Shenzhen One Green Vegetable Technology Co., Ltd." --keep-prefix "FBA: "

# 指定输出文件名
python delete_pdf_text.py 标签.pdf "要删的文字" -o 新名字.pdf
```

> 注意：文字要**一字不差**，包括空格、大小写、逗号、句点。

---

## 三、原理说明（为什么要这么写）

PDF 里的文字不是像 Word 那样直接存内容，而是存了一串「打印指令」，例如：

```
(FBA: Shenzhen One Green Vegetable Technology Co., Ltd.)Tj
```

- 括号 `()` 里面 = 真正显示在页面上的文字
- `Tj` = 「显示」这个动作指令（不会出现在页面上）

本工具做的事情，就是把这行指令括号里的文字换掉：

```
旧：(FBA: Shenzhen One Green Vegetable Technology Co., Ltd.)Tj
新：(FBA:)Tj
```

因为只改了文字内容、没动其它任何指令，所以**除目标文字外，其余所有内容（排版、字体、条码、其他文字）一个字节都不会变**。

---

## 四、如何确认没改错

处理完成后，可以这样自查：

1. 打开新 PDF，全文搜索要删的文字 → 应该搜不到
2. 对比原文件，除了少了那行文字，其余一模一样
3. 页数不变，只是文件体积略小一点
