import os
import unicodedata
from fpdf import FPDF, XPos, YPos

class KeplerPDF(FPDF):
    """
    A robust wrapper around FPDF2 for KeplerLab agents.
    Handles Unicode sanitization, font loading, and layout safety automatically.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_fonts()
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()
        self.set_font("DejaVu", size=11)

    def _setup_fonts(self):
        # Look for the font in the current working directory (copied by artifact_executor)
        font_path = "DejaVuSans.ttf"
        if os.path.exists(font_path):
            try:
                self.add_font("DejaVu", "", font_path)
                self.add_font("DejaVu", "B", font_path.replace(".ttf", "-Bold.ttf") if os.path.exists(font_path.replace(".ttf", "-Bold.ttf")) else font_path)
            except Exception:
                pass # Fallback to core fonts if DejaVu fails
        else:
            self.set_font("Helvetica", size=11)

    def sanitize(self, text):
        if not isinstance(text, str):
            text = str(text)
        # Normalize and translate to latin-1 compatible chars if possible, 
        # but keep it readable. fpdf2 handles unicode better now, but 
        # this ensures maximum compatibility with DejaVu/Latin-1.
        return unicodedata.normalize('NFKD', text).encode('latin-1', 'replace').decode('latin-1')

    def _ensure_page(self):
        if self.page == 0:
            self.add_page()

    def cell(self, w=0, h=0, text="", border=0, ln=0, align="L", fill=False, link="", **kwargs):
        self._ensure_page()
        # Support modern new_x/new_y if ln is used
        if ln == 1:
            kwargs['new_x'] = XPos.LMARGIN
            kwargs['new_y'] = YPos.NEXT
        elif ln == 2:
            kwargs['new_x'] = XPos.RIGHT
            kwargs['new_y'] = YPos.NEXT
            
        return super().cell(w=w, h=h, text=self.sanitize(text), border=border, align=align, fill=fill, link=link, **kwargs)

    def multi_cell(self, w=0, h=0, text="", border=0, align="L", fill=False, **kwargs):
        self._ensure_page()
        # Safety: if w=0 and we are too close to the right margin, move to next line first
        if w == 0 or w == self.epw:
            if self.get_x() > (self.w - self.r_margin - 0.1):
                self.ln()
            w = self.epw
            
        # Ensure we don't crash with "not enough space"
        # If current x is near the edge, reset to left margin
        if self.get_x() > (self.w - self.r_margin - 1):
            self.set_x(self.l_margin)
            
        return super().multi_cell(w=w, h=h, text=self.sanitize(text), border=border, align=align, fill=fill, **kwargs)

    def add_section(self, title, level=1):
        self._ensure_page()
        if level == 1:
            self.ln(10)
            self.set_font("DejaVu", "B", 16)
            self.multi_cell(0, 10, title)
            self.ln(5)
        elif level == 2:
            self.ln(5)
            self.set_font("DejaVu", "B", 13)
            self.multi_cell(0, 8, title)
            self.ln(2)
        self.set_font("DejaVu", "", 11)

    def add_paragraph(self, text):
        self._ensure_page()
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 6, text)
        self.ln(4)

    def add_bullet(self, text):
        self._ensure_page()
        old_x = self.get_x()
        self.set_x(old_x + 5)
        self.write(6, self.sanitize("• "))
        self.multi_cell(0, 6, text)
        self.set_x(old_x)
        self.ln(2)

    def add_table(self, data, headers=None):
        """
        Adds a robust table. data is a list of lists.
        """
        if not data: return
        self._ensure_page()
        self.ln(5)
        with self.table(
            borders_layout="HORIZONTAL_LINES",
            line_height=7,
            text_align="LEFT",
            width=self.epw,
        ) as table:
            if headers:
                row = table.row()
                self.set_font("DejaVu", "B", 10)
                for h in headers:
                    row.cell(self.sanitize(h))
            
            self.set_font("DejaVu", "", 10)
            for row_data in data:
                row = table.row()
                for cell in row_data:
                    row.cell(self.sanitize(cell))
        self.ln(5)

# Simple alias for convenience
PDF = KeplerPDF
