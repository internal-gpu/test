import io
from docx import Document
from docx.shared import RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from a DOCX file."""
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = []
    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text)
    # Also extract text from tables
    for table in doc.tables:
        for row in table.rows:
            row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_texts:
                paragraphs.append(" | ".join(row_texts))
    return "\n".join(paragraphs)


def create_reviewed_docx(file_bytes: bytes, review_items: list[dict]) -> bytes:
    """Create a copy of the DOCX with review comments shown as inline annotations.

    For each review item, find the original text in the document and add
    a strikethrough + red replacement inline to simulate 'track changes' visually.
    """
    doc = Document(io.BytesIO(file_bytes))

    # Build a lookup of original_text -> review item
    reviews_by_text = {}
    for item in review_items:
        orig = item.get("original_text", "").strip()
        if orig:
            reviews_by_text[orig] = item

    for para in doc.paragraphs:
        para_text = para.text
        for orig_text, item in list(reviews_by_text.items()):
            if orig_text in para_text:
                # Clear existing runs and rebuild with annotations
                suggested = item.get("suggested_text", "")
                reason = item.get("reason", "")
                severity = item.get("severity", "warning")

                # Find the position
                idx = para_text.find(orig_text)
                before = para_text[:idx]
                after = para_text[idx + len(orig_text):]

                # Clear paragraph
                for run in para.runs:
                    run.text = ""
                if para.runs:
                    para.runs[0].text = before

                # Add strikethrough original (red)
                run_del = para.add_run(orig_text)
                run_del.font.strike = True
                run_del.font.color.rgb = RGBColor(200, 50, 50)

                # Add suggested text (green, bold)
                run_add = para.add_run(f" → {suggested}")
                run_add.font.color.rgb = RGBColor(0, 140, 60)
                run_add.font.bold = True

                # Add reason as small note
                severity_label = {"critical": "⚠️必须修改", "warning": "⚡建议修改", "info": "💡可选优化"}
                label = severity_label.get(severity, "")
                run_note = para.add_run(f"  [{label}: {reason}]")
                run_note.font.color.rgb = RGBColor(120, 120, 120)
                run_note.font.size = run_note.font.size  # keep same size

                # Add remaining text
                if after:
                    run_after = para.add_run(after)

                # Remove from lookup so we don't double-match
                del reviews_by_text[orig_text]
                break

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
