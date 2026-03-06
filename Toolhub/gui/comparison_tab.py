# -*- coding: utf-8 -*-
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QFileDialog, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QMessageBox,
    QApplication, QRadioButton, QButtonGroup, QColorDialog, QCheckBox,
    QSpinBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QFont, QColor

from core.text_compare import get_mll_data, compare_texts
from core.comparison_reporting import generate_comparison_report

class ComparisonTab(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setWindowTitle("Application Logic Comparison Tool")
        self.resize(1100, 850)
        
        # Default Colors (Updated: Insert=Red, Delete=Green, Replace=Yellow/Black)
        self.colors = {
            'insert_bg': '#FFEBEE', 'insert_fg': '#C62828', # Red for Insertion
            'delete_bg': '#E8F5E9', 'delete_fg': '#2E7D32', # Green for Removal
            'replace_bg': '#FFFF00', 'replace_fg': '#000000', # Yellow BG, Black FG for Replaced
            'intra_left_bg': '#00FF00', 'intra_left_fg': '#000000', # intra-line removal
            'intra_right_bg': '#ff6759', 'intra_right_fg': '#000000' # intra-line addition
        }
        
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header
        header = QLabel("📄 Application Logic Comparison Tool")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #E60027; margin-bottom: 5px;")
        main_layout.addWidget(header)

        # Splitter to separate config and results
        self.splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.splitter)

        # --- Top Section: Configuration ---
        config_container = QWidget()
        config_h_layout = QHBoxLayout(config_container)
        config_h_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left side: File & Signatures
        left_config = QVBoxLayout()
        
        # File Selection Group
        file_grp = QGroupBox("File Selection")
        file_layout = QVBoxLayout(file_grp)
        
        # Old File
        old_lay = QHBoxLayout()
        self.old_edit = QLineEdit()
        self.old_edit.setPlaceholderText("Select Old Version (.txt / .ml2 / .mll)...")
        btn_old = QPushButton("Browse...")
        btn_old.clicked.connect(lambda: self._browse_file(self.old_edit))
        old_lay.addWidget(QLabel("Old Version:"))
        old_lay.addWidget(self.old_edit)
        old_lay.addWidget(btn_old)
        file_layout.addLayout(old_lay)

        # New File
        new_lay = QHBoxLayout()
        self.new_edit = QLineEdit()
        self.new_edit.setPlaceholderText("Select New Version (.txt / .ml2 / .mll)...")
        btn_new = QPushButton("Browse...")
        btn_new.clicked.connect(lambda: self._browse_file(self.new_edit))
        new_lay.addWidget(QLabel("New Version:"))
        new_lay.addWidget(self.new_edit)
        new_lay.addWidget(btn_new)
        file_layout.addLayout(new_lay)
        
        left_config.addWidget(file_grp)

        # Signature Template Group
        sig_grp = QGroupBox("Signature Template Configuration")
        sig_layout = QVBoxLayout(sig_grp)
        
        # (Global signature image removed to support per-signature images in the table below)

        self.sig_table = QTableWidget(0, 3)
        self.sig_table.setHorizontalHeaderLabels(["Name", "Designation/Label", "Signature Image (Optional)"])
        self.sig_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.sig_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.sig_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.sig_table.setFixedHeight(160)
        self.sig_table.verticalHeader().setDefaultSectionSize(28)
        sig_layout.addWidget(self.sig_table)
        
        sig_btn_lay = QHBoxLayout()
        btn_add_sig = QPushButton("+ Add Row")
        btn_add_sig.clicked.connect(self._add_signature_row)
        btn_rem_sig = QPushButton("- Remove Selected")
        btn_rem_sig.clicked.connect(self._remove_signature_row)
        sig_btn_lay.addWidget(btn_add_sig)
        sig_btn_lay.addWidget(btn_rem_sig)
        sig_layout.addLayout(sig_btn_lay)
        
        # Default signatures
        self._add_signature_row("Ashish Dixit", "HRSTS")
        self._add_signature_row("", "App. Date")
        self._add_signature_row("", "DY.CSTE/D&D")
        
        left_config.addWidget(sig_grp)
        config_h_layout.addLayout(left_config, 2)

        # Right side: Style & Options
        right_config = QVBoxLayout()
        
        # Export Options Group
        opt_grp = QGroupBox("Report Settings")
        opt_layout = QVBoxLayout(opt_grp)
        
        self.radio_all = QRadioButton("Export All Pages")
        self.radio_changed = QRadioButton("Export Changed Pages Only")
        self.radio_changed.setChecked(True)
        
        self.opt_group = QButtonGroup(self)
        self.opt_group.addButton(self.radio_all)
        self.opt_group.addButton(self.radio_changed)
        
        opt_layout.addWidget(self.radio_all)
        opt_layout.addWidget(self.radio_changed)
        
        self.check_grid = QCheckBox("Show Grid Lines in PDF")
        self.check_grid.setChecked(True)
        opt_layout.addWidget(self.check_grid)

        # Context lines for changed_only mode
        context_lay = QHBoxLayout()
        self.spin_context = QSpinBox()
        self.spin_context.setRange(0, 500)
        self.spin_context.setValue(10)
        self.spin_context.setFixedWidth(60)
        context_lay.addWidget(QLabel("Context Lines (±):"))
        context_lay.addWidget(self.spin_context)
        context_lay.addStretch()
        opt_layout.addLayout(context_lay)
        
        right_config.addWidget(opt_grp)
        
        # Style Group
        style_grp = QGroupBox("Diff Style Settings")
        style_layout = QVBoxLayout(style_grp)
        
        def get_btn_style(color_hex):
            # Calculate luminance to decide between black and white text
            c = QColor(color_hex)
            lum = (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255
            text_color = "black" if lum > 0.5 else "white"
            return f"background-color: {color_hex}; border: 1px solid #666; font-size: 9px; color: {text_color}; font-weight: bold;"

        def create_color_picker(label, bg_key, fg_key):
            row_widget = QWidget()
            lay = QHBoxLayout(row_widget)
            lay.setContentsMargins(0, 2, 0, 2)
            lay.addWidget(QLabel(label), 1)
            
            # BG Picker
            btn_bg = QPushButton("BG")
            btn_bg.setFixedWidth(40)
            btn_bg.setStyleSheet(get_btn_style(self.colors[bg_key]))
            btn_bg.clicked.connect(lambda: self._pick_color(bg_key, btn_bg))
            lay.addWidget(btn_bg)

            # FG Picker
            btn_fg = QPushButton("FG")
            btn_fg.setFixedWidth(40)
            btn_fg.setStyleSheet(get_btn_style(self.colors[fg_key]))
            btn_fg.clicked.connect(lambda: self._pick_color(fg_key, btn_fg))
            lay.addWidget(btn_fg)
            return row_widget
        
        self.get_btn_style = get_btn_style # Expose for use in _pick_color

        style_layout.addWidget(create_color_picker("Inserted:", 'insert_bg', 'insert_fg'))
        style_layout.addWidget(create_color_picker("Deleted:", 'delete_bg', 'delete_fg'))
        style_layout.addWidget(create_color_picker("Replaced:", 'replace_bg', 'replace_fg'))
        style_layout.addWidget(create_color_picker("Intra-line Left:", 'intra_left_bg', 'intra_left_fg'))
        style_layout.addWidget(create_color_picker("Intra-line Right:", 'intra_right_bg', 'intra_right_fg'))
        
        right_config.addWidget(style_grp)
        right_config.addStretch()
        
        config_h_layout.addLayout(right_config, 1)

        # Bottom Actions
        btn_row = QHBoxLayout()
        self.btn_compare = QPushButton("🚀 Run Comparison")
        self.btn_compare.setFixedHeight(45)
        self.btn_compare.setStyleSheet("background-color: #E60027; color: white; font-weight: bold; font-size: 14px;")
        self.btn_compare.clicked.connect(self._on_compare)
        
        self.btn_export = QPushButton("📤 Export PDF Report")
        self.btn_export.setFixedHeight(45)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export)
        
        btn_row.addWidget(self.btn_compare, 2)
        btn_row.addWidget(self.btn_export, 1)
        main_layout.addLayout(btn_row)
        
        self.splitter.addWidget(config_container)

        # --- Bottom Section: Results ---
        self.results_area = QTextEdit()
        self.results_area.setReadOnly(True)
        self.results_area.setPlaceholderText("Comparison results will appear here...")
        self.results_area.setStyleSheet("font-family: 'Consolas', monospace; background-color: #1e1e1e; color: #d4d4d4; font-size: 12px;")
        self.splitter.addWidget(self.results_area)
        
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        
        self.cached_diff = None

    def _apply_theme(self):
        # Basic dark theme adjustment for the app's style
        try:
            from gui.theme import apply_theme
            apply_theme(self, dark_mode=True)
        except ImportError:
            pass

    def _pick_color(self, key, button):
        color = QColorDialog.getColor(QColor(self.colors[key]), self, f"Pick {key.capitalize()} Color")
        if color.isValid():
            self.colors[key] = color.name()
            button.setStyleSheet(self.get_btn_style(self.colors[key]))
            if self.cached_diff:
                self._display_diff(self.cached_diff)

    def _add_signature_row(self, name="", label="", img=""):
        row = self.sig_table.rowCount()
        self.sig_table.insertRow(row)
        self.sig_table.setItem(row, 0, QTableWidgetItem(name))
        self.sig_table.setItem(row, 1, QTableWidgetItem(label))
        
        # Add Image selection button and display
        container = QWidget()
        btn_lay = QVBoxLayout(container)
        btn_lay.setContentsMargins(1, 1, 1, 1)
        btn_lay.setSpacing(0)
        btn_lay.setAlignment(Qt.AlignCenter)
        btn_pick = QPushButton("Browse...")
        btn_pick.setFixedHeight(22)
        btn_pick.setFixedWidth(90)
        btn_pick.setStyleSheet("font-size: 11px; padding: 0px; border-radius: 4px;")
        if img: btn_pick.setToolTip(img)
        btn_pick.clicked.connect(lambda: self._row_browse_img(row))
        btn_lay.addWidget(btn_pick)
        self.sig_table.setCellWidget(row, 2, container)

    def _row_browse_img(self, row):
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)")
        if path:
            container = self.sig_table.cellWidget(row, 2)
            if container:
                btn = container.findChild(QPushButton)
                if btn:
                    btn.setToolTip(path)
                    btn.setText(os.path.basename(path))

    def _remove_signature_row(self):
        rows = self.sig_table.selectionModel().selectedRows()
        for r in sorted(rows, reverse=True):
            self.sig_table.removeRow(r.row())

    def _browse_file(self, edit_widget):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Source Files (*.txt *.ml2 *.mll);;All Files (*)")
        if path:
            edit_widget.setText(path)

    def _browse_sig_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Signature Image", "", "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)")
        if path:
            self.sig_img_edit.setText(path)

    def _on_compare(self):
        path_a = self.old_edit.text()
        path_b = self.new_edit.text()
        
        if not os.path.exists(path_a) or not os.path.exists(path_b):
            QMessageBox.warning(self, "Missing Files", "Please select both Old and New files.")
            return
            
        try:
            with open(path_a, 'r', encoding='utf-8', errors='ignore') as f:
                text_a = f.read()
            with open(path_b, 'r', encoding='utf-8', errors='ignore') as f:
                text_b = f.read()
                
            self.cached_diff = compare_texts(text_a, text_b)
            self._display_diff(self.cached_diff)
            self.btn_export.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", f"Failed to compare files: {e}")

    def _display_diff(self, diff_data):
        self.results_area.clear()
        
        def append_styled(tag, text_a, text_b):
            if tag == 'equal':
                self.results_area.setTextBackgroundColor(QColor(Qt.transparent))
                self.results_area.setTextColor(QColor("#d4d4d4"))
                self.results_area.append(f"  {text_a}")
            else:
                # Check for granular diff
                if isinstance(text_a, list) or isinstance(text_b, list):
                    if tag == 'replace':
                        # Show original with removals (Green)
                        bg_a = QColor(self.colors.get('delete_bg', "#E8F5E9"))
                        fg_a = QColor(self.colors.get('delete_fg', "#2E7D32"))
                        self.results_area.setTextBackgroundColor(bg_a)
                        self.results_area.setTextColor(fg_a)
                        self.results_area.insertPlainText("- ")
                        self._render_granular_line(text_a, bg_a, fg_a, is_left=True)
                        self.results_area.append("")
                        
                        # Show new with additions (Red)
                        bg_b = QColor(self.colors.get('insert_bg', "#FFEBEE"))
                        fg_b = QColor(self.colors.get('insert_fg', "#C62828"))
                        self.results_area.setTextBackgroundColor(bg_b)
                        self.results_area.setTextColor(fg_b)
                        self.results_area.insertPlainText("+ ")
                        self._render_granular_line(text_b, bg_b, fg_b, is_left=False)
                        self.results_area.append("")
                    else:
                        # Pure delete or insert
                        bg_color = QColor(self.colors.get(f"{tag}_bg", "#000000"))
                        fg_color = QColor(self.colors.get(f"{tag}_fg", "#ffffff"))
                        prefix = "-" if tag == 'delete' else "+"
                        self.results_area.setTextBackgroundColor(bg_color)
                        self.results_area.setTextColor(fg_color)
                        self.results_area.insertPlainText(f"{prefix} ")
                        parts = text_a if tag == 'delete' else text_b
                        self._render_granular_line(parts, bg_color, fg_color, is_left=(tag == 'delete'))
                        self.results_area.append("")
                else:
                    bg_color = QColor(self.colors.get(f"{tag}_bg", "#000000"))
                    fg_color = QColor(self.colors.get(f"{tag}_fg", "#ffffff"))
                    prefix = "-" if tag == 'delete' else ("+" if tag == 'insert' else "!")
                    self.results_area.setTextBackgroundColor(bg_color)
                    self.results_area.setTextColor(fg_color)
                    content = text_a if tag == 'delete' else (text_b if tag == 'insert' else f"{text_a} -> {text_b}")
                    self.results_area.append(f"{prefix} {content}")

        for tag, text_a, text_b in diff_data:
            append_styled(tag, text_a, text_b)
        
        self.results_area.setTextBackgroundColor(QColor(Qt.transparent))
        self.results_area.setTextColor(QColor("#d4d4d4"))
        self.results_area.verticalScrollBar().setValue(0)

    def _render_granular_line(self, parts, base_bg, base_fg, is_left=False):
        # We assume 'parts' is a list from get_line_diff
        for part in parts:
            if isinstance(part, tuple) and part[0] == 'changed':
                # Use customizable colors
                key_prefix = 'intra_left' if is_left else 'intra_right'
                h_bg = QColor(self.colors.get(f'{key_prefix}_bg', "#00FF00" if is_left else "#FF3333"))
                h_fg = QColor(self.colors.get(f'{key_prefix}_fg', "#000000"))
                
                self.results_area.setTextBackgroundColor(h_bg)
                self.results_area.setTextColor(h_fg)
                self.results_area.insertPlainText(part[1])
                # Restore base colors
                self.results_area.setTextBackgroundColor(base_bg)
                self.results_area.setTextColor(base_fg)
            else:
                self.results_area.insertPlainText(part)

    def _on_export(self):
        if not self.cached_diff: return
        
        out_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "Comparison_Report.pdf", "PDF Files (*.pdf)")
        if not out_path: return
        
        path_a = self.old_edit.text()
        path_b = self.new_edit.text()
        
        # Get CRC/Checksum
        crc_a, checksum_a = get_mll_data(path_a)
        crc_b, checksum_b = get_mll_data(path_b)
        
        header_data = {
            'path_a': path_a, 'crc_a': crc_a, 'checksum_a': checksum_a,
            'path_b': path_b, 'crc_b': crc_b, 'checksum_b': checksum_b
        }
        
        # Get Signatures from table
        signatures = []
        for r in range(self.sig_table.rowCount()):
            name_item = self.sig_table.item(r, 0)
            label_item = self.sig_table.item(r, 1)
            container = self.sig_table.cellWidget(r, 2)
            
            name = name_item.text() if name_item else ""
            label = label_item.text() if label_item else ""
            img_path = ""
            if container:
                btn = container.findChild(QPushButton)
                if btn:
                    img_path = btn.toolTip()
            
            # Skip completely empty rows
            if not name and not label and not img_path:
                continue
                
            signatures.append({
                'name': name,
                'label': label,
                'img': img_path
            })
            
        options = {
            'changed_only': self.radio_changed.isChecked(),
            'context_lines': self.spin_context.value(),
            'colors': self.colors,
            'show_grid': self.check_grid.isChecked()
        }
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            generate_comparison_report(out_path, header_data, self.cached_diff, signatures, options)
            QApplication.restoreOverrideCursor()
            QMessageBox.information(self, "Success", f"Comparison report generated:\n{out_path}")
            os.startfile(out_path)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", f"Failed to generate PDF:\n{str(e)}")

if __name__ == "__main__":
    app = QApplication([])
    win = ComparisonTab()
    win.show()
    app.exec()
