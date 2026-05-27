# -*- coding: utf-8 -*-
import os
import sys
import re
from pathlib import Path
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, 
    QLineEdit, QToolButton, QProgressBar, QTextEdit,
    QFileDialog, QCheckBox, QComboBox, QTimeEdit, QSplitter,
    QMessageBox, QStyle, QScrollArea, QDateEdit, QTabWidget,
    QFrame, QStackedWidget, QSizePolicy, QGroupBox, QDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox,
    QAbstractItemView
)
from PySide6.QtCore import Qt, QSize, QDate, Signal, Slot, QEvent, QSettings, QPoint
from PySide6.QtGui import QIcon, QColor, QFont, QPixmap, QPainter, QPolygon, QKeyEvent
from PySide6.QtWidgets import QApplication

from core.log_analyzer_core import (
    GlobalWorker, EventWorker, BitWorker, ErrorWorker,
    err_plot_time_chart
)
from gui.ide_theme import ModernTheme


class _ArrowOverlayMixin:
    def _init_arrow_overlay(self):
        self._arrow_label = _ArrowIndicator(self)
        self._arrow_label.show()

    def _update_arrow_overlay_style(self, arrow_color: str, border_color: str):
        if hasattr(self, "_arrow_label"):
            self._arrow_label.set_colors(arrow_color, border_color)

    def _position_arrow_overlay(self):
        if hasattr(self, "_arrow_label"):
            self._arrow_label.setGeometry(self.width() - 20, 0, 20, self.height())
            self._arrow_label.raise_()


class ArrowComboBox(QComboBox, _ArrowOverlayMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_arrow_overlay()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_arrow_overlay()


_CALENDAR_DARK_STYLE = """
    QCalendarWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
    }
    /* Navigation bar (header row with month/year and arrows) */
    QCalendarWidget QWidget#qt_calendar_navigationbar {
        background-color: #2a2a2a;
        border-bottom: 1px solid #444;
        padding: 4px;
    }
    /* Month/Year nav buttons (◀ ▶) and month/year label buttons */
    QCalendarWidget QToolButton {
        color: #e0e0e0;
        background-color: #333;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 3px 8px;
        font-weight: bold;
        font-size: 11px;
    }
    QCalendarWidget QToolButton:hover {
        background-color: #00aaff;
        color: #ffffff;
        border-color: #00aaff;
    }
    QCalendarWidget QToolButton:pressed {
        background-color: #0077cc;
    }
    QCalendarWidget QToolButton::menu-indicator { image: none; }
    /* The left/right arrows inside the nav buttons */
    QCalendarWidget QToolButton#qt_calendar_prevmonth,
    QCalendarWidget QToolButton#qt_calendar_nextmonth {
        qproperty-icon: none;
        min-width: 24px;
        min-height: 24px;
    }
    /* Year/Month spin box inside navigation */
    QCalendarWidget QSpinBox {
        background-color: #2b2b2b;
        color: #e0e0e0;
        border: 1px solid #555;
        padding: 2px;
    }
    /* Day-of-week header row */
    QCalendarWidget QWidget { alternate-background-color: #252525; }
    /* Individual day cells */
    QCalendarWidget QAbstractItemView {
        background-color: #1e1e1e;
        selection-background-color: #00aaff;
        selection-color: #ffffff;
        color: #e0e0e0;
        gridline-color: #333;
        outline: none;
    }
    QCalendarWidget QAbstractItemView:enabled {
        color: #e0e0e0;
    }
    QCalendarWidget QAbstractItemView:disabled {
        color: #555;
    }
"""

class ArrowDateEdit(QDateEdit, _ArrowOverlayMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_arrow_overlay()
        self._cal_styled = False

    def calendarWidget(self):
        """Return the calendar widget, applying dark styling on first access."""
        w = super().calendarWidget()
        if w and not self._cal_styled:
            w.setStyleSheet(_CALENDAR_DARK_STYLE)
            self._cal_styled = True
        return w

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_arrow_overlay()


class ArrowTimeEdit(QTimeEdit):
    """QTimeEdit with a premium two-arrow (▲/▼) spin indicator overlay."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._spin_label = _SpinIndicator(self)
        self._spin_label.show()
        self._arrow_color = "#e0e0e0"
        self._border_color = "rgba(255,255,255,0.18)"

    def _update_arrow_overlay_style(self, arrow_color: str, border_color: str):
        self._arrow_color = arrow_color
        self._border_color = border_color
        self._spin_label.set_colors(arrow_color, border_color)

    def _position_arrow_overlay(self):
        self._spin_label.setGeometry(self.width() - 20, 0, 20, self.height())
        self._spin_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_arrow_overlay()


class _ArrowIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._arrow_color = QColor("#e0e0e0")
        self._border_color = QColor(255, 255, 255, 46)
        self.setFixedWidth(20)

    def set_colors(self, arrow_color: str, border_color: str):
        self._arrow_color = QColor(arrow_color)
        self._border_color = QColor(border_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self._border_color)
        painter.drawLine(0, 0, 0, self.height())
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._arrow_color)
        cx = self.width() // 2 + 1
        cy = self.height() // 2 + 1
        tri = QPolygon([
            QPoint(cx - 4, cy - 2),
            QPoint(cx + 4, cy - 2),
            QPoint(cx, cy + 3),
        ])
        painter.drawPolygon(tri)

    def mousePressEvent(self, event):
        parent = self.parent()
        if isinstance(parent, QComboBox):
            parent.showPopup()
            event.accept()
            return
        if isinstance(parent, QDateEdit):
            parent.setFocus()
            # Simulate a click at the native calendar-popup button position
            # (rightmost area of the QDateEdit, where the hidden native button sits)
            from PySide6.QtGui import QMouseEvent as _ME
            from PySide6.QtCore import QPointF
            btn_pos = QPointF(parent.width() - 10, parent.height() / 2)
            global_pos = parent.mapToGlobal(btn_pos.toPoint())
            press = _ME(
                QEvent.Type.MouseButtonPress,
                btn_pos,
                QPointF(global_pos),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            release = _ME(
                QEvent.Type.MouseButtonRelease,
                btn_pos,
                QPointF(global_pos),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.NoButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.sendEvent(parent, press)
            QApplication.sendEvent(parent, release)
            event.accept()
            return
        super().mousePressEvent(event)

class _SpinIndicator(QWidget):
    """Overlay showing ▲ (top) and ▼ (bottom) separated by a hairline, for QTimeEdit."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._arrow_color = QColor("#e0e0e0")
        self._border_color = QColor(255, 255, 255, 46)
        self.setFixedWidth(20)
        self.setCursor(Qt.ArrowCursor)

    def set_colors(self, arrow_color: str, border_color: str):
        self._arrow_color = QColor(arrow_color)
        self._border_color = QColor(border_color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        mid = h // 2
        cx = w // 2 + 1

        # Vertical separator on the left edge
        painter.setPen(self._border_color)
        painter.drawLine(0, 0, 0, h)

        # Hairline between the two halves
        painter.setPen(self._border_color)
        painter.drawLine(2, mid, w - 2, mid)

        painter.setPen(Qt.NoPen)
        painter.setBrush(self._arrow_color)

        # ▲ upper half — pointing up
        up_cy = mid // 2
        up_tri = QPolygon([
            QPoint(cx - 4, up_cy + 3),
            QPoint(cx + 4, up_cy + 3),
            QPoint(cx,     up_cy - 3),
        ])
        painter.drawPolygon(up_tri)

        # ▼ lower half — pointing down
        dn_cy = mid + (h - mid) // 2
        dn_tri = QPolygon([
            QPoint(cx - 4, dn_cy - 3),
            QPoint(cx + 4, dn_cy - 3),
            QPoint(cx,     dn_cy + 3),
        ])
        painter.drawPolygon(dn_tri)

    def mousePressEvent(self, event):
        """Top half = step up, bottom half = step down."""
        parent = self.parent()
        if isinstance(parent, QTimeEdit):
            parent.setFocus()
            if event.y() < self.height() // 2:
                parent.stepUp()
            else:
                parent.stepDown()
            event.accept()
            return
        super().mousePressEvent(event)

class ChartPreviewDialog(QDialog):
    def __init__(self, png_bytes, parent=None, is_dark=True):
        super().__init__(parent)
        self.setWindowTitle("Advanced Log Graph Preview")
        self.resize(1100, 800)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self._png = png_bytes
        self._scale = 1.0
        
        # Theme detection
        self.is_dark = is_dark
        self._bg = "#0d1117" if is_dark else "#ffffff"
        self._tbar_bg = "#1a1a1a" if is_dark else "#f0f0f0"
        self._tbar_border = "#333" if is_dark else "#ccc"
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        
        # Toolbar
        tbar = QFrame(); tbar.setFixedHeight(50); tbar.setStyleSheet(f"background: {self._tbar_bg}; border-bottom: 1px solid {self._tbar_border};")
        tl = QHBoxLayout(tbar); tl.setContentsMargins(15,0,15,0); tl.setSpacing(10)
        
        self.btn_zin = QPushButton("🔍+ Zoom In"); self.btn_zin.clicked.connect(lambda: self._zoom(1.2))
        self.btn_zout = QPushButton("🔍- Zoom Out"); self.btn_zout.clicked.connect(lambda: self._zoom(0.8))
        self.btn_fit = QPushButton("📺 Fit to Page"); self.btn_fit.clicked.connect(self._fit_to_page)
        self.btn_save = QPushButton("💾 Save / Export"); self.btn_save.clicked.connect(self._save)
        self.btn_close = QPushButton("✖ Close"); self.btn_close.clicked.connect(self.close)
        
        for b in [self.btn_zin, self.btn_zout, self.btn_fit, self.btn_save, self.btn_close]:
            b.setMinimumHeight(30); tl.addWidget(b)
        tl.addStretch()
        layout.addWidget(tbar)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)
        self.scroll.setStyleSheet(f"background: {self._bg}; border: none;")
        
        self.img_lbl = QLabel()
        self.img_lbl.setAlignment(Qt.AlignCenter)
        self._px = QPixmap(); self._px.loadFromData(self._png)
        self.img_lbl.setPixmap(self._px)
        
        self.scroll.setWidget(self.img_lbl)
        layout.addWidget(self.scroll)

    def _zoom(self, factor):
        self._scale *= factor
        self._scale = max(0.1, min(self._scale, 5.0))
        new_px = self._px.scaled(self._px.size() * self._scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_lbl.setPixmap(new_px)
        self.img_lbl.adjustSize()

    def _fit_to_page(self):
        # Calculate scale factor to fit either width or height of scroll area
        aw, ah = self.scroll.viewport().width() - 4, self.scroll.viewport().height() - 4
        pw, ph = self._px.width(), self._px.height()
        if pw <= 0 or ph <= 0: return
        self._scale = min(aw / pw, ah / ph)
        self._scale = max(0.1, min(self._scale, 5.0))
        new_px = self._px.scaled(self._px.size() * self._scale, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.img_lbl.setPixmap(new_px)
        self.img_lbl.adjustSize()

    def _save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Graph", "chart_export.png", "PNG Images (*.png);;All Files (*.*)")
        if path: self._px.save(path, "PNG")

class CommAnalysisDialog(QDialog):
    def __init__(self, events: List[Dict[str, Any]], parent=None, is_dark=True):
        super().__init__(parent)
        self.setWindowTitle("Communication Link Analysis")
        self.resize(1100, 800)
        self._events = events
        self.is_dark = is_dark
        self._setup_ui()
        self._populate()

    def _setup_ui(self):
        main_lay = QVBoxLayout(self)
        
        # --- Top Filter Bar (Applies to ALL tabs) ---
        tbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter: Search Station or Message...")
        self.search.textChanged.connect(self._filter)
        tbar.addWidget(QLabel("🔍 Filter:"))
        tbar.addWidget(self.search, 1)
        
        self.btn_csv = QPushButton("💾 Export CSV")
        self.btn_csv.clicked.connect(self._export)
        tbar.addWidget(self.btn_csv)
        main_lay.addLayout(tbar)

        dbar = QHBoxLayout()
        self.date_start = ArrowDateEdit(); self.date_start.setCalendarPopup(True); self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_end = ArrowDateEdit(); self.date_end.setCalendarPopup(True); self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.btn_apply = QPushButton("Apply Filter")
        self.btn_apply.clicked.connect(self._filter)
        
        dbar.addWidget(QLabel("📅 From:"))
        dbar.addWidget(self.date_start)
        dbar.addWidget(QLabel("To:"))
        dbar.addWidget(self.date_end)
        dbar.addWidget(self.btn_apply)
        dbar.addStretch(1)
        main_lay.addLayout(dbar)

        # --- Tabs ---
        self.tabs = QTabWidget()
        main_lay.addWidget(self.tabs)

        # Tab 1: All Events
        self.tab_all = QWidget(); tab1_lay = QVBoxLayout(self.tab_all)
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["System", "DateTime", "Address", "Station Name", "Level", "Message"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        tab1_lay.addWidget(self.table)
        self.tabs.addTab(self.tab_all, "📋 All Communication Logs")

        # Tab 2: Failure Summary
        self.tab_summary = QWidget(); tab2_lay = QVBoxLayout(self.tab_summary)
        self.table_sum = QTableWidget()
        self.table_sum.setColumnCount(9)
        self.table_sum.setHorizontalHeaderLabels([
            "System", "Address", "Station Name", 
            "Timeouts", "Downs", "Missed Data/Seq", 
            "Total Fails", "Max Fails/24h", "Status"
        ])
        self.table_sum.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sum.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sum.horizontalHeader().setStretchLastSection(True)
        tab2_lay.addWidget(self.table_sum)
        self.tabs.addTab(self.tab_summary, "📊 Failure Summary")

    def _populate(self):
        if not self._events: return
        self.table.setRowCount(len(self._events))
        
        # Initialize initial dates from data
        dts = [e["dt"] for e in self._events if e.get("dt")]
        if dts:
            min_d, max_d = min(dts).date(), max(dts).date()
            self.date_start.setDate(min_d); self.date_end.setDate(max_d)
        
        for i, e in enumerate(self._events):
            self._set_row(i, e)
        self.table.resizeColumnsToContents()
        self._filter()

    def _set_row(self, i, e):
        addr_match = re.search(r'Address\s+(\d+)\b', e["msg"], re.IGNORECASE)
        addr = addr_match.group(1) if addr_match else ""
        
        self.table.setItem(i, 0, QTableWidgetItem(e.get("system", "")))
        # Use dt_display if available (shorter format without trailing zeros)
        dt_str = e.get("dt_display", str(e.get("dt", "")))
        self.table.setItem(i, 1, QTableWidgetItem(dt_str))
        self.table.setItem(i, 2, QTableWidgetItem(addr))
        self.table.setItem(i, 3, QTableWidgetItem(e.get("station_name", "")))
        self.table.setItem(i, 4, QTableWidgetItem(e.get("level", "")))
        
        msg_item = QTableWidgetItem(e.get("msg", ""))
        if "timeout" in e["msg"].lower(): msg_item.setForeground(QColor("#ff5555"))
        elif "link up" in e["msg"].lower() or "station up" in e["msg"].lower(): msg_item.setForeground(QColor("#55ff55"))
        self.table.setItem(i, 5, msg_item)

    def _filter(self, _=None):
        txt = self.search.text().lower()
        start_qd = self.date_start.date()
        end_qd = self.date_end.date()
        
        for i in range(self.table.rowCount()):
            # Check Text
            txt_match = False
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                if item and txt in item.text().lower():
                    txt_match = True
                    break
            
            # Check Date
            date_match = True
            dt_item = self.table.item(i, 1)
            if dt_item:
                dt_str = dt_item.text().strip()
                if dt_str:
                    # Parse the date part yyyy-mm-dd
                    parts = dt_str.split()
                    if parts:
                        row_qd = QDate.fromString(parts[0], "yyyy-MM-dd")
                        if row_qd.isValid():
                            date_match = (start_qd <= row_qd <= end_qd)
                
            self.table.setRowHidden(i, not (txt_match and date_match))
        
        self._batch_update_summary()

    def _batch_update_summary(self):
        from collections import defaultdict, Counter
        # stats[key] = {'all': [], 'to': 0, 'down': 0, 'miss': 0}
        stats = defaultdict(lambda: {"all": [], "to": 0, "down": 0, "miss": 0})
        
        for i in range(self.table.rowCount()):
            if self.table.isRowHidden(i): continue
            e = self._events[i]
            msg = e.get("msg", "").lower()
            
            # Categorize
            is_to = ("timeout" in msg)
            is_down = ("down" in msg)
            is_miss = any(x in msg for x in ["missed status", "missed sequence", "invalid received"])
            
            if is_to or is_down or is_miss:
                addr_match = re.search(r'Address\s+(\d+)\b', e["msg"], re.IGNORECASE)
                addr = addr_match.group(1) if addr_match else "?"
                key = (e.get("system", "?"), addr, e.get("station_name", "UNKNOWN"))
                
                s = stats[key]
                s["all"].append(e)
                if is_to: s["to"] += 1
                if is_down: s["down"] += 1
                if is_miss: s["miss"] += 1

        self.table_sum.setRowCount(len(stats))
        # Sort by total fails descending
        sorted_stats = sorted(stats.items(), key=lambda x: len(x[1]["all"]), reverse=True)
        
        for i, (key, s) in enumerate(sorted_stats):
            sys, addr, name = key
            fails = s["all"]
            total = len(fails)
            
            # Calculate Max Density (Fails in any 24h window)
            max_24h = 0
            if fails:
                date_counts = Counter([f["dt"].date() for f in fails if f.get("dt")])
                if date_counts: max_24h = max(date_counts.values())
            
            # Determine Status
            if max_24h > 10: 
                status = "● CRITICAL FAILURE"
                color = "#ff4444"
            elif max_24h > 3: 
                status = "● WARNING: Frequent"
                color = "#ffaa00"
            else: 
                status = "● Occasional"
                color = "#55ff55"
            
            self.table_sum.setItem(i, 0, QTableWidgetItem(sys))
            self.table_sum.setItem(i, 1, QTableWidgetItem(addr))
            self.table_sum.setItem(i, 2, QTableWidgetItem(name))
            self.table_sum.setItem(i, 3, QTableWidgetItem(str(s["to"])))
            self.table_sum.setItem(i, 4, QTableWidgetItem(str(s["down"])))
            self.table_sum.setItem(i, 5, QTableWidgetItem(str(s["miss"])))
            self.table_sum.setItem(i, 6, QTableWidgetItem(str(total)))
            self.table_sum.setItem(i, 7, QTableWidgetItem(str(max_24h)))
            
            st_item = QTableWidgetItem(status)
            st_item.setForeground(QColor(color))
            st_item.setFont(QFont("Segoe UI", weight=QFont.Bold))
            self.table_sum.setItem(i, 8, st_item)

        self.table_sum.resizeColumnsToContents()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Analysis", "comm_analysis.csv", "CSV Files (*.csv)")
        if not path: return
        import csv
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["System", "DateTime", "Address", "Station Name", "Level", "Message"])
            for i in range(self.table.rowCount()):
                if not self.table.isRowHidden(i):
                    writer.writerow([self.table.item(i, j).text() for j in range(self.table.columnCount())])
        QMessageBox.information(self, "Export Successful", f"Analysis exported to {path}")

        QMessageBox.information(self, "Export Successful", f"Analysis exported to {path}")

class MappingDialog(QDialog):
    def __init__(self, mapping: Dict[str, Dict[str, str]], parent=None, is_dark=True):
        super().__init__(parent)
        self.setWindowTitle("Logic-Log File Pairing Summary")
        self.resize(800, 400)
        self.is_dark = is_dark
        self._mapping = mapping
        self._setup_ui()

    def _setup_ui(self):
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("The following mapping was used to correlate Addresses to Station Names:"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Event Log File", "Detected Program", "Matched Logic File"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        
        self.table.setRowCount(len(self._mapping))
        for i, (log, info) in enumerate(self._mapping.items()):
            self.table.setItem(i, 0, QTableWidgetItem(log))
            self.table.setItem(i, 1, QTableWidgetItem(info["program"]))
            
            logic_item = QTableWidgetItem(info["logic_file"])
            if info["logic_file"] == "NOT FOUND":
                logic_item.setForeground(QColor("#ff5555"))
            else:
                logic_item.setForeground(QColor("#55ff55"))
            self.table.setItem(i, 2, logic_item)
            
        self.table.resizeColumnsToContents()
        lay.addWidget(self.table)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)

class LogAnalyzerManagerTab(QWidget):
    def __init__(self, parent=None, is_dark=True):
        super().__init__(parent)
        self.is_dark = is_dark
        self.settings = QSettings("Hitachi", "MLK-II ALVT")
        self.worker = None
        self._m = None
        self._sel = []
        self._last_error_rows = None
        self._all_cardfiles = []
        self._last_png = None
        self._last_events = []
        self._last_mapping = {}

        self.setup_ui()



    def apply_styles(self, is_dark: bool = True):
        """Apply theme-aware styles — structural elements only.
        Generic widgets (QComboBox, QPushButton, QLineEdit…) are left to
        ide_theme.py so their pseudo-elements (::drop-down, :hover…) stay intact."""
        self.is_dark = is_dark

        txt_color   = "#e0e0e0"               if is_dark else "#212121"
        card_bg     = "rgba(45,45,45,0.4)"    if is_dark else "rgba(255,255,255,0.9)"
        card_border = "rgba(255,255,255,0.08)" if is_dark else "rgba(0,0,0,0.12)"
        lbl_off     = "rgba(255,255,255,0.6)"  if is_dark else "rgba(0,0,0,0.5)"
        lbl_ph      = "rgba(255,255,255,0.4)"  if is_dark else "rgba(0,0,0,0.4)"
        lbl_active  = "#00ff99"               if is_dark else "#008855"
        footer_bg   = "rgba(35,35,35,0.6)"    if is_dark else "rgba(235,235,235,0.95)"
        console_bg  = "#121212"               if is_dark else "#ffffff"
        console_txt = "#00ff99"               if is_dark else "#008855"
        preview_bg  = "#0d1117"               if is_dark else "#ffffff"
        lbl_res     = "rgba(255,255,255,0.1)"  if is_dark else "rgba(0,0,0,0.2)"
        arrow_color = "#e0e0e0" if is_dark else "#212121"
        arrow_border = "rgba(255,255,255,0.18)" if is_dark else "rgba(0,0,0,0.18)"

        if hasattr(self, 'status'):
            self.status.setStyleSheet(
                "color: rgba(255,255,255,0.7);" if is_dark else "color: rgba(0,0,0,0.7);"
            )

        for attr_name in (
            'cmb_mode', 'cmb_station', 'cmb_y', 'cmb_year', 'cmb_month', 'cmb_day',
            'date_start', 'date_end', 'date_e', 'err_date_from', 'err_date_to',
            'start_t', 'end_t', 'time_from', 'time_to'
        ):
            widget = getattr(self, attr_name, None)
            if hasattr(widget, "_update_arrow_overlay_style"):
                widget._update_arrow_overlay_style(arrow_color, arrow_border)
                widget._position_arrow_overlay()

        # ONLY named selectors — no generic QWidget types
        self.setStyleSheet(f"""
            #LogAnalyzerTab {{ color: {txt_color}; font-family: 'Segoe UI', sans-serif; font-size: 10px; }}
            QScrollArea {{ border: none; background: transparent; }}

            QFrame#Card {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 4px;
            }}
            QFrame#FooterPane {{
                background: {footer_bg};
                border-top: 1px solid {card_border};
            }}
            QFrame#PreviewCard {{
                background: {preview_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
            }}
            QTextEdit#Console {{
                background-color: {console_bg};
                color: {console_txt};
                border: 1px solid {card_border};
                font-family: 'Consolas', monospace;
            }}
            QLabel#CardHeader  {{ color: #00aaff; font-weight: bold; padding-bottom: 2px; }}
            QLabel#FieldLabel  {{ color: {lbl_off}; min-width: 40px; }}
            QLabel#PreviewLabel {{
                color: {lbl_res};
                font-weight: bold;
                border: 1px dashed {card_border};
            }}
            QLabel#InputLabel {{
                color: {lbl_ph};
                font-style: italic;
                font-weight: normal;
            }}
            QLabel#InputLabel[state="active"] {{
                color: {lbl_active};
                font-style: normal;
                font-weight: bold;
            }}
            QPushButton#Primary {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0052D4,stop:1 #6FB1FC);
                color: white; border: none; font-weight: bold;
            }}
            QPushButton#Stop {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eb3349,stop:1 #f45c43);
                color: white; border: none; font-weight: bold;
            }}
            QProgressBar#RunProgress {{
                background-color: rgba(0,0,0,0.3);
                border-radius: 2px;
                text-align: center;
                height: 10px;
            }}
            QProgressBar#RunProgress::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00aaff,stop:1 #00ffcc);
                border-radius: 2px;
            }}
            #LogAnalyzerTab QComboBox,
            #LogAnalyzerTab QDateEdit {{
                padding-right: 22px;
            }}
            #LogAnalyzerTab QComboBox::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                background: transparent;
                border: none;
            }}
            #LogAnalyzerTab QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border: none;
                margin: 0px;
            }}
            #LogAnalyzerTab QDateEdit::drop-down {{
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 20px;
                background: transparent;
                border: none;
            }}
            #LogAnalyzerTab QDateEdit::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
                border: none;
                margin: 0px;
            }}

            /* --- All buttons: clearly visible, not flat --- */
            #LogAnalyzerTab QPushButton {{
                background-color: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.20);
                border-radius: 4px;
                padding: 4px 12px;
                color: {txt_color};
                font-weight: 600;
                min-width: 50px;
            }}
            #LogAnalyzerTab QPushButton:hover {{
                background-color: rgba(0,170,255,0.18);
                border-color: #00aaff;
                color: #00aaff;
            }}
            #LogAnalyzerTab QPushButton:pressed {{
                background-color: rgba(0,170,255,0.30);
                border-color: #00aaff;
            }}
            #LogAnalyzerTab QPushButton#Primary {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #0052D4,stop:1 #6FB1FC);
                color: white; border: none; font-weight: bold;
            }}
            #LogAnalyzerTab QPushButton#Stop {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #eb3349,stop:1 #f45c43);
                color: white; border: none; font-weight: bold;
            }}
        """)




    def _create_card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 4, 12, 4)
        v.setSpacing(0)
        
        if title:
            h = QLabel(title.upper())
            h.setObjectName("CardHeader")
            v.addWidget(h)
            
        return card, v

    def setup_ui(self):
        self.setObjectName("LogAnalyzerTab")
        # 0. Robust Cleanup
        if self.layout():
            layout = self.layout()
            while layout.count():
                it = layout.takeAt(0)
                if it.widget(): it.widget().deleteLater()
            try:
                import shiboken6
                shiboken6.delete(layout)
            except Exception:
                try:
                    import sip
                    sip.delete(layout)
                except Exception:
                    pass

        self.apply_styles()
        
        # 1. Main Splitter (Top: Config | Bottom: Results)
        self._main_split = QSplitter(Qt.Vertical)
        
        # --- Top Area: Scrollable Configuration ---
        config_scroll = QScrollArea()
        config_scroll.setWidgetResizable(True)
        config_container = QWidget()
        config_scroll.setWidget(config_container)
        
        self.config_lay = QVBoxLayout(config_container)
        self.config_lay.setContentsMargins(10, 0, 10, 0)
        self.config_lay.setSpacing(0)

        # A. Mode Selector Card
        mode_card, mv = self._create_card("Analysis Mode")
        mg = QGridLayout(); mg.setSpacing(8); mg.setContentsMargins(0, 2, 0, 0)
        
        lbl_m = QLabel("SELECT MODE:"); lbl_m.setObjectName("FieldLabel")
        self.cmb_mode = ArrowComboBox()
        self.cmb_mode.addItems([
            "Global Upload (All Types)", 
            "User Log (Bit Status)", 
            "Event Log Analysis", 
            "Error Log Analysis"
        ])
        self.cmb_mode.setMinimumWidth(350)
        self.cmb_mode.currentIndexChanged.connect(self.on_mode_changed)
        
        mg.addWidget(lbl_m, 0, 0, Qt.AlignRight)
        mg.addWidget(self.cmb_mode, 0, 1, Qt.AlignLeft)
        mg.setColumnStretch(2, 1)
        mv.addLayout(mg)
        self.config_lay.addWidget(mode_card)

        # B. I/O Config Card
        io_card, iv = self._create_card("Input / Output Configuration")
        ig = QGridLayout(); ig.setSpacing(8); ig.setContentsMargins(0, 2, 0, 0)
        
        # Row 0: Source
        lbl_s = QLabel("SOURCE FILES:"); lbl_s.setObjectName("FieldLabel")
        self.input_label = QLabel("No files selected.")
        self.input_label.setObjectName("InputLabel")
        
        b_box = QWidget(); bl = QHBoxLayout(b_box); bl.setContentsMargins(0,0,0,0); bl.setSpacing(8)
        self.btn_f = QPushButton("📁 Folder"); self.btn_f.clicked.connect(self.pick_folder)
        self.btn_fi = QPushButton("📄 Files"); self.btn_fi.clicked.connect(self.pick_files)
        self.btn_fz = QPushButton("🗜 ZIP"); self.btn_fz.clicked.connect(self.pick_zip)
        bl.addWidget(self.btn_f); bl.addWidget(self.btn_fi); bl.addWidget(self.btn_fz)
        
        ig.addWidget(lbl_s, 0, 0, Qt.AlignRight)
        ig.addWidget(self.input_label, 0, 1)
        ig.addWidget(b_box, 0, 2)
        
        # Row 1: Destination
        lbl_d = QLabel("SAVE RESULTS TO:"); lbl_d.setObjectName("FieldLabel")
        self.out_e = QLineEdit(self._get_last_output_dir())
        self.out_b = QPushButton(); self.out_b.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon)); self.out_b.setFixedWidth(50); self.out_b.clicked.connect(self.choose_out)
        ig.addWidget(lbl_d, 1, 0, Qt.AlignRight)
        ig.addWidget(self.out_e, 1, 1)
        ig.addWidget(self.out_b, 1, 2)
        
        # Row 2: Global Options (Consolidated into one row)
        self.chk_sort = QCheckBox("Sort output chronologically"); self.chk_sort.setChecked(True)
        self.chk_auto = QCheckBox("Auto-open report on completion"); self.chk_auto.setChecked(False)
        
        opt_w = QWidget(); opt_l = QHBoxLayout(opt_w); opt_l.setContentsMargins(0,0,0,0); opt_l.setSpacing(20)
        opt_l.addWidget(self.chk_sort); opt_l.addWidget(self.chk_auto); opt_l.addStretch(1)
        ig.addWidget(opt_w, 2, 1, 1, 2)
        
        ig.setColumnStretch(1, 1)
        iv.addLayout(ig)
        self.config_lay.addWidget(io_card)

        # C. Specialized Options Card
        opt_card, ov = self._create_card("Analysis Parameters")
        self.config_stack = QStackedWidget()
        
        # Stack 0: Global
        p0 = QWidget(); g0 = QGridLayout(p0); g0.setContentsMargins(0,0,0,0); g0.setSpacing(8)
        self.rules_e = QLineEdit()
        self.rules_b = QPushButton("Browse..."); self.rules_b.clicked.connect(self.choose_rules)
        g0.addWidget(QLabel("Rules JSON:"), 0, 0, Qt.AlignRight)
        g0.addWidget(self.rules_e, 0, 1); g0.addWidget(self.rules_b, 0, 2)
        self.chk_propose = QCheckBox("Export proposed rules"); g0.addWidget(self.chk_propose, 1, 1)
        g0.setColumnStretch(1, 1); self.config_stack.addWidget(p0)

        # Stack 1: User Log (Bit)
        p1 = QWidget(); g1 = QGridLayout(p1); g1.setContentsMargins(0,0,0,0); g1.setSpacing(8)
        self.date_e = ArrowDateEdit(QDate.currentDate()); self.date_e.setCalendarPopup(True); self.date_e.setDisplayFormat("dd/MM/yyyy")
        self.start_t = ArrowTimeEdit(); self.start_t.setDisplayFormat("hh:mm:ss AP")
        self.end_t = ArrowTimeEdit(); self.end_t.setDisplayFormat("hh:mm:ss AP")
        self.chk_parse_all = QCheckBox("Parse all logs (ignore date/time filters)")
        self.chk_cons = QCheckBox("Consolidate multiple logs into single report")
        
        # Connect toggle to disable inputs
        self.chk_parse_all.toggled.connect(lambda checked: [self.date_e.setDisabled(checked), self.start_t.setDisabled(checked), self.end_t.setDisabled(checked)])

        g1.addWidget(QLabel("Reference Date:"), 0, 0, Qt.AlignRight); g1.addWidget(self.date_e, 0, 1)
        g1.addWidget(QLabel("Filter Start:"), 1, 0, Qt.AlignRight); g1.addWidget(self.start_t, 1, 1)
        g1.addWidget(QLabel("Filter End:"), 2, 0, Qt.AlignRight); g1.addWidget(self.end_t, 2, 1)
        g1.addWidget(self.chk_parse_all, 3, 1)
        g1.addWidget(self.chk_cons, 4, 1); g1.setColumnStretch(1, 1); self.config_stack.addWidget(p1)

        # Stack 2: Event
        p2 = QWidget(); g2 = QGridLayout(p2); g2.setContentsMargins(0,0,0,0); g2.setSpacing(8)
        self.rules_e_e = QLineEdit()
        self.rules_b_e = QPushButton("Browse..."); self.rules_b_e.clicked.connect(self.choose_rules)
        g2.addWidget(QLabel("Rules JSON:"), 0, 0, Qt.AlignRight)
        g2.addWidget(self.rules_e_e, 0, 1); g2.addWidget(self.rules_b_e, 0, 2)
        
        # Logic File for Station Mapping
        self.logic_e_e = QLineEdit()
        self.logic_b_e = QPushButton("Logic Dir/File..."); self.logic_b_e.clicked.connect(self.choose_logic)
        g2.addWidget(QLabel("Logic Source:"), 1, 0, Qt.AlignRight)
        g2.addWidget(self.logic_e_e, 1, 1); g2.addWidget(self.logic_b_e, 1, 2)

        # Event Type Filtering
        self.chk_include_event = QCheckBox("[event]"); self.chk_include_event.setChecked(True)
        self.chk_include_warning = QCheckBox("[warning]"); self.chk_include_warning.setChecked(True)
        self.chk_include_error = QCheckBox("[error]"); self.chk_include_error.setChecked(True)
        
        # Comm Analysis Controls
        self.btn_pop_evt = QPushButton("↗ Pop-out Analysis"); self.btn_pop_evt.setEnabled(False); self.btn_pop_evt.clicked.connect(self.pop_comm_analysis)
        self.btn_mapping = QPushButton("🔗 View Mapping"); self.btn_mapping.setEnabled(False); self.btn_mapping.clicked.connect(self.show_mapping)
        
        g2.addWidget(QLabel("Include Levels:"), 2, 0, Qt.AlignRight)
        evt_w = QWidget(); evt_l = QHBoxLayout(evt_w); evt_l.setContentsMargins(0,0,0,0); evt_l.setSpacing(15)
        evt_l.addWidget(self.chk_include_event); evt_l.addWidget(self.chk_include_warning); evt_l.addWidget(self.chk_include_error)
        evt_l.addSpacing(20); evt_l.addWidget(self.btn_pop_evt); evt_l.addWidget(self.btn_mapping); evt_l.addStretch(1)
        g2.addWidget(evt_w, 2, 1, 1, 2)
        
        g2.setColumnStretch(1, 1); self.config_stack.addWidget(p2)

        # Stack 3: Error
        p3 = QWidget(); g3 = QGridLayout(p3); g3.setContentsMargins(0,0,0,0); g3.setSpacing(8)
        self.cmb_station = ArrowComboBox(); self.cmb_station.addItem("All"); self.cmb_station.setFixedWidth(140)
        self.cmb_y = ArrowComboBox(); self.cmb_y.addItems(["Auto","Second","Minute","Hour","Date","Month","Year"]); self.cmb_y.setFixedWidth(120)
        self.btn_rep = QPushButton("🔄 Replot"); self.btn_rep.clicked.connect(self.replot)
        self.btn_pop = QPushButton("↗ Pop-out"); self.btn_pop.setEnabled(False); self.btn_pop.clicked.connect(self.pop_chart)
        g3.addWidget(QLabel("Target Station:"), 0, 0, Qt.AlignRight); g3.addWidget(self.cmb_station, 0, 1)
        g3.addWidget(QLabel("Time Scale:"), 0, 2, Qt.AlignRight); g3.addWidget(self.cmb_y, 0, 3)
        g3.addWidget(self.btn_rep, 0, 4); g3.addWidget(self.btn_pop, 0, 5)
        
        self.cmb_year = ArrowComboBox(); self.cmb_month = ArrowComboBox(); self.cmb_day = ArrowComboBox()
        self.cmb_year.setMinimumWidth(80); self.cmb_month.setMinimumWidth(60); self.cmb_day.setMinimumWidth(60)
        self.cmb_year.addItem("All"); self.cmb_month.addItem("All"); self.cmb_day.addItem("All")
        g3.addWidget(QLabel("Date Filter:"), 1, 0, Qt.AlignRight)
        dw = QWidget(); dlay = QHBoxLayout(dw); dlay.setContentsMargins(0,0,0,0); dlay.setSpacing(5)
        dlay.addWidget(self.cmb_year); dlay.addWidget(self.cmb_month); dlay.addWidget(self.cmb_day); dlay.addStretch(1)
        g3.addWidget(dw, 1, 1, 1, 3)

        self.chk_custom_date_range = QCheckBox("Use Custom Date Range")
        self.err_date_from = ArrowDateEdit(QDate.currentDate())
        self.err_date_to = ArrowDateEdit(QDate.currentDate())
        for w in (self.err_date_from, self.err_date_to):
            w.setCalendarPopup(True)
            w.setDisplayFormat("yyyy-MM-dd")
            w.setEnabled(False)
        self.chk_custom_date_range.toggled.connect(self.err_date_from.setEnabled)
        self.chk_custom_date_range.toggled.connect(self.err_date_to.setEnabled)
        g3.addWidget(QLabel("Custom Range:"), 2, 0, Qt.AlignRight)
        rw = QWidget(); rlay = QHBoxLayout(rw); rlay.setContentsMargins(0,0,0,0); rlay.setSpacing(8)
        rlay.addWidget(self.chk_custom_date_range)
        rlay.addWidget(QLabel("From:")); rlay.addWidget(self.err_date_from)
        rlay.addWidget(QLabel(" To:")); rlay.addWidget(self.err_date_to)
        rlay.addStretch(1)
        g3.addWidget(rw, 2, 1, 1, 5)
        
        self.time_from = ArrowTimeEdit(); self.time_to = ArrowTimeEdit(); self.chk_err_ev = QCheckBox("Show Overlaying Events")
        self.time_from.setDisplayFormat("hh:mm:ss AP"); self.time_to.setDisplayFormat("hh:mm:ss AP")
        g3.addWidget(QLabel("Full Time Range:"), 3, 0, Qt.AlignRight)
        tw = QWidget(); tlay = QHBoxLayout(tw); tlay.setContentsMargins(0,0,0,0); tlay.setSpacing(8)
        tlay.addWidget(QLabel("From:")); tlay.addWidget(self.time_from); tlay.addWidget(QLabel(" To:")); tlay.addWidget(self.time_to)
        tlay.addSpacing(20); tlay.addWidget(self.chk_err_ev); tlay.addStretch(1)
        g3.addWidget(tw, 3, 1, 1, 5)
        
        self.cmb_year.currentIndexChanged.connect(self.on_year_change); self.cmb_month.currentIndexChanged.connect(self.on_month_change)
        g3.setColumnStretch(6, 1); self.config_stack.addWidget(p3)

        ov.addWidget(self.config_stack)
        self.config_lay.addWidget(opt_card)
        
        # Expand config scroll to fill space
        self.config_lay.addStretch(1)
        
        # --- Bottom Area: Pinned Global Controls ---
        self.footer_pane = QFrame()
        self.footer_pane.setObjectName("FooterPane")  # Important for global stylesheet targeting
        fl = QHBoxLayout(self.footer_pane); fl.setContentsMargins(15, 8, 15, 8); fl.setSpacing(15)
        
        self.btn_start = QPushButton("START LOG ANALYSIS", objectName="Primary")
        self.btn_start.setMinimumWidth(180)
        self.btn_start.clicked.connect(self.start_analysis)
        
        self.progress = QProgressBar(); self.progress.setValue(0)
        self.progress.setMinimumWidth(100)
        
        self.status = QLabel("Ready"); self.status.setObjectName("StatusLabel")
        
        self.btn_stop = QPushButton("STOP", objectName="Stop"); self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.stop_analysis)
        self.btn_stop.setFixedWidth(80)
        
        fl.addWidget(self.btn_start, 0)
        fl.addWidget(self.progress, 2)
        fl.addWidget(self.status, 1)
        fl.addWidget(self.btn_stop, 0)

        # Build Config Column (Scrollable)
        config_scroll.setWidget(config_container)
        
        # --- Bottom Area: Results Viewer ---
        results_view = QSplitter(Qt.Horizontal)
        self.console = QTextEdit(); self.console.setObjectName("Console"); self.console.setReadOnly(True)
        self.console.setPlaceholderText(">> Run Log will appear here...")
        
        self.preview_card = QFrame(); self.preview_card.setObjectName("PreviewCard")
        pv = QVBoxLayout(self.preview_card); pv.setContentsMargins(5, 5, 5, 5)
        
        self.preview_stack = QStackedWidget()
        
        # Page 0: Label (Default / Info)
        self.preview = QLabel("NO PREVIEW"); self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setObjectName("PreviewLabel")
        self.preview_stack.addWidget(self.preview)
        
        # Page 1: Comm Table
        self.comm_table = QTableWidget()
        self.comm_table.setColumnCount(5)
        self.comm_table.setHorizontalHeaderLabels(["System", "Time", "Address", "Station Name", "Message"])
        self.comm_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.comm_table.horizontalHeader().setStretchLastSection(True)
        self.comm_table.setAlternatingRowColors(True)
        self.comm_table.setStyleSheet("QTableWidget { font-size: 9px; }")
        self.preview_stack.addWidget(self.comm_table)
        
        pv.addWidget(self.preview_stack)
        
        results_view.addWidget(self.console)
        results_view.addWidget(self.preview_card)
        results_view.setStretchFactor(0, 1)
        results_view.setStretchFactor(1, 2)
        
        # Assemble Main Splitter
        self._main_split.addWidget(config_scroll)
        self._main_split.addWidget(self.footer_pane)
        self._main_split.addWidget(results_view)
        
        # Proportions: Top (Config) 75%, Middle (Footer) Fixed/Auto, Bottom (Results) 15%
        self._main_split.setStretchFactor(0, 10)
        self._main_split.setStretchFactor(1, 0) # Fixed size for status bar
        self._main_split.setStretchFactor(2, 2)
        
        # Initial Sizes
        self._main_split.setSizes([600, 40, 100])
        
        final_lay = QVBoxLayout(self); final_lay.setContentsMargins(0,0,0,0); final_lay.setSpacing(0)
        final_lay.addWidget(self._main_split)
        
        # Apply strict styling at end
        self.apply_styles()
        self._restore_last_input_state()

    # --- Keep Existing Logic Methods (no changes) ---
    def default_out(self): return Path.home() / 'Desktop' if (Path.home() / 'Desktop').exists() else Path.cwd()

    def _get_last_input_dir(self) -> str:
        return self.settings.value("log_analyzer/last_input_dir", str(self.default_out()), str)

    def _get_last_output_dir(self) -> str:
        return self.settings.value("log_analyzer/last_output_dir", str(self.default_out()), str)

    def _remember_input_dir(self, path: str) -> None:
        if path:
            self.settings.setValue("log_analyzer/last_input_dir", path)

    def _remember_output_dir(self, path: str) -> None:
        if path:
            self.settings.setValue("log_analyzer/last_output_dir", path)

    def _restore_last_input_state(self) -> None:
        last_input_dir = self._get_last_input_dir()
        if last_input_dir and Path(last_input_dir).exists():
            self.input_label.setText(f"📁 Last path: {last_input_dir}")
            self.input_label.setProperty("state", "active")
            self.style().unpolish(self.input_label)
            self.style().polish(self.input_label)

    def choose_out(self):
        if p := QFileDialog.getExistingDirectory(self, "Choose Output", self.out_e.text()):
            self.out_e.setText(p)
            self._remember_output_dir(p)

    def choose_rules(self): (f := QFileDialog.getOpenFileName(self, "Select rules.json", "", "JSON (*.json)")[0]) and (self.rules_e.setText(f), self.rules_e_e.setText(f))
    def choose_logic(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Logic Source")
        msg.setText("Would you like to select a single logic file or a directory containing multiple logic files?")
        f_btn = msg.addButton("Single File", QMessageBox.ActionRole)
        d_btn = msg.addButton("Directory", QMessageBox.ActionRole)
        msg.exec_()
        
        if msg.clickedButton() == f_btn:
            (f := QFileDialog.getOpenFileName(self, "Select Logic File", "", "Logic Files (*.txt *.ml2);;All Files (*.*)")[0]) and (self.logic_e_e.setText(f), self.btn_mapping.setEnabled(True))
        elif msg.clickedButton() == d_btn:
            (d := QFileDialog.getExistingDirectory(self, "Select Logic Directory")) and (self.logic_e_e.setText(d), self.btn_mapping.setEnabled(True))
    def pick_folder(self): (d := QFileDialog.getExistingDirectory(self, "Select Folder", self._get_last_input_dir())) and (self.set_input('folder', [d]))
    def pick_files(self): (f := QFileDialog.getOpenFileNames(self, "Select Files", self._get_last_input_dir(), "Log Files (*.log *.zip)")[0]) and (self.set_input('files', f))
    def pick_zip(self): (f := QFileDialog.getOpenFileNames(self, "Select ZIP Archives", self._get_last_input_dir(), "ZIP Archives (*.zip);;All Files (*.*)")[0]) and (self.set_input('files', f))
    
    def set_input(self, m, s):
        self._sel = s; self._m = m
        if m == 'folder':
            t = f"📂 {Path(s[0]).name}"
        elif any(Path(x).suffix.lower() == '.zip' for x in s):
            t = f"🗜 {len(s)} ZIP archive(s)"
        else:
            t = f"📄 {len(s)} file(s)"
        self.input_label.setText(t)
        
        # Update styling state
        self.input_label.setProperty("state", "active")
        self.style().unpolish(self.input_label)
        self.style().polish(self.input_label)
        
        if s:
            p = Path(s[0]); out_dir = p if p.is_dir() else p.parent
            if out_dir.exists():
                out_dir_str = str(out_dir)
                self._remember_input_dir(out_dir_str)
                self.out_e.setText(out_dir_str)
                self._remember_output_dir(out_dir_str)

    def on_mode_changed(self, idx):
        self.config_stack.setCurrentIndex(idx)
        self.preview_stack.setCurrentIndex(0)
        self.preview.clear(); self.preview.setText("NO PREVIEW")
        self.btn_pop.setEnabled(False)

    def pop_comm_analysis(self):
        if not self._last_events: return
        dlg = CommAnalysisDialog(self._last_events, self, is_dark=self.is_dark)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.show()
        
    def show_mapping(self):
        # If we have a cached mapping from a finished run, show it
        if self._last_mapping:
            dlg = MappingDialog(self._last_mapping, self, is_dark=self.is_dark)
            dlg.exec_()
            return
        
        # Otherwise, perform a quick validation scan
        logic_path = self.logic_e_e.text()
        if not logic_path or not self._sel:
            QMessageBox.warning(self, "Missing Files", "Please select both Source Files and a Logic Source first.")
            return
            
        from core.log_analyzer_core import EventWorker as EW
        temp_mapping = {}
        
        # Collect actual log files from selection (handling directories)
        check_files = []
        for s in self._sel:
            p = Path(s)
            if p.is_file() and p.suffix.lower() == ".log":
                check_files.append(p)
            elif p.is_dir():
                # Recursive scan for logs in the directory
                for f in p.rglob("*.log"):
                    check_files.append(f)
                    if len(check_files) >= 50: break
            if len(check_files) >= 50: break
            
        for p in check_files[:50]:
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
                header = EW._parse_header(text)
                prog = str(header.get("Program", "Unknown"))
                
                # Simple logic match logic (mirroring core)
                matched = "NOT FOUND"
                ls = Path(logic_path)
                if ls.is_file(): matched = ls.name
                elif ls.is_dir():
                    # Recursive scan (matching core logic)
                    for f in ls.rglob("*"):
                        if f.is_file() and prog.upper() in f.name.upper() and f.suffix.lower() in (".txt", ".ml2"):
                            matched = f.name
                            break
                temp_mapping[p.name] = {"program": prog, "logic_file": matched}
            except: pass
            
        if temp_mapping:
            dlg = MappingDialog(temp_mapping, self, is_dark=self.is_dark)
            dlg.exec_()
        else:
             QMessageBox.warning(self, "Validation Failed", "No valid event logs found in selection to map.")

    def on_progress(self, p, s):
        pct = int(p / s * 100) if s > 0 else 0
        self.progress.setValue(pct)
        self.status.setText(f"Processing... {pct}% ({p}/{s})")
    def on_failed(self, e): 
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        QMessageBox.critical(self, "Analysis Failed", f"Critical error in engine:\n{e}")

    def _build_error_time_filter(self):
        tf = {
            'year': self.cmb_year.currentText(),
            'month': self.cmb_month.currentText(),
            'day': self.cmb_day.currentText(),
            't_from': self.time_from.time(),
            't_to': self.time_to.time()
        }
        if self.chk_custom_date_range.isChecked():
            tf['date_from'] = self.err_date_from.date()
            tf['date_to'] = self.err_date_to.date()
        return tf

    def start_analysis(self):
        if not self._sel: return QMessageBox.warning(self, "Missing Input", "Select source logs first.")
        idx = self.cmb_mode.currentIndex()
        self.console.clear(); self.progress.setValue(0); self.status.setText("Initializing engine...")
        self.btn_start.setEnabled(False); self.btn_stop.setEnabled(True)
        
        if idx == 0: self.worker = GlobalWorker(self._m, self._sel, self.out_e.text(), self.rules_e.text() or None, self.chk_propose.isChecked())
        elif idx == 1: 
            if self.chk_parse_all.isChecked():
                d = s = e = None
            else:
                d = self.date_e.date().toString(Qt.ISODate)
                s, e = self.start_t.time().toString("HH:mm:ss"), self.end_t.time().toString("HH:mm:ss")
            self.worker = BitWorker(self._m, self._sel, self.out_e.text(), d, s, e, self.chk_cons.isChecked(), self.chk_sort.isChecked())
        elif idx == 2: 
            # Determine which event types to include
            include_types = []
            if self.chk_include_event.isChecked(): include_types.append('event')
            if self.chk_include_warning.isChecked(): include_types.append('warning')
            if self.chk_include_error.isChecked(): include_types.append('error')
            self.worker = EventWorker(self._m, self._sel, self.out_e.text(), self.rules_e_e.text() or None, False, self.chk_sort.isChecked(), tuple(include_types), logic_file=self.logic_e_e.text() or None)
        elif idx == 3: 
            # Collect Error Log Filters
            st = self.cmb_station.currentText()
            tf = self._build_error_time_filter()
            self.worker = ErrorWorker(self._m, self._sel, self.out_e.text(), self.chk_err_ev.isChecked(), self.cmb_y.currentText(), 
                                      station=st, time_filter=tf, sort_chrono=self.chk_sort.isChecked())

        self.worker.log_msg.connect(self.console.append); self.worker.progress.connect(self.on_progress)
        self.worker.failed.connect(self.on_failed); self.worker.result_ready.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, r):
        self.btn_start.setEnabled(True); self.btn_stop.setEnabled(False)
        self.status.setText("Done."); self.progress.setValue(100)
        self._all_cardfiles = r.get('card_files', [])
        self._last_error_rows = r.get('error_rows', [])
        if png := r.get('chart_png'):
            self._last_png = png
            px = QPixmap(); px.loadFromData(png)
            self.preview.setPixmap(px.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.preview.setPixmap(px.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.btn_pop.setEnabled(True)
            
            
            # Populate Stations
            current_stations = {self.cmb_station.itemText(i) for i in range(self.cmb_station.count())}
            new_stations = sorted(list({r.get('station') for r in self._last_error_rows if r.get('station')}))
            for s in new_stations:
                if s not in current_stations: self.cmb_station.addItem(s)
            
            # Populate Years
            current_years = {self.cmb_year.itemText(i) for i in range(self.cmb_year.count())}
            new_years = sorted(list({str(r['time_dt'].year) for r in self._last_error_rows if r.get('time_dt')}))
            for y in new_years:
                if y not in current_years: self.cmb_year.addItem(y)

            available_dates = sorted({r['time_dt'].date() for r in self._last_error_rows if r.get('time_dt')})
            if available_dates:
                min_date = QDate(available_dates[0].year, available_dates[0].month, available_dates[0].day)
                max_date = QDate(available_dates[-1].year, available_dates[-1].month, available_dates[-1].day)
                
                # Clear any min/max constraints to allow user to select custom dates freely
                self.err_date_from.setMinimumDate(QDate(2000, 1, 1))
                self.err_date_from.setMaximumDate(QDate(2099, 12, 31))
                self.err_date_to.setMinimumDate(QDate(2000, 1, 1))
                self.err_date_to.setMaximumDate(QDate(2099, 12, 31))
                
                # Only set the date values if custom range is not checked (i.e. default initialization)
                if not self.chk_custom_date_range.isChecked():
                    self.err_date_from.setDate(min_date)
                    self.err_date_to.setDate(max_date)

        if events := r.get('comm_events'):
            self._last_events = events
            self._last_mapping = r.get('mapping', {})
            self.btn_pop_evt.setEnabled(True)
            self.btn_mapping.setEnabled(True) if self._last_mapping else None
            
            self.preview_stack.setCurrentIndex(1)
            self.comm_table.setRowCount(len(events))
            
            # Auto-show mapping if logic was loaded
            if self._last_mapping:
                self.show_mapping()
            for i, e in enumerate(events):
                addr_match = re.search(r'Address\s+(\d+)\b', e["msg"], re.IGNORECASE)
                addr = addr_match.group(1) if addr_match else ""
                
                # Interleaved coloring or labels already handled by system/station_name
                self.comm_table.setItem(i, 0, QTableWidgetItem(e.get("system", "U")))
                self.comm_table.setItem(i, 1, QTableWidgetItem(str(e.get("dt", ""))))
                self.comm_table.setItem(i, 2, QTableWidgetItem(addr))
                self.comm_table.setItem(i, 3, QTableWidgetItem(e.get("station_name", "UNKNOWN")))
                
                msg_item = QTableWidgetItem(e.get("msg", ""))
                if "timeout" in e["msg"].lower(): msg_item.setForeground(QColor("#ff5555"))
                elif "link up" in e["msg"].lower() or "station up" in e["msg"].lower(): msg_item.setForeground(QColor("#55ff55"))
                
                self.comm_table.setItem(i, 4, msg_item)
            self.comm_table.resizeColumnsToContents()
            self.comm_table.horizontalHeader().setStretchLastSection(True)

        if (p := r.get('report_path')) and os.path.exists(p) and self.chk_auto.isChecked(): os.startfile(p)

    def stop_analysis(self):
        if self.worker: self.worker.terminate(); self.status.setText("Aborted."); self.btn_start.setEnabled(True)

    def replot(self):
        if not self._last_error_rows: return
        
        st = self.cmb_station.currentText()
        tf = self._build_error_time_filter()
        
        png = err_plot_time_chart(self._last_error_rows, y_scale=self.cmb_y.currentText(), include_events=self.chk_err_ev.isChecked(), 
                                  all_cardfiles=self._all_cardfiles, station=st, time_filter=tf)
        if png:
            self._last_png = png
            px = QPixmap(); px.loadFromData(png)
            self.preview.setPixmap(px.scaled(self.preview.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def pop_chart(self):
        if not self._last_png: return
        self._chart_dlg = ChartPreviewDialog(self._last_png, self, is_dark=self.is_dark)
        self._chart_dlg.setAttribute(Qt.WA_DeleteOnClose)
        self._chart_dlg.show()

    def on_year_change(self):
        self.cmb_month.clear(); self.cmb_month.addItem("All")
        if (y := self.cmb_year.currentText()) != "All":
            # Filter by time_dt.year
            months = sorted({str(r['time_dt'].month).zfill(2) for r in self._last_error_rows if r.get('time_dt') and str(r['time_dt'].year) == y})
            self.cmb_month.addItems(months)

    def on_month_change(self):
        self.cmb_day.clear(); self.cmb_day.addItem("All")
        if (m := self.cmb_month.currentText()) != "All":
            y = self.cmb_year.currentText()
            # Filter by time_dt.year and .month
            days = sorted({str(r['time_dt'].day).zfill(2) for r in self._last_error_rows if r.get('time_dt') and str(r['time_dt'].year) == y and str(r['time_dt'].month).zfill(2) == m})
            self.cmb_day.addItems(days)
