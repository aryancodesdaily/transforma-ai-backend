from pathlib import Path
import re
import html

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
)

from docx import Document
from docx.shared import Pt

from gemini_engine import generate_image_from_content


def clean_text(text: str) -> str:
    """
    Clean characters that may not render correctly
    in the default PDF font.
    """

    replacements = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2011": "-",   # non-breaking hyphen
        "\u2010": "-",   # hyphen
        "\u2212": "-",   # minus sign
        "\u00a0": " ",   # non-breaking space
        "\u2022": "-",   # bullet
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def markdown_to_reportlab(text: str) -> str:
    """
    Convert basic Markdown formatting into ReportLab-compatible HTML.
    """

    text = clean_text(text)
    text = html.escape(text)

    # Bold: **text** -> <b>text</b>
    text = re.sub(
        r"\*\*(.+?)\*\*",
        r"<b>\1</b>",
        text
    )

    # Italic: *text* -> <i>text</i>
    text = re.sub(
        r"(?<!\*)\*([^*]+?)\*(?!\*)",
        r"<i>\1</i>",
        text
    )

    return text


def generate_pdf(content: str, output_path: str):
    """
    Generate a formatted PDF from generated AI content.
    """

    document = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=50,
        leftMargin=50,
        topMargin=50,
        bottomMargin=50,
    )

    styles = getSampleStyleSheet()

    body_style = ParagraphStyle(
        "Body",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        alignment=TA_LEFT,
        spaceAfter=6,
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        spaceBefore=10,
        spaceAfter=7,
    )

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        spaceAfter=14,
    )

    story = []

    lines = content.splitlines()

    for line in lines:
        line = line.strip()

        if not line:
            story.append(Spacer(1, 5))
            continue

        # Remove Markdown heading markers
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)

            story.append(
                Paragraph(
                    markdown_to_reportlab(line),
                    heading_style
                )
            )
            continue

        # Bullet points
        if line.startswith("- "):
            bullet_text = line[2:].strip()

            story.append(
                ListFlowable(
                    [
                        ListItem(
                            Paragraph(
                                markdown_to_reportlab(bullet_text),
                                body_style
                            )
                        )
                    ],
                    bulletType="bullet",
                    leftIndent=18,
                )
            )
            continue

        # Numbered points
        numbered_match = re.match(
            r"^(\d+)\.\s+(.*)",
            line
        )

        if numbered_match:
            number = numbered_match.group(1)
            text = numbered_match.group(2)

            story.append(
                Paragraph(
                    f"<b>{number}.</b> "
                    f"{markdown_to_reportlab(text)}",
                    body_style
                )
            )
            continue

        # First non-empty line is treated as title
        if not story:
            story.append(
                Paragraph(
                    markdown_to_reportlab(line),
                    title_style
                )
            )
        else:
            story.append(
                Paragraph(
                    markdown_to_reportlab(line),
                    body_style
                )
            )

    document.build(story)


def generate_docx(content: str, output_path: str):
    """
    Generate a basic formatted DOCX from generated AI content.
    """

    document = Document()

    lines = content.splitlines()

    for line in lines:
        line = clean_text(line.strip())

        if not line:
            continue

        # Main heading
        if line.startswith("#"):
            heading = re.sub(r"^#+\s*", "", line)

            paragraph = document.add_paragraph()
            run = paragraph.add_run(
                heading.replace("**", "")
            )
            run.bold = True
            run.font.size = Pt(14)

            continue

        # Bullet point
        if line.startswith("- "):
            text = line[2:]

            paragraph = document.add_paragraph(
                style="List Bullet"
            )

            add_formatted_docx_text(
                paragraph,
                text
            )

            continue

        # Numbered point
        numbered_match = re.match(
            r"^(\d+)\.\s+(.*)",
            line
        )

        if numbered_match:
            text = numbered_match.group(2)

            paragraph = document.add_paragraph(
                style="List Number"
            )

            add_formatted_docx_text(
                paragraph,
                text
            )

            continue

        paragraph = document.add_paragraph()

        add_formatted_docx_text(
            paragraph,
            line
        )

    document.save(output_path)


def add_formatted_docx_text(paragraph, text: str):
    """
    Add basic Markdown bold formatting to a DOCX paragraph.
    """

    parts = re.split(
        r"(\*\*.*?\*\*)",
        text
    )

    for part in parts:

        if not part:
            continue

        if part.startswith("**") and part.endswith("**"):

            run = paragraph.add_run(
                part[2:-2]
            )

            run.bold = True

        else:

            paragraph.add_run(part)


def generate_output(
    content: str,
    output_format: str,
    output_path: str
):
    """
    Generate the requested output file.
    """

    output_format = output_format.upper()

    if output_format == "PDF":

        generate_pdf(
            content,
            output_path
        )

    elif output_format == "DOCX":

        generate_docx(
            content,
            output_path
        )

    elif output_format == "PNG":

        generate_image_from_content(
            content,
            output_path
        )

    else:

        raise ValueError(
            f"Unsupported output format: {output_format}"
        )