# -*- coding: utf-8 -*-
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Hitachi Branding constants
REPORT_NAME = "Comparison Report"
HITACHI_RED = colors.HexColor('#E60027')

class ComparisonCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.header_data = kwargs.pop('header_data', {})
        self.signatures = kwargs.pop('signatures', [])
        self.show_grid = kwargs.pop('show_grid', True)
        # Global sig_image removed
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def draw_header(self):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.black)
        
        file_a = os.path.basename(self.header_data.get('path_a', 'File A'))
        file_b = os.path.basename(self.header_data.get('path_b', 'File B'))
        
        info_a = f"Old: {file_a} (CRC={self.header_data.get('crc_a', '—')}, Checksum={self.header_data.get('checksum_a', '—')})"
        info_b = f"New: {file_b} (CRC={self.header_data.get('crc_b', '—')}, Checksum={self.header_data.get('checksum_b', '—')})"
        
        self.setFont('Helvetica-Bold', 11)
        self.setFillColor(HITACHI_RED)
        self.drawCentredString(self._pagesize[0]/2, self._pagesize[1] - 25, REPORT_NAME)

        self.setFont('Helvetica-Bold', 9)
        self.setFillColor(colors.black)
        self.drawString(50, self._pagesize[1] - 35, info_a)
        self.drawString(50, self._pagesize[1] - 48, info_b)
        
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(50, self._pagesize[1] - 55, self._pagesize[0] - 50, self._pagesize[1] - 55)
        self.restoreState()

    def draw_footer(self, page_count):
        self.saveState()
        footer_y = 25
        
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.black)
        timestamp = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        # String will be drawn lower than the table
        self.drawString(50, footer_y, f"Page {self._pageNumber} of {page_count} | Generated: {timestamp}")

        if self.signatures:
            # We want rows: [Name + Image], [Designation]
            row_top = []
            row_labels = []
            
            num_sig = len(self.signatures)
            page_width = self._pagesize[0]
            cw = (page_width - 100) / num_sig
            
            for sig in self.signatures:
                name = sig.get('name', '')
                img_path = sig.get('img', '')
                
                # Create a sub-table for Name and Image side-by-side
                # Col widths: 70% name, 30% image (adjustable)
                sub_cw = [cw * 0.65, cw * 0.35]
                
                # Image flowable
                i_flow = ""
                if img_path and os.path.exists(img_path):
                    try:
                        i = Image(img_path)
                        i._restrictSize(sub_cw[1] - 5, 25) # Short image
                        i_flow = i
                    except: pass
                
                p_name = Paragraph(f"<b>{name}</b>", ParagraphStyle('footer_name', fontSize=8, alignment=TA_CENTER))
                
                sub_table = Table([[p_name, i_flow]], colWidths=sub_cw, rowHeights=[30])
                sub_table.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (0,0), 'CENTER'),
                    ('ALIGN', (1,0), (1,0), 'CENTER'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
                
                row_top.append(sub_table)
                row_labels.append(sig.get('label', ''))
            
            table_data = [row_top, row_labels]
            sig_table = Table(table_data, colWidths=[cw]*num_sig, rowHeights=[30, 20])
            
            grid_style = ('GRID', (0,0), (-1,-1), 0.5, colors.black)
            
            sig_table.setStyle(TableStyle([
                grid_style,
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
                ('BACKGROUND', (0,1), (-1,1), colors.whitesmoke),
                ('LEFTPADDING', (0,0), (-1,0), 2),
                ('RIGHTPADDING', (0,0), (-1,0), 2),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ]))
            
            sig_table.wrapOn(self, 50, footer_y + 15)
            sig_table.drawOn(self, 50, footer_y + 15)
        self.restoreState()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header()
            self.draw_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def generate_comparison_report(out_path, header_data, diff_data, signatures, options=None):
    if options is None: options = {}
    changed_only = options.get('changed_only', False)
    custom_colors = options.get('colors', {})
    show_grid = options.get('show_grid', True)
    
    # Use hex strings directly for HTML fonts
    c_map_hex = {
        'insert_bg': custom_colors.get('insert_bg', '#FFEBEE'),
        'insert_fg': custom_colors.get('insert_fg', '#C62828'),
        'delete_bg': custom_colors.get('delete_bg', '#E8F5E9'),
        'delete_fg': custom_colors.get('delete_fg', '#2E7D32'),
        'replace_bg': custom_colors.get('replace_bg', '#FFFF00'),
        'replace_fg': custom_colors.get('replace_fg', '#000000'),
        'intra_left_bg': custom_colors.get('intra_left_bg', '#00FF00'),
        'intra_left_fg': custom_colors.get('intra_left_fg', '#000000'),
        'intra_right_bg': custom_colors.get('intra_right_bg', '#FF3333'),
        'intra_right_fg': custom_colors.get('intra_right_fg', '#000000'),
    }

    doc = SimpleDocTemplate(
        out_path, pagesize=landscape(letter),
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.8*inch, bottomMargin=1.5*inch
    )
    
    styles = getSampleStyleSheet()
    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=10,
        whitespace='normal'
    )
    
    file_a = os.path.basename(header_data.get('path_a', 'Old File'))
    file_b = os.path.basename(header_data.get('path_b', 'New File'))
    
    story = []
    # Dynamic Headers
    table_rows = [["#", f"{file_a} (Old or Existing file)", f"{file_b} (New or Revised file)"]]
    row_styles = []

    context_lines = options.get('context_lines', 10)
    
    # Determine which lines to include
    include_indices = set()
    if changed_only:
        for i, (tag, _, _) in enumerate(diff_data):
            if tag != 'equal':
                start = max(0, i - context_lines)
                end = min(len(diff_data), i + context_lines + 1)
                for j in range(start, end):
                    include_indices.add(j)
    else:
        include_indices = set(range(len(diff_data)))

    def _line_to_html(content, fg_color, is_left=False):
        if not isinstance(content, list):
            safe = str(content).replace('<', '&lt;').replace('>', '&gt;')
            return f'<font color="{fg_color}">{safe}</font>' if fg_color else safe
        
        html_parts = []
        for part in content:
            if isinstance(part, tuple) and part[0] == 'changed':
                safe_p = part[1].replace('<', '&lt;').replace('>', '&gt;')
                
                key_prefix = 'intra_left' if is_left else 'intra_right'
                highlight = c_map_hex.get(f'{key_prefix}_bg')
                txt_c = c_map_hex.get(f'{key_prefix}_fg')
                
                html_parts.append(f'<font backColor="{highlight}" color="{txt_c}">{safe_p}</font>')
            else:
                safe_p = str(part).replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f'<font color="{fg_color}">{safe_p}</font>' if fg_color else safe_p)
        return "".join(html_parts)

    current_row = 1
    last_idx = -1
    
    for i, (tag, text_a, text_b) in enumerate(diff_data):
        if i not in include_indices:
            continue
            
        # Add a separator if there's a gap
        if last_idx != -1 and i > last_idx + 1:
            table_rows.append(["...", "...", "..."])
            row_styles.append(('BACKGROUND', (0, current_row), (-1, current_row), colors.whitesmoke))
            row_styles.append(('TEXTCOLOR', (0, current_row), (-1, current_row), colors.grey))
            current_row += 1

        line_num = i + 1
        fg = c_map_hex.get(f"{tag}_fg") if tag != 'equal' else None
        bg = colors.HexColor(c_map_hex.get(f"{tag}_bg")) if tag != 'equal' else None
        
        content_a = _line_to_html(text_a, fg, is_left=True)
        content_b = _line_to_html(text_b, fg, is_left=False)
        
        if bg:
            row_styles.append(('BACKGROUND', (0, current_row), (-1, current_row), bg))
            
        p_a = Paragraph(content_a, code_style)
        p_b = Paragraph(content_b, code_style)
        
        table_rows.append([str(line_num), p_a, p_b])
        current_row += 1
        last_idx = i

    if len(table_rows) == 1:
        table_rows.append(["-", "No differences found or all pages filtered out.", ""])

    t_width = landscape(letter)[0] - inch
    base_style = [
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEEEEE')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (0,0), (0,-1), 'CENTER'),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]
    
    text_col_w = (t_width - 50) / 2
    diff_table = Table(table_rows, colWidths=[50, text_col_w, text_col_w], repeatRows=1)
    
    if show_grid:
        base_style.insert(0, ('GRID', (0,0), (-1,-1), 0.25, colors.grey))
    else:
        base_style.insert(0, ('LINEBELOW', (0,0), (-1,0), 1, colors.black))

    base_style.extend(row_styles)
    diff_table.setStyle(TableStyle(base_style))
    story.append(diff_table)
    
    canvas_args = {'header_data': header_data, 'signatures': signatures, 'show_grid': show_grid}
    doc.build(story, canvasmaker=lambda *args, **kwargs: ComparisonCanvas(*args, **canvas_args, **kwargs))
    return out_path
