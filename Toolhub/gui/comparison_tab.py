# -*- coding: utf-8 -*-
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QFileDialog, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QMessageBox,
    QApplication, QRadioButton, QButtonGroup, QColorDialog, QCheckBox,
    QSpinBox
)
from PySide6.QtCore import Qt, QSize, QSettings
from PySide6.QtGui import QIcon, QFont, QColor

from core.text_compare import get_mll_data, compare_texts
from core.functional_compare import compare_sections
from core.comparison_reporting import generate_comparison_report, generate_functional_report
from gui.comparison_preview import ComparisonPreviewWindow
from gui.log_analyzer_tab import _SpinIndicator


class _SpinBoxIndicator(_SpinIndicator):
    """Same painted ▲/▼ overlay as _SpinIndicator but handles QSpinBox clicks."""
    def mousePressEvent(self, event):
        parent = self.parent()
        if isinstance(parent, QSpinBox):
            parent.setFocus()
            if event.y() < self.height() // 2:
                parent.stepUp()
            else:
                parent.stepDown()
            event.accept()
            return
        super().mousePressEvent(event)


class ArrowSpinBox(QSpinBox):
    """QSpinBox with a clean ▲/▼ overlay, matching the Log Analyser style."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hide native buttons so the overlay is the only control
        self.setStyleSheet("""
            QSpinBox { padding-right: 20px; }
            QSpinBox::up-button, QSpinBox::down-button { width: 0px; border: none; }
        """)
        self._spin_label = _SpinBoxIndicator(self)
        self._spin_label.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._spin_label.setGeometry(self.width() - 20, 0, 20, self.height())
        self._spin_label.raise_()

    def update_arrow_style(self, arrow_color: str, border_color: str):
        self._spin_label.set_colors(arrow_color, border_color)

class ComparisonTab(QMainWindow):
    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.parent_window = parent
        self.setWindowTitle("Application Logic Comparison Tool")
        self.resize(1100, 850)
        
        # Theme-aware colors
        self.colors = {
            'insert_bg': '#FFEBEE', 'insert_fg': '#C62828', # Red for Insertion
            'delete_bg': '#E8F5E9', 'delete_fg': '#2E7D32', # Green for Removal
            'replace_bg': '#FFFF00', 'replace_fg': '#000000', # Yellow BG, Black FG for Replaced
            'intra_left_bg': '#00FF00', 'intra_left_fg': '#000000', # intra-line removal
            'intra_right_bg': '#ff6759', 'intra_right_fg': '#000000' # intra-line addition
        }
        
        self._settings = QSettings("Hitachi", "MLK-II ALVT")
        self._build_ui()
        self._apply_theme()
        self._restore_paths()

    def _build_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Header
        header = QLabel("📄 Application Logic Comparison Tool")
        header.setProperty("class", "brand")
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
        btn_old.clicked.connect(lambda: self._browse_file(self.old_edit, 'old'))
        old_lay.addWidget(QLabel("Old Version:"))
        old_lay.addWidget(self.old_edit)
        old_lay.addWidget(btn_old)
        file_layout.addLayout(old_lay)

        # New File
        new_lay = QHBoxLayout()
        self.new_edit = QLineEdit()
        self.new_edit.setPlaceholderText("Select New Version (.txt / .ml2 / .mll)...")
        btn_new = QPushButton("Browse...")
        btn_new.clicked.connect(lambda: self._browse_file(self.new_edit, 'new'))
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

        # Comparison Mode Selection
        mode_grp = QGroupBox("Comparison Mode")
        mode_lay = QVBoxLayout(mode_grp)
        self.radio_line = QRadioButton("Line-wise Comparison")
        self.radio_line.setChecked(True)
        self.radio_functional = QRadioButton("Functional Logic Comparison")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_line)
        self.mode_group.addButton(self.radio_functional)
        mode_lay.addWidget(self.radio_line)
        mode_lay.addWidget(self.radio_functional)
        opt_layout.addWidget(mode_grp)

        # Context lines for changed_only mode
        context_lay = QHBoxLayout()
        self.spin_context = ArrowSpinBox()
        self.spin_context.setRange(0, 500)
        self.spin_context.setValue(10)
        self.spin_context.setFixedWidth(70)

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
            btn_bg.setFixedWidth(50)
            btn_bg.setStyleSheet(get_btn_style(self.colors[bg_key]))
            btn_bg.clicked.connect(lambda: self._pick_color(bg_key, btn_bg))
            lay.addWidget(btn_bg)

            # FG Picker
            btn_fg = QPushButton("FG")
            btn_fg.setFixedWidth(50)
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

        self.btn_preview = QPushButton("🔍 Preview Report")
        self.btn_preview.setFixedHeight(45)
        self.btn_preview.setEnabled(False)
        self.btn_preview.clicked.connect(self._on_preview_report)
        
        self.btn_export = QPushButton("📤 Export PDF")
        self.btn_export.setFixedHeight(45)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._on_export)
        
        btn_row.addWidget(self.btn_compare, 2)
        btn_row.addWidget(self.btn_preview, 1)
        btn_row.addWidget(self.btn_export, 1)
        main_layout.addLayout(btn_row)
        
        self.splitter.addWidget(config_container)

        # --- Bottom Section: Results (Placeholder) ---
        self.preview_placeholder = QWidget()
        preview_lay = QVBoxLayout(self.preview_placeholder)
        self.lbl_status = QLabel("Ready to compare. Results will open in a new preview window.")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 16px; color: #888; border: 2px dashed #444; border-radius: 10px;")
        preview_lay.addWidget(self.lbl_status)
        self.splitter.addWidget(self.preview_placeholder)
        
        self.cached_diff = None
        self.preview_win = None

    def _apply_theme(self):
        # Basic theme adjustment for the app's style
        try:
            from gui.ide_theme import ModernTheme
            ModernTheme.apply(self, is_dark=self.is_dark)
        except ImportError:
            pass

    def _pick_color(self, key, button):
        color = QColorDialog.getColor(QColor(self.colors[key]), self, f"Pick {key.capitalize()} Color")
        if color.isValid():
            self.colors[key] = color.name()
            button.setStyleSheet(self.get_btn_style(self.colors[key]))
            if self.cached_diff:
                self._on_preview_report()

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

    def _restore_paths(self):
        """Restore previously used file paths from settings."""
        old = self._settings.value("comparison/old_path", "")
        new = self._settings.value("comparison/new_path", "")
        if old and os.path.exists(old):
            self.old_edit.setText(old)
        if new and os.path.exists(new):
            self.new_edit.setText(new)

    def _save_paths(self):
        """Save current file paths to settings."""
        self._settings.setValue("comparison/old_path", self.old_edit.text())
        self._settings.setValue("comparison/new_path", self.new_edit.text())

    def _browse_file(self, edit_widget, which='old'):
        # Start from last used directory, or the directory of the current value
        current = edit_widget.text()
        start_dir = os.path.dirname(current) if current and os.path.exists(current) else \
                    self._settings.value("comparison/last_dir", "")
        path, _ = QFileDialog.getOpenFileName(self, "Select File", start_dir, "Source Files (*.txt *.ml2 *.mll);;All Files (*)")
        if path:
            edit_widget.setText(path)
            self._settings.setValue("comparison/last_dir", os.path.dirname(path))
            # Save path immediately so it's restored on next open
            key = "comparison/old_path" if which == 'old' else "comparison/new_path"
            self._settings.setValue(key, path)

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
        self._save_paths()  # Remember paths before running
            
        try:
            with open(path_a, 'r', encoding='utf-8', errors='ignore') as f:
                text_a = f.read()
            with open(path_b, 'r', encoding='utf-8', errors='ignore') as f:
                text_b = f.read()
                
            if self.radio_line.isChecked():
                self.cached_diff = compare_texts(text_a, text_b)
            else:
                self.cached_diff = compare_sections(text_a, text_b)
                
            self.lbl_status.setText("Comparison complete! Use 'Preview Report' to view.")
            self.btn_preview.setEnabled(True)
            self.btn_export.setEnabled(True)
            self._on_preview_report() # Still auto-open for convenience
        except Exception as e:
            QMessageBox.critical(self, "Comparison Error", f"Failed to compare files: {e}")

    def _on_preview_report(self):
        """Generates a temporary PDF and opens the Preview window"""
        if not self.cached_diff: return
        
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_pdf = os.path.join(temp_dir, f"Comparison_Preview_{datetime.now().strftime('%H%M%S')}.pdf")
        
        header_data = self._get_header_data()
        signatures = self._get_signatures()
        options = self._get_options()
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if self.radio_line.isChecked():
                generate_comparison_report(temp_pdf, header_data, self.cached_diff, signatures, options)
            else:
                generate_functional_report(temp_pdf, header_data, self.cached_diff, signatures, options)
            QApplication.restoreOverrideCursor()
            
            if self.preview_win:
                self.preview_win.close()
            
            self.preview_win = ComparisonPreviewWindow(temp_pdf, self, is_dark=self.is_dark)
            self.preview_win.show()
            self.lbl_status.setText("Report Preview ready in new window.")
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Preview Error", f"Failed to generate preview:\n{e}")

    def _get_header_data(self):
        path_a = self.old_edit.text()
        path_b = self.new_edit.text()
        from core.text_compare import get_mll_data
        crc_a, checksum_a = get_mll_data(path_a)
        crc_b, checksum_b = get_mll_data(path_b)
        return {
            'path_a': path_a, 'crc_a': crc_a, 'checksum_a': checksum_a,
            'path_b': path_b, 'crc_b': crc_b, 'checksum_b': checksum_b
        }

    def _get_signatures(self):
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
                if btn: img_path = btn.toolTip()
            if not name and not label and not img_path: continue
            signatures.append({'name': name, 'label': label, 'img': img_path})
        return signatures

    def _get_options(self):
        return {
            'changed_only': self.radio_changed.isChecked(),
            'context_lines': self.spin_context.value(),
            'colors': self.colors,
            'show_grid': self.check_grid.isChecked()
        }



    def _on_export(self):
        if not self.cached_diff: return
        
        out_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", "Comparison_Report.pdf", "PDF Files (*.pdf)")
        if not out_path: return
        
        path_a = self.old_edit.text()
        path_b = self.new_edit.text()
        
        header_data = self._get_header_data()
        signatures = self._get_signatures()
        options = self._get_options()
        
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            if self.radio_line.isChecked():
                generate_comparison_report(out_path, header_data, self.cached_diff, signatures, options)
            else:
                generate_functional_report(out_path, header_data, self.cached_diff, signatures, options)
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
