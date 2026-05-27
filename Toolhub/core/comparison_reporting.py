# -*- coding: utf-8 -*-
import os
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, KeepTogether
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
        'insert_bg': custom_colors.get('insert_bg', '#E8F5E9'), # Light Green
        'insert_fg': custom_colors.get('insert_fg', '#2E7D32'), # Dark Green
        'delete_bg': custom_colors.get('delete_bg', '#FFEBEE'), # Light Red
        'delete_fg': custom_colors.get('delete_fg', '#C62828'), # Dark Red
        'replace_bg': custom_colors.get('replace_bg', '#FFFDE7'), # Light Yellow
        'replace_fg': custom_colors.get('replace_fg', '#F57F17'), # Dark Yellow
        'intra_left_bg': custom_colors.get('intra_left_bg', '#e1f5fe'), # Blue-ish for intra
        'intra_left_fg': custom_colors.get('intra_left_fg', '#01579b'),
        'intra_right_bg': custom_colors.get('intra_right_bg', '#f3e5f5'), # Purple-ish
        'intra_right_fg': custom_colors.get('intra_right_fg', '#4a148c'),
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

# --- Functional (Section-Aware) Reporting ---

SECTION_BLUE  = colors.HexColor('#1565C0')
CLR_ADDED     = colors.HexColor('#E8F5E9')
CLR_DELETED   = colors.HexColor('#FFEBEE')
CLR_MODIFIED  = colors.HexColor('#FFFDE7')
CLR_OK        = colors.HexColor('#F1F8E9')
CLR_CHANGED   = colors.HexColor('#FFF3E0')
DARK_GREEN    = colors.HexColor('#2E7D32')
DARK_RED      = colors.HexColor('#C62828')
DARK_AMBER    = colors.HexColor('#E65100')

class FuncCompCanvas(canvas.Canvas):
    """Custom canvas for functional reports."""
    def __init__(self, *args, **kwargs):
        self.header_data  = kwargs.pop('header_data',  {})
        self.signatures   = kwargs.pop('signatures',   [])
        self.show_grid    = kwargs.pop('show_grid',    True)
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def _draw_header(self):
        self.saveState()
        w = self._pagesize[0]
        top = self._pagesize[1]
        self.setFont('Helvetica-Bold', 11)
        self.setFillColor(HITACHI_RED)
        self.drawCentredString(w / 2, top - 22, "Functional Logic Comparison Report")
        file_a = os.path.basename(self.header_data.get('path_a', 'File A'))
        file_b = os.path.basename(self.header_data.get('path_b', 'File B'))
        self.setFont('Helvetica-Bold', 8)
        self.setFillColor(colors.black)
        self.drawString(50, top - 36, f"Old: {file_a}  (CRC={self.header_data.get('crc_a','-')}, Checksum={self.header_data.get('checksum_a','-')})")
        self.drawString(50, top - 48, f"New: {file_b}  (CRC={self.header_data.get('crc_b','-')}, Checksum={self.header_data.get('checksum_b','-')})")
        self.setStrokeColor(colors.lightgrey)
        self.setLineWidth(0.5)
        self.line(50, top - 54, w - 50, top - 54)
        self.restoreState()

    def _draw_footer(self, page_count):
        self.saveState()
        footer_y = 25
        ts = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        self.setFont('Helvetica', 8)
        self.drawString(50, footer_y, f"Page {self._pageNumber} of {page_count} | Generated: {ts}")
        if self.signatures:
            num_sig = len(self.signatures); page_width = self._pagesize[0]; cw = (page_width - 100) / num_sig
            row_top, row_labels = [], []
            for sig in self.signatures:
                p = Paragraph(f"<b>{sig.get('name','')}</b>", ParagraphStyle('fn', fontSize=8, alignment=TA_CENTER))
                row_top.append(p); row_labels.append(sig.get('label', ''))
            t = Table([row_top, row_labels], colWidths=[cw] * num_sig, rowHeights=[28, 18])
            t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 0.5, colors.black), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTSIZE', (0,0), (-1,-1), 8), ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'), ('BACKGROUND', (0,1), (-1,1), colors.whitesmoke)]))
            t.wrapOn(self, 50, footer_y + 15); t.drawOn(self, 50, footer_y + 15)
        self.restoreState()

    def save(self):
        n = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state); self._draw_header(); self._draw_footer(n); canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

def generate_functional_report(out_path, header_data, section_diffs, signatures, options=None):
    if options is None: options = {}
    show_grid = options.get('show_grid', True)
    custom_c = options.get('colors', {})
    context_lines = options.get('context_lines', 10)
    c_map = {
        'delete_bg': custom_c.get('delete_bg', '#E8F5E9'), 'delete_fg': custom_c.get('delete_fg', '#2E7D32'),
        'insert_bg': custom_c.get('insert_bg', '#FFEBEE'), 'insert_fg': custom_c.get('insert_fg', '#C62828'),
        'replace_bg': custom_c.get('replace_bg', '#FFFDE7'), 'replace_fg': custom_c.get('replace_fg', '#E65100'),
        'intra_left_bg': custom_c.get('intra_left_bg', '#C8E6C9'), 'intra_left_fg': custom_c.get('intra_left_fg', '#1B5E20'),
        'intra_right_bg': custom_c.get('intra_right_bg', '#FFCDD2'), 'intra_right_fg': custom_c.get('intra_right_fg', '#B71C1C'),
    }
    doc = SimpleDocTemplate(out_path, pagesize=landscape(letter), leftMargin=0.5*inch, rightMargin=0.5*inch, topMargin=0.85*inch, bottomMargin=1.5*inch)
    styles = getSampleStyleSheet()
    code_style = ParagraphStyle('Code', parent=styles['Normal'], fontName='Courier', fontSize=8, leading=10)
    sec_hdr_style = ParagraphStyle('SecHdr', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.white, alignment=TA_CENTER)
    title_style = ParagraphStyle('Title', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, textColor=HITACHI_RED, alignment=TA_CENTER)
    note_style = ParagraphStyle('Note', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.grey, alignment=TA_CENTER)
    story = []
    page_w = landscape(letter)[0] - inch
    story.append(Spacer(1, 0.1*inch)); story.append(Paragraph("Section-Wise Change Summary", title_style)); story.append(Spacer(1, 0.08*inch))
    file_a = os.path.basename(header_data.get('path_a', 'Old File')); file_b = os.path.basename(header_data.get('path_b', 'New File'))
    story.append(Paragraph(f"Comparing: <b>{file_a}</b> &rarr; <b>{file_b}</b>", note_style)); story.append(Spacer(1, 0.15*inch))
    sum_rows = [[Paragraph('<b>#</b>', code_style), Paragraph('<b>Section</b>', code_style), Paragraph('<b>Status</b>', code_style), Paragraph('<b>Added</b>', code_style), Paragraph('<b>Deleted</b>', code_style), Paragraph('<b>Modified</b>', code_style), Paragraph('<b>Unchanged</b>', code_style)]]
    sum_styles = [('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEEEEE')), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]
    if show_grid: sum_styles.insert(0, ('GRID', (0,0), (-1,-1), 0.4, colors.grey))
    else: sum_styles.insert(0, ('LINEBELOW', (0,0), (-1,0), 1, colors.black))
    total_added = total_deleted = total_modified = 0
    for i, sd in enumerate(section_diffs, start=1):
        if not sd.text_a and not sd.text_b: status_txt, bg = '⬛ Not Present', colors.whitesmoke
        elif sd.has_changes: status_txt, bg = '⚠ Changed', colors.HexColor('#FFF8E1')
        else: status_txt, bg = '✅ No Changes', colors.HexColor('#F1F8E9')
        total_added += sd.added; total_deleted += sd.deleted; total_modified += sd.modified
        sum_rows.append([str(i), sd.name, status_txt, str(sd.added) if sd.has_changes else '—', str(sd.deleted) if sd.has_changes else '—', str(sd.modified) if sd.has_changes else '—', str(sd.unchanged)])
        sum_styles.append(('BACKGROUND', (0, i), (-1, i), bg))
    sum_rows.append(['', 'TOTAL', '', str(total_added), str(total_deleted), str(total_modified), ''])
    sum_styles.append(('BACKGROUND', (0, len(sum_rows)-1), (-1, len(sum_rows)-1), colors.HexColor('#EEEEEE')))
    sum_styles.append(('FONTNAME', (0, len(sum_rows)-1), (-1, len(sum_rows)-1), 'Helvetica-Bold'))
    sum_table = Table(sum_rows, colWidths=[30, page_w*0.32, page_w*0.14, page_w*0.10, page_w*0.10, page_w*0.10, page_w*0.12])
    sum_table.setStyle(TableStyle(sum_styles)); story.append(sum_table)
    changed_sections = [sd for sd in section_diffs if sd.has_changes]
    if not changed_sections:
        story.append(Spacer(1, 0.3*inch)); story.append(Paragraph("✅ No functional differences found.", ParagraphStyle('ok', parent=styles['Normal'], fontSize=12, textColor=DARK_GREEN, alignment=TA_CENTER)))
    else:
        for sd in changed_sections:
            story.append(Spacer(1, 0.25*inch)); story.append(HRFlowable(width='100%', thickness=1, color=SECTION_BLUE)); story.append(Spacer(1, 0.06*inch))
            hdr_table = Table([[Paragraph(f"SECTION: {sd.name.upper()}", sec_hdr_style)]], colWidths=[page_w])
            hdr_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), SECTION_BLUE), ('TOPPADDING', (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6)]))
            story.append(KeepTogether([hdr_table])); story.append(Spacer(1, 0.08*inch))
            summary_txt = f"Changes: <b><font color='#C62828'>+{sd.added} added</font></b>  <b><font color='#2E7D32'>−{sd.deleted} deleted</font></b>  <b><font color='#E65100'>~{sd.modified} modified</font></b>"
            story.append(Paragraph(summary_txt, ParagraphStyle('sum', parent=styles['Normal'], fontSize=9, alignment=TA_LEFT))); story.append(Spacer(1, 0.06*inch))
            diff_data = sd.changes; include = set()
            for j, (tag, _, _) in enumerate(diff_data):
                if tag != 'equal':
                    for k in range(max(0, j-context_lines), min(len(diff_data), j+context_lines+1)): include.add(k)
            text_col_w = (page_w - 50) / 2
            diff_rows = [[Paragraph('<b>#</b>', code_style), Paragraph(f'<b>{file_a} (Old)</b>', code_style), Paragraph(f'<b>{file_b} (New)</b>', code_style)]]
            diff_styles = [('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EEEEEE')), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('ALIGN', (0,0), (0,-1), 'CENTER')]
            if show_grid: diff_styles.insert(0, ('GRID', (0,0), (-1,-1), 0.25, colors.grey))
            else: diff_styles.insert(0, ('LINEBELOW', (0,0), (-1,0), 1, colors.black))
            curr_r = 1; last_j = -1
            def _to_h(content, fg, is_l=False):
                if not isinstance(content, list): return f'<font color="{fg}">{str(content).replace("<","&lt;").replace(">","&gt;")}</font>' if fg else str(content).replace("<","&lt;").replace(">","&gt;")
                parts = []
                for p in content:
                    if isinstance(p, tuple) and p[0] == 'changed':
                        px = 'intra_left' if is_l else 'intra_right'
                        parts.append(f'<font backColor="{c_map[px+"_bg"]}" color="{c_map[px+"_fg"]}">{p[1].replace("<","&lt;").replace(">","&gt;")}</font>')
                    else: parts.append(f'<font color="{fg}">{str(p).replace("<","&lt;").replace(">","&gt;")}</font>' if fg else str(p).replace("<","&lt;").replace(">","&gt;"))
                return ''.join(parts)
            for j, (tag, ta, tb) in enumerate(diff_data):
                if j not in include: continue
                if last_j != -1 and j > last_j + 1:
                    diff_rows.append(['…', '…', '…']); diff_styles.append(('BACKGROUND', (0, curr_r), (-1, curr_r), colors.whitesmoke)); curr_r += 1
                bgx = colors.HexColor(c_map[tag+'_bg']) if tag != 'equal' else None
                fgx = c_map.get(tag+'_fg') if tag != 'equal' else None
                if bgx: diff_styles.append(('BACKGROUND', (0, curr_r), (-1, curr_r), bgx))
                diff_rows.append([str(j+1), Paragraph(_to_h(ta, fgx, True), code_style), Paragraph(_to_h(tb, fgx, False), code_style)])
                curr_r += 1; last_j = j
            diff_table = Table(diff_rows, colWidths=[50, text_col_w, text_col_w], repeatRows=1); diff_table.setStyle(TableStyle(diff_styles)); story.append(diff_table)
    doc.build(story, canvasmaker=lambda *a, **kw: FuncCompCanvas(*a, header_data=header_data, signatures=signatures, show_grid=show_grid, **kw))
    return out_path
