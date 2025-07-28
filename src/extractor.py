import fitz  # PyMuPDF
import re
import json
from pathlib import Path
from collections import Counter

# Load and compile expensive resources once at module load
with open("config.json", "r") as f:
    CONFIG = json.load(f)

HEADING_STRUCTURE_PATTERN = re.compile(CONFIG["HEADING_STRUCTURE_REGEX"])


def clean_text(text: str) -> str:
    """Removes redundant whitespace from a string."""
    return re.sub(r"\s+", " ", text).strip()


def get_style_key(span: dict) -> tuple:
    """Creates a unique, hashable key representing the visual style of a text span."""
    font_size = round(span["size"])
    font_name = span["font"].split("+")[-1].lower()
    is_bold = "bold" in font_name or (span["flags"] & 2**4)
    return (font_size, font_name, is_bold)


def _is_within_any_bbox(
    element_bbox: fitz.Rect, container_bboxes: list[fitz.Rect]
) -> bool:
    """Checks if an element's bounding box is inside any of the container bboxes."""
    for bbox in container_bboxes:
        if element_bbox in bbox:
            return True
    return False


def _is_potential_heading(line, block, body_size, config) -> tuple[bool, str, tuple]:
    """
    Applies a series of heuristic filters to a line of text to see if it's a heading.
    Returns:
        A tuple of (is_heading, cleaned_text, style_key).
    """
    if not line.get("spans"):
        return False, None, None

    # Reconstruct and clean text from all spans in the line
    line_text = clean_text(" ".join(s["text"] for s in line["spans"]))
    if not line_text:
        return False, None, None

    # All style decisions for the line are based on its first span
    style = get_style_key(line["spans"][0])
    font_size = style[0]

    # --- HEADING FILTERS ---
    # 1. Must be visually distinct: font size must be larger than the main body text.
    if font_size <= body_size:
        return False, None, None

    # 2. Must be concise: headings are typically in blocks with very few lines.
    if len(block.get("lines", [])) > 2:
        return False, None, None

    # 3. Must have a plausible length: word count must be within configured limits.
    word_count = len(line_text.split())
    if not (config["MIN_HEADING_WORDS"] <= word_count <= config["MAX_HEADING_WORDS"]):
        return False, None, None

    return True, line_text, style


def extract_from_layout(doc: fitz.Document):
    """
    Extracts an outline by performing multi-pass analysis on visual styles,
    filtering out tables and non-heading text structures.
    """
    # Pass 1: Profile document font sizes and detect all tables to create exclusion zones.
    font_size_counts = Counter()
    table_bboxes_by_page = [
        [table.bbox for table in page.find_tables()] for page in doc
    ]

    for page_num, page in enumerate(doc):
        # Process only text blocks outside of any detected table area
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") == 0 and not _is_within_any_bbox(
                fitz.Rect(block["bbox"]), table_bboxes_by_page[page_num]
            ):
                for line in block.get("lines", []):
                    if line.get("spans"):
                        size = round(line["spans"][0]["size"])
                        font_size_counts[size] += 1
    if not font_size_counts:
        return []

    body_size = font_size_counts.most_common(1)[0][0]

    # Pass 2: Identify potential headings using the heuristic helper function.
    potential_headings = []
    heading_styles = set()
    for page_num, page in enumerate(doc):
        for block in page.get_text("dict").get("blocks", []):
            # Skip non-text blocks and blocks inside tables
            if block.get("type") != 0 or _is_within_any_bbox(
                fitz.Rect(block["bbox"]), table_bboxes_by_page[page_num]
            ):
                continue
            for line in block.get("lines", []):
                is_heading, text, style = _is_potential_heading(
                    line, block, body_size, CONFIG
                )
                if is_heading:
                    potential_headings.append(
                        {
                            "text": text,
                            "style": style,
                            "page": page.number,
                            "y_pos": line["bbox"][1],
                        }
                    )
                    heading_styles.add(style)
    if not potential_headings:
        return []

    # Pass 3: Rank styles and build the final outline.
    ranked_styles = sorted(
        list(heading_styles), key=lambda s: (s[0], s[2]), reverse=True
    )
    style_to_level = {
        style: i + 1
        for i, style in enumerate(ranked_styles[: CONFIG["MAX_HEADING_LEVELS"]])
    }

    outline = []
    for h in potential_headings:
        if h["style"] in style_to_level:
            text = HEADING_STRUCTURE_PATTERN.sub("", h["text"]).strip()
            if text:
                outline.append(
                    {
                        "level": style_to_level[h["style"]],
                        "text": text,
                        "page": h["page"],
                        "y_pos": h["y_pos"],
                    }
                )

    if not outline:
        return []

    # Final post-processing and formatting
    outline.sort(key=lambda x: (x["page"], x["y_pos"]))
    for i in range(1, len(outline)):
        if outline[i]["level"] > outline[i - 1]["level"] + 1:
            outline[i]["level"] = outline[i - 1]["level"] + 1

    for item in outline:
        item["level"] = f"H{item['level']}"
        del item["y_pos"]

    return outline


def extract_outline_from_pdf(pdf_path: Path) -> dict:
    """
    Extracts a structured outline from a PDF using a hybrid strategy.
    It first attempts to use the embedded Table of Contents. If unavailable, it
    falls back to the advanced layout analysis engine.
    """
    with fitz.open(pdf_path) as doc:
        title = doc.metadata.get("title", "") or pdf_path.stem.replace("_", " ").title()

        toc = doc.get_toc()
        if toc:
            outline = [
                {
                    "level": f"H{min(level, CONFIG['MAX_HEADING_LEVELS'])}",
                    "text": clean_text(heading_text),
                    "page": page_num - 1,
                }
                for level, heading_text, page_num in toc
            ]
        else:
            outline = extract_from_layout(doc)

    return {"title": clean_text(title), "outline": outline}
