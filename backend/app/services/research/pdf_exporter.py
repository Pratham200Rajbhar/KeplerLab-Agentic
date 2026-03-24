import os
import time
import logging
import re
import uuid
from datetime import datetime, timedelta
from fpdf import FPDF
import markdown_it
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

# Brand Colors
CLR_ACCENT = (26, 115, 232)  # Kepler Blue
CLR_TITLE = (15, 23, 42)    # Slate 900
CLR_HEADER = (30, 41, 59)   # Slate 800
CLR_BODY = (51, 65, 85)     # Slate 700
CLR_MUTED = (100, 116, 139) # Slate 500
CLR_BG_CALLOUT = (248, 250, 252) # Slate 50
CLR_BORDER = (226, 232, 240)    # Slate 200

class ResearchPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        
        self.set_font("DejaVu", "B", 9)
        self.set_text_color(*CLR_MUTED)
        self.cell(0, 10, "KeplerLab Intelligence Report", 0, 0, "L")
        
        self.set_font("DejaVu", "I", 8)
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d')}", 0, 0, "R")
        self.ln(12)
        
        # Subtle divider
        self.set_draw_color(*CLR_BORDER)
        self.set_line_width(0.1)
        self.line(10, 20, 200, 20)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", "I", 8)
        self.set_text_color(*CLR_MUTED)
        self.cell(0, 10, f"Confidential Intelligence | Page {self.page_no()}/{{nb}}", 0, 0, "C")

    # --- Component Renderers ---
    def render_h1(self, text):
        text = text.replace('**', '').replace('*', '')
        self.ln(6)
        self.set_font("DejaVu", "B", 18)
        self.set_text_color(*CLR_TITLE)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 10, text)
        self.set_draw_color(*CLR_ACCENT)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y()+2, self.get_x()+30, self.get_y()+2)
        self.ln(6)

    def render_h2(self, text):
        text = text.replace('**', '').replace('*', '')
        self.ln(4)
        self.set_font("DejaVu", "B", 14)
        self.set_text_color(*CLR_HEADER)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 8, text)
        self.ln(2)

    def render_h3(self, text):
        text = text.replace('**', '').replace('*', '')
        self.ln(2)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*CLR_ACCENT)
        w = self.w - self.l_margin - self.r_margin
        self.multi_cell(w, 7, text)
        self.ln(1)

    def render_paragraph(self, text):
        self.set_font("DejaVu", "", 10.5)
        self.set_text_color(*CLR_BODY)
        # Handle simple bold parsing
        parts = re.split(r'(\*\*.*?\*\*)', text)
        for part in parts:
            if part.startswith('**') and part.endswith('**'):
                self.set_font("DejaVu", "B", 10.5)
                self.write(6, part[2:-2].replace('*', ''))
                self.set_font("DejaVu", "", 10.5)
            else:
                self.write(6, part.replace('*', ''))
        self.ln(8)

    def render_bullet(self, text):
        self.set_x(15)
        self.set_font("DejaVu", "B", 10.5)
        self.set_text_color(*CLR_ACCENT)
        self.write(6, "• ")
        self.set_x(20)
        self.render_paragraph(text)

    def render_callout(self, title, content_lines):
        title = title.replace('**', '').replace('*', '')
        self.set_fill_color(*CLR_BG_CALLOUT)
        self.set_draw_color(*CLR_ACCENT)
        self.set_line_width(0.3)
        
        # Calculate height roughly
        h = 10 + (len(content_lines) * 6) + 6
        self.rect(10, self.get_y(), 190, h, style="FD")
        
        self.set_y(self.get_y() + 4)
        self.set_x(15)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*CLR_ACCENT)
        self.cell(0, 6, title.upper(), 0, 1)
        
        for line in content_lines:
            self.set_x(15)
            self.render_paragraph(line)
        self.ln(4)

    def render_table(self, markdown_table):
        lines = markdown_table.strip().split('\n')
        if len(lines) < 2: return
        
        # Parse data
        data = []
        for line in lines:
            if '|' in line and not re.match(r'^[\s|:-]+$', line):
                cols = [c.strip() for c in line.split('|') if c.strip()]
                data.append(cols)
        
        if not data: return
        
        self.ln(4)
        with self.table(
            borders_layout="HORIZONTAL_LINES",
            cell_fill_color=CLR_BG_CALLOUT,
            cell_fill_mode="ROWS",
            line_height=7,
            text_align="LEFT",
            width=190,
        ) as table:
            for row_idx, row_data in enumerate(data):
                row = table.row()
                if row_idx == 0:
                    self.set_font("DejaVu", "B", 9)
                    self.set_text_color(*CLR_TITLE)
                else:
                    self.set_font("DejaVu", "", 9)
                    self.set_text_color(*CLR_BODY)
                
                for cell in row_data:
                    row.cell(cell)
        self.ln(6)

async def generate_research_pdf(
    report_md: str, 
    query: str, 
    sources_count: int,
    user_id: str,
    notebook_id: str = None
) -> dict:
    """
    Converts a Markdown research report into a professional PDF and registers it as an artifact.
    Returns info about the generated artifact.
    """
    try:
        pdf = ResearchPDF()
        
        # --- Add Unicode Fonts ---
        font_dir = "/usr/share/fonts/truetype/dejavu"
        pdf.add_font("DejaVu", "", os.path.join(font_dir, "DejaVuSans.ttf"))
        pdf.add_font("DejaVu", "B", os.path.join(font_dir, "DejaVuSans-Bold.ttf"))
        pdf.add_font("DejaVu", "I", os.path.join(font_dir, "DejaVuSans-Oblique.ttf"))
        pdf.add_font("DejaVu", "BI", os.path.join(font_dir, "DejaVuSans-BoldOblique.ttf"))
        
        # --- Cover Page ---
        pdf.add_page()
        pdf.ln(40)
        
        # Brand Accent Line
        pdf.set_draw_color(*CLR_ACCENT)
        pdf.set_line_width(2)
        pdf.line(10, 50, 40, 50)
        pdf.ln(10)
        
        pdf.set_font("DejaVu", "B", 34)
        pdf.set_text_color(*CLR_TITLE)
        pdf.multi_cell(0, 14, query.title())
        pdf.ln(6)
        
        pdf.set_font("DejaVu", "", 14)
        pdf.set_text_color(*CLR_MUTED)
        pdf.multi_cell(0, 8, "Deep Research Intelligence Dossier")
        pdf.ln(30)
        
        # Meta Info Box
        pdf.set_fill_color(*CLR_BG_CALLOUT)
        pdf.rect(10, pdf.get_y(), 190, 24, style="F")
        pdf.set_y(pdf.get_y() + 6)
        pdf.set_x(15)
        pdf.set_font("DejaVu", "B", 10)
        pdf.set_text_color(*CLR_ACCENT)
        pdf.cell(50, 12, "DATE", 0, 0)
        pdf.cell(50, 12, "SOURCES", 0, 0)
        pdf.cell(50, 12, "CONFIDENTIALITY", 0, 1)
        
        pdf.set_x(15)
        pdf.set_font("DejaVu", "", 10)
        pdf.set_text_color(*CLR_HEADER)
        pdf.cell(50, 4, datetime.now().strftime("%B %d, %Y"), 0, 0)
        pdf.cell(50, 4, f"{sources_count} Verified Sources", 0, 0)
        pdf.cell(50, 4, "Internal Use Only", 0, 1)
        
        # --- Content Page ---
        pdf.add_page()
        
        # Advanced Markdown Parser (Custom)
        import re
        lines = report_md.split('\n')
        content_buffer = []
        in_callout = False
        callout_title = ""
        in_table = False
        table_buffer = []

        for i, line in enumerate(lines):
            line = line.strip()
            
            # Detect tables
            if '|' in line:
                in_table = True
                table_buffer.append(line)
                continue
            elif in_table:
                pdf.render_table('\n'.join(table_buffer))
                table_buffer = []
                in_table = False

            # Detect Callouts (Executive Summary etc)
            if i < len(lines)-1 and (lines[i+1].startswith('====') or line.startswith('# Executive Summary')):
                if in_callout: # Close existing callout if any
                    pdf.render_callout(callout_title, content_buffer)
                    content_buffer = []
                in_callout = True
                callout_title = "Executive Summary"
                continue
            
            if in_callout:
                if line.startswith('##') or line.startswith('1.'):
                    pdf.render_callout(callout_title, content_buffer)
                    content_buffer = []
                    in_callout = False
                else:
                    if line: content_buffer.append(line)
                    continue

            # Standards Elements
            if line.startswith('### '):
                pdf.render_h3(line[4:].strip())
            elif line.startswith('## '):
                pdf.render_h2(line[3:].strip())
            elif line.startswith('# '):
                pdf.render_h1(line[2:].strip())
            elif line.startswith('- ') or line.startswith('* '):
                pdf.render_bullet(line[2:].strip())
            elif line.startswith('1. ') or line.startswith('2. '):
                pdf.render_bullet(line[3:].strip())
            elif line:
                pdf.render_paragraph(line)
        
        # --- Export Path ---
        export_dir = "/disk1/KeplerLab_Agentic/backend/data/exports"
        os.makedirs(export_dir, exist_ok=True)
        
        filename = f"Kepler_Research_{int(time.time())}.pdf"
        filepath = os.path.join(export_dir, filename)
        pdf.output(filepath)
        size_bytes = os.path.getsize(filepath)
        
        # --- Register Artifact ---
        artifact_id = str(uuid.uuid4())
        download_token = uuid.uuid4().hex
        
        artifact = await prisma.artifact.create(data={
            "id": artifact_id,
            "userId": user_id,
            "notebookId": notebook_id,
            "filename": filename,
            "mimeType": "application/pdf",
            "displayType": "research_report",
            "sizeBytes": size_bytes,
            "downloadToken": download_token,
            "tokenExpiry": datetime.now() + timedelta(days=7),
            "workspacePath": filepath,
        })
        
        logger.info(f"Generated research PDF artifact: {artifact_id} at {filepath}")
        return {
            "id": artifact_id,
            "filename": filename,
            "mime": "application/pdf",
            "size": size_bytes,
            "url": f"/api/artifacts/{artifact_id}",
            "display_type": "research_report"
        }


    except Exception as e:
        logger.error(f"Failed to generate/register PDF: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return {}

