from PyQt6.QtWidgets import QPushButton, QSizePolicy
from PyQt6.QtCore import QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen

class DwellCard(QPushButton):
    dwell_completed = pyqtSignal(str)

    def __init__(self, text, bg_color="#2ECC71", dwell_time_ms=900, parent=None):
        super().__init__(text, parent)
        self.text_label = text
        self.bg_color = bg_color
        self.dwell_time_ms = dwell_time_ms
        self.dwell_progress = 0.0
        self.is_locked = False
        self.is_gaze_inside = False

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._apply_style(focused=False)

        self.clicked.connect(self._manual_click)

        self.timer = QTimer(self)
        self.timer.setInterval(20)
        self.timer.timeout.connect(self._update_dwell)

    def _apply_style(self, focused=False):
        border_color = "#00E5FF" if focused else "#2C3240"
        border_width = "4px" if focused else "2px"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.bg_color};
                color: #FFFFFF;
                font-size: 34px;
                font-weight: bold;
                border-radius: 20px;
                border: {border_width} solid {border_color};
            }}
            QPushButton:pressed {{
                background-color: #3D4659;
            }}
        """)

    def set_locked(self, locked: bool):
        self.is_locked = locked
        if locked:
            self.reset_dwell()

    def start_dwell(self):
        if self.is_locked:
            return
        if not self.is_gaze_inside:
            self.is_gaze_inside = True
            self._apply_style(focused=True)
            self.timer.start()

    def reset_dwell(self):
        if self.is_gaze_inside or self.dwell_progress > 0.0:
            self.is_gaze_inside = False
            self.timer.stop()
            self.dwell_progress = 0.0
            self._apply_style(focused=False)
            self.update()

    def _manual_click(self):
        if not self.is_locked:
            self.dwell_completed.emit(self.text_label)

    def _update_dwell(self):
        if self.is_locked or not self.is_gaze_inside:
            self.reset_dwell()
            return

        self.dwell_progress += 20 / self.dwell_time_ms
        if self.dwell_progress >= 1.0:
            self.timer.stop()
            self.dwell_completed.emit(self.text_label)
            self.dwell_progress = 0.0
            self._apply_style(focused=False)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.dwell_progress > 0.0 and not self.is_locked:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("#00E676"), 8)
            painter.setPen(pen)

            center_x = self.width() / 2
            center_y = 52
            radius = 26
            rect = QRectF(center_x - radius, center_y - radius, radius * 2, radius * 2)

            span_angle = int(-self.dwell_progress * 360 * 16)
            painter.drawArc(rect, 90 * 16, span_angle)