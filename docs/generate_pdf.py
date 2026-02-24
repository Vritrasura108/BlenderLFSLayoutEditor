"""
Generate guide.pdf from all markdown files in the docs/ folder.

Usage:
    python docs/generate_pdf.py
"""

import subprocess
import sys
import glob
import os
import re

REQUIRED_PACKAGES = {"pymupdf": "fitz"}


def ensure_dependencies():
    missing = []
    for pkg, import_name in REQUIRED_PACKAGES.items():
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return

    print(f"Missing packages: {', '.join(missing)}")
    answer = input("Install them now? [Y/n]: ").strip().lower()
    if answer and answer != "y":
        print("Aborted. Install manually: pip install " + " ".join(missing))
        sys.exit(1)

    subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
    print()


ensure_dependencies()

import fitz  # noqa: E402

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(DOCS_DIR)
OUTPUT_PDF = os.path.join(REPO_DIR, "guide.pdf")

# Page layout
PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 60
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN

# Fonts
FONT_BODY = "helv"
FONT_BOLD = "hebo"
FONT_MONO = "cour"
FONT_SIZE_H1 = 22
FONT_SIZE_H2 = 16
FONT_SIZE_H3 = 13
FONT_SIZE_BODY = 11
FONT_SIZE_SMALL = 9
LINE_HEIGHT = 1.4


def collect_markdown_files():
    """Collect all .md files from docs/ sorted alphabetically."""
    pattern = os.path.join(DOCS_DIR, "*.md")
    files = sorted(glob.glob(pattern))
    return files


def parse_markdown(md_path):
    """Parse a markdown file into a list of content blocks."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i]

        # Headings
        if line.startswith("# "):
            blocks.append(("h1", line[2:].strip()))
            i += 1
        elif line.startswith("## "):
            blocks.append(("h2", line[3:].strip()))
            i += 1
        elif line.startswith("### "):
            blocks.append(("h3", line[4:].strip()))
            i += 1

        # Images
        elif re.match(r"!\[.*?\]\(.*?\)", line):
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            if m:
                alt, src = m.group(1), m.group(2)
                img_path = os.path.normpath(os.path.join(DOCS_DIR, src))
                blocks.append(("image", img_path, alt))
            i += 1

        # Blockquote
        elif line.startswith("> "):
            quote_lines = []
            while i < len(lines) and lines[i].startswith("> "):
                quote_lines.append(lines[i][2:])
                i += 1
            blocks.append(("quote", " ".join(quote_lines)))

        # Unordered list item
        elif line.startswith("- "):
            blocks.append(("list_item", line[2:].strip()))
            i += 1

        # Non-empty paragraph text
        elif line.strip():
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "!", ">", "- ")):
                para_lines.append(lines[i])
                i += 1
            blocks.append(("paragraph", " ".join(para_lines)))

        else:
            i += 1

    return blocks


def strip_markdown_inline(text):
    """Remove inline markdown formatting for plain text rendering."""
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    # Inline code
    text = re.sub(r"`(.*?)`", r"\1", text)
    # Links [text](url)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    # Quotes
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text


def render_text_wrapped(page, text, x, y, max_width, fontname, fontsize):
    """Render text with word wrapping. Returns the y position after the text."""
    words = text.split()
    current_line = ""
    line_y = y

    for word in words:
        test = f"{current_line} {word}".strip()
        tw = fitz.get_text_length(test, fontname=fontname, fontsize=fontsize)
        if tw > max_width and current_line:
            page.insert_text(
                (x, line_y), current_line,
                fontname=fontname, fontsize=fontsize, color=(0, 0, 0),
            )
            line_y += fontsize * LINE_HEIGHT
            current_line = word
        else:
            current_line = test

    if current_line:
        page.insert_text(
            (x, line_y), current_line,
            fontname=fontname, fontsize=fontsize, color=(0, 0, 0),
        )
        line_y += fontsize * LINE_HEIGHT

    return line_y


def render_rich_text_wrapped(page, text, x, y, max_width, fontsize):
    """Render text with bold and code spans, word wrapping."""
    # Split text into segments: (text, style) where style is 'normal', 'bold', 'code'
    segments = []
    pattern = re.compile(r"(\*\*.*?\*\*|`.*?`)")
    parts = pattern.split(text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            segments.append((part[2:-2], "bold"))
        elif part.startswith("`") and part.endswith("`"):
            segments.append((part[1:-1], "code"))
        else:
            segments.append((part, "normal"))

    # Flatten into words with style
    styled_words = []
    for seg_text, style in segments:
        for word in seg_text.split():
            styled_words.append((word, style))

    font_map = {"normal": FONT_BODY, "bold": FONT_BOLD, "code": FONT_MONO}
    current_line_words = []
    current_width = 0
    line_y = y

    def flush_line():
        nonlocal line_y
        lx = x
        for w, s in current_line_words:
            fn = font_map[s]
            page.insert_text((lx, line_y), w + " ", fontname=fn, fontsize=fontsize, color=(0, 0, 0))
            lx += fitz.get_text_length(w + " ", fontname=fn, fontsize=fontsize)
        line_y += fontsize * LINE_HEIGHT

    space_width = fitz.get_text_length(" ", fontname=FONT_BODY, fontsize=fontsize)

    for word, style in styled_words:
        fn = font_map[style]
        ww = fitz.get_text_length(word + " ", fontname=fn, fontsize=fontsize)
        if current_width + ww > max_width and current_line_words:
            flush_line()
            current_line_words = []
            current_width = 0
        current_line_words.append((word, style))
        current_width += ww

    if current_line_words:
        flush_line()

    return line_y


def generate_pdf():
    md_files = collect_markdown_files()
    if not md_files:
        print("No markdown files found in docs/")
        return

    doc = fitz.open()
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN

    def ensure_space(needed):
        nonlocal page, y
        if y + needed > PAGE_HEIGHT - MARGIN:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = MARGIN
        return page

    for md_file in md_files:
        print(f"Processing: {os.path.basename(md_file)}")
        blocks = parse_markdown(md_file)

        for block in blocks:
            btype = block[0]

            if btype == "h1":
                ensure_space(40)
                y = render_text_wrapped(page, block[1], MARGIN, y, CONTENT_WIDTH, FONT_BOLD, FONT_SIZE_H1)
                y += 8

            elif btype == "h2":
                ensure_space(35)
                y += 6
                y = render_text_wrapped(page, block[1], MARGIN, y, CONTENT_WIDTH, FONT_BOLD, FONT_SIZE_H2)
                y += 4

            elif btype == "h3":
                ensure_space(30)
                y += 4
                y = render_text_wrapped(page, block[1], MARGIN, y, CONTENT_WIDTH, FONT_BOLD, FONT_SIZE_H3)
                y += 2

            elif btype == "paragraph":
                ensure_space(30)
                y = render_rich_text_wrapped(page, block[1], MARGIN, y, CONTENT_WIDTH, FONT_SIZE_BODY)
                y += 4

            elif btype == "quote":
                ensure_space(30)
                text = strip_markdown_inline(block[1])
                # Draw quote bar
                page.draw_rect(
                    fitz.Rect(MARGIN, y - 2, MARGIN + 3, y + 14),
                    color=(0.6, 0.6, 0.6), fill=(0.6, 0.6, 0.6),
                )
                y = render_text_wrapped(
                    page, text, MARGIN + 12, y, CONTENT_WIDTH - 12,
                    FONT_BODY, FONT_SIZE_SMALL,
                )
                y += 4

            elif btype == "list_item":
                ensure_space(20)
                page.insert_text(
                    (MARGIN + 8, y), "\u2022",
                    fontname=FONT_BODY, fontsize=FONT_SIZE_BODY, color=(0, 0, 0),
                )
                y = render_rich_text_wrapped(
                    page, block[1], MARGIN + 22, y, CONTENT_WIDTH - 22, FONT_SIZE_BODY,
                )
                y += 2

            elif btype == "image":
                img_path = block[1]
                if not os.path.isfile(img_path):
                    print(f"  WARNING: image not found: {img_path}")
                    continue

                img = fitz.open(img_path)
                img_page = img[0]
                iw, ih = img_page.rect.width, img_page.rect.height

                # Scale to fit content width, max half page height
                max_img_height = (PAGE_HEIGHT - 2 * MARGIN) * 0.55
                scale = min(CONTENT_WIDTH / iw, max_img_height / ih, 1.0)
                draw_w = iw * scale
                draw_h = ih * scale

                ensure_space(draw_h + 10)

                # Center the image
                img_x = MARGIN + (CONTENT_WIDTH - draw_w) / 2
                rect = fitz.Rect(img_x, y, img_x + draw_w, y + draw_h)
                page.insert_image(rect, filename=img_path)
                y += draw_h + 10
                img.close()

    doc.save(OUTPUT_PDF)
    doc.close()
    print(f"\nGenerated: {OUTPUT_PDF} ({len(doc) if False else 'done'})")
    # Reopen to count pages
    check = fitz.open(OUTPUT_PDF)
    print(f"Pages: {len(check)}")
    check.close()


if __name__ == "__main__":
    generate_pdf()
