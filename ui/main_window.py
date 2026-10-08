from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, 
    QHBoxLayout, QLabel, QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygonF, QImage, QPixmap
from ui.dwell_card import DwellCard
from nlp.speech_engine import SpeechEngine

THEME = {
    "bg_window": "#14161D",
    "bg_sub_window": "#181B24",
    "output_bg": "#E8F4F8",
    "output_text": "#0F4C5C",
    "card_subject": "#3A4D6B",
    "card_subject_active": "#5C76A3",
    "card_category": "#2A7B4C",
    "card_action": "#7A4A3B",
    "card_urgent": "#8E2828",
    "card_binary": "#3D4450",
    "card_sub": "#265FB2",
    "card_back": "#8C3030"
}

# Standalone Always-On-Top Floating Gaze Pointer
class GazePointerOverlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(80, 80)
        self.show()

    def move_to_gaze(self, global_pt: QPoint):
        self.move(global_pt.x() - 40, global_pt.y() - 40)
        self.raise_()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = 40.0, 40.0

        # Directional Pointer Wedge
        wedge_polygon = QPolygonF([
            QPointF(cx - 28.0, cy - 8.0),
            QPointF(cx - 2.0, cy - 16.0),
            QPointF(cx - 2.0, cy - 2.0)
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 162, 255, 230))
        painter.drawPolygon(wedge_polygon)

        # Main Cyan Gaze Ring with White Border
        pen = QPen(QColor(255, 255, 255, 255), 3)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 170, 255, 220))
        painter.drawEllipse(int(cx - 16), int(cy - 16), 32, 32)

        # Center Aim Core
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 255, 200, 255))
        painter.drawEllipse(int(cx - 5), int(cy - 5), 10, 10)

class AACMainWindow(QMainWindow):
    recalibrate_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AAC Assistive Gaze Interface")
        self.showFullScreen()

        self.speech_engine = SpeechEngine()
        self.active_category = None
        self.cards = []
        self.page_locked = False
        self.auto_return_timer = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(40, 20, 40, 20)
        self.central_widget.setStyleSheet(f"background-color: {THEME['bg_window']};")

        # Persistent Top Header with Camera Preview
        self.header_layout = QHBoxLayout()
        self.header_title = QLabel("AAC Assistive Gaze Interface")
        self.header_title.setStyleSheet("color: #78909C; font-size: 18px; font-weight: bold;")
        self.header_layout.addWidget(self.header_title)
        self.header_layout.addStretch()

        self.cam_preview = QLabel("Camera Loading...")
        self.cam_preview.setFixedSize(140, 95)
        self.cam_preview.setStyleSheet("border: 2px solid #00E5FF; background-color: #000; color: #FFF;")
        self.cam_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_layout.addWidget(self.cam_preview)
        self.root_layout.addLayout(self.header_layout)

        self.stacked_widget = QStackedWidget()
        self.root_layout.addWidget(self.stacked_widget, stretch=1)

        # ---------------- Page 0: Main Menu ----------------
        self.main_menu_page = QWidget()
        self.main_menu_layout = QVBoxLayout(self.main_menu_page)
        self.main_grid_container = QWidget()
        self.main_grid = QGridLayout(self.main_grid_container)
        self.main_grid.setSpacing(25)
        for r in range(2):
            self.main_grid.setRowStretch(r, 1)
        for c in range(4):
            self.main_grid.setColumnStretch(c, 1)
        self.main_menu_layout.addWidget(self.main_grid_container, stretch=1)

        self.recal_container = QHBoxLayout()
        self.recal_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_menu_layout.addLayout(self.recal_container)

        # ---------------- Page 1: Sub-Menu ----------------
        self.sub_menu_page = QWidget()
        self.sub_menu_layout = QVBoxLayout(self.sub_menu_page)
        self.sub_grid_container = QWidget()
        self.sub_grid = QGridLayout(self.sub_grid_container)
        self.sub_grid.setSpacing(25)
        for r in range(2):
            self.sub_grid.setRowStretch(r, 1)
        for c in range(4):
            self.sub_grid.setColumnStretch(c, 1)
        self.sub_menu_layout.addWidget(self.sub_grid_container, stretch=1)

        # ---------------- Page 2: Output Display ----------------
        self.output_page = QWidget()
        self.output_layout = QVBoxLayout(self.output_page)
        self.output_layout.setContentsMargins(50, 40, 50, 40)

        self.output_label = QLabel("")
        self.output_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_label.setWordWrap(True)
        self.output_label.setStyleSheet(f"""
            background-color: {THEME['output_bg']};
            color: {THEME['output_text']};
            font-size: 58px;
            font-weight: bold;
            border-radius: 20px;
            padding: 30px;
        """)
        self.output_layout.addWidget(self.output_label, stretch=2)

        # Large, easily triggered BACK button across the bottom area
        self.output_back_btn = DwellCard("वापस (BACK)", bg_color=THEME["card_back"], dwell_time_ms=900)
        self.output_back_btn.setMinimumHeight(120)
        self.output_back_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.output_back_btn.dwell_completed.connect(self.return_to_main_now)
        self.output_layout.addWidget(self.output_back_btn, stretch=1)

        self.stacked_widget.addWidget(self.main_menu_page)
        self.stacked_widget.addWidget(self.sub_menu_page)
        self.stacked_widget.addWidget(self.output_page)

        self.cursor_overlay = GazePointerOverlay()
        self.render_main_menu()

    def closeEvent(self, event):
        if hasattr(self, 'cursor_overlay') and self.cursor_overlay:
            self.cursor_overlay.close()
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        elif event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

    def lock_page_briefly(self):
        """1000ms delay on page transitions to settle eye focus."""
        self.page_locked = True
        for card in self.cards:
            card.set_locked(True)
            card.reset_dwell()

        def unlock():
            self.page_locked = False
            for card in self.cards:
                card.set_locked(False)

        QTimer.singleShot(1000, unlock)

    def clear_active_cards(self):
        for card in self.cards:
            card.reset_dwell()
        self.cards.clear()

    def trigger_recalibration(self):
        self.recalibrate_requested.emit()
        self.show_final_output("री-कैलिब्रेशन शुरू... स्क्रीन के केंद्र में देखें")

    def render_main_menu(self):
        if self.auto_return_timer:
            self.auto_return_timer.stop()
            self.auto_return_timer = None

        self.clear_active_cards()
        self.active_category = None
        self.stacked_widget.setCurrentIndex(0)

        while self.main_grid.count():
            w = self.main_grid.takeAt(0).widget()
            if w:
                w.deleteLater()
        while self.recal_container.count():
            w = self.recal_container.takeAt(0).widget()
            if w:
                w.deleteLater()

        items = [
            ("मुझे", THEME["card_subject"], 0, 0),
            ("खाना", THEME["card_category"], 0, 1),
            ("पानी", THEME["card_category"], 0, 2),
            ("जाना है", THEME["card_category"], 0, 3),
            ("दर्द", THEME["card_urgent"], 1, 0),
            ("मदद", THEME["card_action"], 1, 1),
            ("हाँ", THEME["card_binary"], 1, 2),
            ("नहीं", THEME["card_binary"], 1, 3)
        ]

        for text, color, r, c in items:
            card = DwellCard(text, bg_color=color, dwell_time_ms=900)
            card.dwell_completed.connect(self.handle_main_card_selection)
            self.main_grid.addWidget(card, r, c)
            self.cards.append(card)

        recal_btn = DwellCard("RE-CALIBRATE", bg_color="#374151", dwell_time_ms=1200)
        recal_btn.setFixedSize(220, 44)
        recal_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #B0BEC5;
                font-size: 15px;
                font-weight: bold;
                border-radius: 8px;
                border: 1px solid #455A64;
            }
        """)
        recal_btn.dwell_completed.connect(self.trigger_recalibration)
        self.recal_container.addWidget(recal_btn)
        self.cards.append(recal_btn)

        self.lock_page_briefly()

    def render_sub_menu(self, category: str):
        self.clear_active_cards()
        self.active_category = category
        self.stacked_widget.setCurrentIndex(1)

        while self.sub_grid.count():
            w = self.sub_grid.takeAt(0).widget()
            if w:
                w.deleteLater()

        items = []
        if category == "खाना":
            items = [
                ("दाल रोटी", 0, 0), ("चावल सब्ज़ी", 0, 1), 
                ("नाश्ता", 0, 2), ("बिस्कुट", 0, 3),
                ("दाल भात", 1, 0), ("टिफ़िन", 1, 1), 
                ("कुछ और", 1, 2), ("BACK", 1, 3)
            ]
        elif category == "जाना है":
            items = [
                ("कमरे में", 0, 0), ("वॉशरूम", 0, 1), 
                ("बिस्तर पर", 0, 2), ("घर", 0, 3),
                ("बाहर", 1, 0), ("अस्पताल", 1, 1), 
                ("बगीचे में", 1, 2), ("BACK", 1, 3)
            ]
        elif category == "दर्द":
            items = [
                ("सर में", 0, 0), ("पेट में", 0, 1), 
                ("छाती में", 0, 2), ("हाथ में", 0, 3),
                ("पैरों में", 1, 0), ("पीठ में", 1, 1), 
                ("कहीं", 1, 2), ("BACK", 1, 3)
            ]

        for text, r, c in items:
            btn_color = THEME["card_back"] if text == "BACK" else THEME["card_sub"]
            card = DwellCard(text, bg_color=btn_color, dwell_time_ms=900)
            if text == "BACK":
                card.dwell_completed.connect(self.render_main_menu)
            else:
                card.dwell_completed.connect(self.handle_sub_card_selection)
            self.sub_grid.addWidget(card, r, c)
            self.cards.append(card)

        self.lock_page_briefly()

    def handle_main_card_selection(self, label: str):
        if label in ["खाना", "जाना है", "दर्द"]:
            self.render_sub_menu(label)
        elif label == "मुझे":
            for card in self.cards:
                if card.text_label == "मुझे":
                    card.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {THEME['card_subject_active']};
                            color: #FFD600;
                            font-size: 34px;
                            font-weight: bold;
                            border-radius: 20px;
                            border: 4px solid #FFD600;
                        }}
                    """)
        elif label in ["पानी", "मदद"]:
            sentence = self.speech_engine.build_sov_sentence(label, "")
            self.show_final_output(sentence)
        elif label in ["हाँ", "नहीं"]:
            self.show_final_output(label)

    def handle_sub_card_selection(self, label: str):
        sentence = self.speech_engine.build_sov_sentence(self.active_category, label)
        self.show_final_output(sentence)

    def show_final_output(self, sentence: str):
        self.clear_active_cards()
        self.output_label.setText(sentence)
        self.stacked_widget.setCurrentIndex(2)

        self.cards.append(self.output_back_btn)
        self.output_back_btn.reset_dwell()

        QTimer.singleShot(200, lambda: self.speech_engine.speak(sentence))

        self.auto_return_timer = QTimer(self)
        self.auto_return_timer.setSingleShot(True)
        self.auto_return_timer.setInterval(5000)
        self.auto_return_timer.timeout.connect(self.render_main_menu)
        self.auto_return_timer.start()

        self.lock_page_briefly()

    def return_to_main_now(self):
        if self.auto_return_timer:
            self.auto_return_timer.stop()
        self.render_main_menu()

    def update_camera_preview(self, cv_img):
        if cv_img is None:
            return
        h, w, ch = cv_img.shape
        qt_img = QImage(cv_img.data, w, h, ch * w, QImage.Format.Format_BGR888)
        pixmap = QPixmap.fromImage(qt_img).scaled(
            self.cam_preview.width(), self.cam_preview.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.cam_preview.setPixmap(pixmap)

    def update_gaze_point(self, screen_x: int, screen_y: int, is_blinking: bool):
        pt = QPoint(int(screen_x), int(screen_y))

        if hasattr(self, 'cursor_overlay') and self.cursor_overlay is not None:
            self.cursor_overlay.move_to_gaze(pt)

        if is_blinking or self.page_locked:
            for card in self.cards:
                card.reset_dwell()
            return

        for card in self.cards:
            top_left = card.mapToGlobal(QPoint(0, 0))
            card_rect = card.rect()
            card_rect.moveTo(top_left)

            if card_rect.contains(pt):
                card.start_dwell()
            else:
                card.reset_dwell()