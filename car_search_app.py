import sys
import os
import sqlite3
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QLabel,
    QLineEdit, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox,
    QSizePolicy, QGridLayout, QScrollArea, QStackedWidget, QFrame,
    QCompleter, QToolTip
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QIcon, QIntValidator, QCursor, QAction

# --- הגדרות גלובליות ---

CONFIG_FILE = "app_config.json"
HISTORY_LIMIT = 50 
HISTORY_DISPLAY_LIMIT = 4

ICON_MAP = {
    "מספר רכב": "license-plate.png", "שם הרכב": "factory.png", "שם דגם": "car-model.png",
    "רמת גימור": "finish.png", "שנת ייצור": "calendar.png", "דגם מנוע": "engine.png",
    "ביצוע טסט קודם": "test.png", "טסט בתוקף עד": "license.png", "בעלות": "owner.png",
    "צבע הרכב": "color-palette.png", "סוג דלק": "fuel.png", "מועד עלייה לכביש": "road.png"
}
COLUMN_NAMES_HEBREW = [
    "מספר רכב", "קוד תוצר", "סוג דגם", "שם הרכב", "קוד דגם", "שם דגם", "רמת גימור",
    "רמת אבזור בטיחותי", "דרגת זיהום", "שנת ייצור", "דגם מנוע", "ביצוע טסט קודם",
    "טסט בתוקף עד", "בעלות", "מסגרת", "קוד צבע", "צבע הרכב", "צמיג קדמי",
    "צמיג אחורי", "סוג דלק", "הוראת רישום", "מועד עלייה לכביש", "כינוי מסחרי"
]
CATEGORIES = {
    "פרטים עיקריים": [
        "שם הרכב",  "בעלות", "ביצוע טסט קודם", "מועד עלייה לכביש"
        , "שנת ייצור", "צבע הרכב", "טסט בתוקף עד" , "מספר רכב"
    ],
    "מפרט טכני": [
      "דרגת זיהום", "רמת אבזור בטיחותי",  "רמת גימור", "דגם מנוע", "סוג דלק", "צמיג קדמי", "צמיג אחורי", 
        "כינוי מסחרי"
    ],
    "פרטי זיהוי": [
        "מסגרת",  "שם דגם", "הוראת רישום", "קוד תוצר", "קוד דגם", 
        "סוג דגם", "קוד צבע"
    ]
}
loaded_icons = {}

# --- פונקציות עזר ---

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError): pass
    return {"last_db_path": None, "search_history": []}

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)
    except IOError as e: print(f"Error saving config file: {e}")

def load_icons():
    copy_icon_path = resource_path("icon_copy.ico")
    loaded_icons['copy_icon'] = QIcon(copy_icon_path)
    
    delete_icon_path = resource_path("icon_delete.ico")
    loaded_icons['delete_icon'] = QIcon(delete_icon_path)

    search_icon_path = resource_path("icon_search.ico")
    loaded_icons['search_icon'] = QIcon(search_icon_path)

    for field, icon_name in ICON_MAP.items():
        path = resource_path(os.path.join("icons", icon_name))
        pixmap = QPixmap(path)
        loaded_icons[field] = pixmap.scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation) if not pixmap.isNull() else QPixmap()


# --- ווידג'ט כרטיס מותאם אישית ---

class HoverCard(QFrame):
    def __init__(self, field_name, value, parent=None):
        super().__init__(parent)
        self.value_to_copy = str(value)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QFrame { background-color: #2a2a45; border-radius: 12px; border: none; }
        """)
        
        card_layout = QVBoxLayout(self)
        card_layout.setContentsMargins(12, 8, 12, 8)
        card_layout.setSpacing(5)

        header_layout = QHBoxLayout()
        
        field_label = QLabel(field_name)
        field_label.setFont(QFont("Arial", 14, QFont.Bold))
        field_label.setStyleSheet("color: #e0e0e0;")

        value_label = QLabel(self.value_to_copy)
        value_label.setFont(QFont("Arial", 12))
        value_label.setStyleSheet("color: #a0a0c0;")
        value_label.setWordWrap(True)

        self.copy_button = QPushButton()
        self.copy_button.setIcon(loaded_icons['copy_icon'])
        self.copy_button.setFixedSize(24, 24)
        self.copy_button.setStyleSheet("""
            QPushButton { background: none; border: none; border-radius: 12px; }
            QPushButton:hover { background-color: #444a58; }
        """)
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.hide()

        header_layout.addWidget(field_label)
        header_layout.addStretch()
        header_layout.addWidget(self.copy_button)
        
        card_layout.addLayout(header_layout)
        card_layout.addWidget(value_label)
        card_layout.addStretch()

    def enterEvent(self, event):
        self.copy_button.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.copy_button.hide()
        super().leaveEvent(event)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.value_to_copy)
        QToolTip.showText(QCursor.pos(), "הועתק!", self, msecShowTime=1000)


# --- חלון האפליקציה הראשי ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("איתור פרטי רכב 🚗")
        self.setWindowIcon(QIcon(resource_path("my_icon.ico")))

        self.setGeometry(100, 100, 900, 700)
        self.showMaximized()
        self.config = load_config()
        self.db_path = self.config.get("last_db_path")
        self.search_history = self.config.get("search_history", [])

        load_icons()
        self._apply_global_styles()

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        self.setup_screen = self._create_setup_ui()
        self.initial_search_screen = self._create_initial_search_ui()
        self.main_screen = self._create_main_ui()

        self._setup_completer()

        self.stacked_widget.addWidget(self.setup_screen)
        self.stacked_widget.addWidget(self.initial_search_screen)
        self.stacked_widget.addWidget(self.main_screen)

        self._check_for_database()
        self._update_history_display()
        
        self._toggle_clear_button(self.initial_plate_input)
        self._toggle_clear_button(self.main_plate_input)

    # --- פונקציית טוגל לניהול כפתור המחיקה ---
    def _toggle_clear_button(self, line_edit):
        """מציג או מסתיר את כפתור המחיקה בהתאם לטקסט בשדה."""
        action = line_edit.actions()[0] if line_edit.actions() else None
        if action:
            action.setVisible(bool(line_edit.text()))

    def _check_for_database(self):
        if self.db_path and os.path.exists(self.db_path):
            self.db_status_label.setText(f"קובץ בשימוש: {os.path.basename(self.db_path)}")
            self.stacked_widget.setCurrentWidget(self.initial_search_screen)
        else:
            self.stacked_widget.setCurrentWidget(self.setup_screen)

    def _apply_global_styles(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #1e1e2f; color: #e0e0e0; font-family: Arial, sans-serif;
            }
            QLabel { color: #c0c0c0; }
            QPushButton {
                background-color: #3f51b5; color: white; border: none;
                border-radius: 8px; padding: 12px 24px; font-size: 14px; font-weight: bold;
            }
            QPushButton:hover { background-color: #303f9f; }
            QLineEdit {
                background-color: #2a2a45; color: #e0e0e0; border: 1px solid #3f51b5;
                border-radius: 8px; padding: 12px 12px 12px 40px; 
                font-size: 16px;
            }
            QLineEdit:focus { border: 2px solid #5c6bc0; }
            QMessageBox { background-color: #2a2a45; }
            QCompleter QAbstractItemView {
                background-color: #2a2a45; color: #e0e0e0; border: 1px solid #5c6bc0;
                border-radius: 8px; font-size: 14px;
            }
            QCompleter QAbstractItemView::item:hover { background-color: #3f51b5; color: white; }
            QCompleter QAbstractItemView::item:selected { background-color: #303f9f; color: white; }
        """)

    def _setup_completer(self):
        self.completer = QCompleter(self.search_history, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchContains)
        self.initial_plate_input.setCompleter(self.completer)
        self.main_plate_input.setCompleter(self.completer)

    def _show_about_popup(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("אודות")
        msg.setStyleSheet("""
            QMessageBox { background-color: #2a2a45; }
            QLabel { color: #e0e0e0; }
            QPushButton {
                background-color: #3f51b5; color: white; border-radius: 4px; padding: 5px 10px;
            }
        """)
        msg.setText("פותח על ידי @cfopuser ו @איש-אמת")
        msg.exec()

    def _create_setup_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)
        welcome_label = QLabel("ברוכים הבאים לאיתור פרטי רכב")
        welcome_label.setFont(QFont("Arial", 24, QFont.Bold))
        instruction_label = QLabel("כדי להתחיל, יש לטעון את קובץ מסד הנתונים.")
        instruction_label.setFont(QFont("Arial", 14))
        load_button = QPushButton("📂 טען מסד הנתונים")
        load_button.clicked.connect(self._select_db_and_proceed)
        layout.addWidget(welcome_label)
        layout.addWidget(instruction_label)
        layout.addWidget(load_button)
        return widget

    def _create_initial_search_ui(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)

        centered_container = QWidget()
        centered_layout = QVBoxLayout(centered_container)
        centered_layout.setSpacing(15)
        centered_layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel("איתור פרטי רכב")
        title_label.setFont(QFont("Arial", 24, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)

        self.initial_plate_input = QLineEdit()
        self.initial_plate_input.setPlaceholderText("הכניסו את מספר לוחית הרישוי לדוג' 43565502")
        self.initial_plate_input.setFixedWidth(400)
        self.initial_plate_input.setAlignment(Qt.AlignCenter)
        self.initial_plate_input.returnPressed.connect(self._perform_initial_search)
        
        only_int_validator = QIntValidator()
        self.initial_plate_input.setValidator(only_int_validator)

        clear_action_initial = QAction(loaded_icons['delete_icon'], "נקה", self.initial_plate_input)
        clear_action_initial.triggered.connect(self.initial_plate_input.clear)
        self.initial_plate_input.addAction(clear_action_initial, QLineEdit.LeadingPosition)
        self.initial_plate_input.textChanged.connect(lambda: self._toggle_clear_button(self.initial_plate_input))

        # <<< שינוי: החלפת טקסט האמוג'י באייקון חיפוש
        search_button = QPushButton("חפש")
        search_button.setIcon(loaded_icons['search_icon'])
        search_button.setFixedWidth(400)
        search_button.clicked.connect(self._perform_initial_search)

        history_widget = QWidget()
        self.initial_history_layout = QHBoxLayout(history_widget)
        self.initial_history_layout.setContentsMargins(0, 5, 0, 5)
        self.initial_history_layout.setSpacing(10)
        self.initial_history_layout.setAlignment(Qt.AlignCenter)

        centered_layout.addWidget(title_label)
        centered_layout.addWidget(self.initial_plate_input)
        centered_layout.addWidget(history_widget)
        centered_layout.addWidget(search_button)

        main_layout.addWidget(centered_container, 1)

        bottom_row = QFrame()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.addStretch()

        about_button = QPushButton("אודות")
        about_button.setStyleSheet("""
            QPushButton {
                background: none; border: none; color: #5c6bc0;
                font-size: 12px; padding: 5px;
            }
            QPushButton:hover { color: #3f51b5; }
        """)
        about_button.clicked.connect(self._show_about_popup)

        bottom_layout.addWidget(about_button)
        main_layout.addWidget(bottom_row)
        return widget

    def _create_main_ui(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        top_bar_widget = QFrame()
        top_bar_widget.setStyleSheet("background-color: #2a2a45; border-radius: 12px; padding: 8px;")
        top_bar_layout = QHBoxLayout(top_bar_widget)
        self.main_plate_input = QLineEdit()
        self.main_plate_input.setPlaceholderText("הכניסו את מספר לוחית הרישוי לדוג' 43565502")
        self.main_plate_input.returnPressed.connect(self.search_car)
        
        only_int_validator = QIntValidator()
        self.main_plate_input.setValidator(only_int_validator)

        clear_action_main = QAction(loaded_icons['delete_icon'], "נקה", self.main_plate_input)
        clear_action_main.triggered.connect(self.main_plate_input.clear)
        self.main_plate_input.addAction(clear_action_main, QLineEdit.LeadingPosition)
        self.main_plate_input.textChanged.connect(lambda: self._toggle_clear_button(self.main_plate_input))

        # <<< שינוי: החלפת טקסט האמוג'י באייקון חיפוש והוספת Tooltip
        self.search_button = QPushButton()
        self.search_button.setIcon(loaded_icons['search_icon'])
        self.search_button.setFixedSize(50, 46)
        self.search_button.clicked.connect(self.search_car)
        self.search_button.setToolTip("חיפוש") # Tooltip added here!
        
        self.db_status_label = QLabel("לא נטען מסד נתונים.")
        self.db_status_label.setFont(QFont("Arial", 10))

        home_button = QPushButton("חזור")
        home_button.clicked.connect(self._go_to_home)
        change_db_button = QPushButton("החלף קובץ")
        change_db_button.clicked.connect(self._change_db)

        secondary_button_style = """
            QPushButton { background-color: #444a58; color: #e0e0e0; border-radius: 8px;
                          padding: 8px 12px; font-size: 12px; font-weight: bold; }
            QPushButton:hover { background-color: #586175; }
        """
        home_button.setStyleSheet(secondary_button_style)
        change_db_button.setStyleSheet(secondary_button_style)

        top_bar_layout.addWidget(home_button)
        top_bar_layout.addWidget(change_db_button)
        top_bar_layout.addWidget(self.db_status_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.search_button)
        top_bar_layout.addWidget(self.main_plate_input)

        history_widget = QWidget()
        self.main_history_layout = QHBoxLayout(history_widget)
        self.main_history_layout.setContentsMargins(0, 5, 0, 5)
        self.main_history_layout.setSpacing(10)
        self.main_history_layout.setAlignment(Qt.AlignRight)

        results_container = QWidget()
        self.results_container_layout = QVBoxLayout(results_container)
        self.results_container_layout.setContentsMargins(0, 10, 0, 0)
        initial_message = QLabel("תוצאות החיפוש יופיעו כאן...")
        initial_message.setAlignment(Qt.AlignCenter)
        initial_message.setFont(QFont("Arial", 16))
        self.results_container_layout.addWidget(initial_message)

        main_layout.addWidget(top_bar_widget)
        main_layout.addWidget(history_widget)
        main_layout.addWidget(results_container, 1)
        return widget

    def _go_to_home(self):
        self.initial_plate_input.clear()
        self.stacked_widget.setCurrentWidget(self.initial_search_screen)

    def _update_history_display(self):
        for layout in [self.initial_history_layout, self.main_history_layout]:
            if layout is not None:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget(): child.widget().deleteLater()
        
        recent_searches = self.search_history[:HISTORY_DISPLAY_LIMIT]
        btn_style = """
            QPushButton { background-color: #444a58; padding: 6px 12px; 
                          font-size: 12px; border-radius: 12px; }
            QPushButton:hover { background-color: #586175; }
        """
        
        for term in recent_searches:
            btn_initial = QPushButton(term)
            btn_initial.setStyleSheet(btn_style)
            btn_initial.clicked.connect(lambda checked, text=term: self._search_from_initial_history(text))
            self.initial_history_layout.addWidget(btn_initial)
        
        for term in recent_searches:
            btn_main = QPushButton(term)
            btn_main.setStyleSheet(btn_style)
            btn_main.clicked.connect(lambda checked, text=term: self._search_from_main_history(text))
            self.main_history_layout.addWidget(btn_main)
        
        if self.main_history_layout is not None:
             self.main_history_layout.addStretch()

    def _search_from_initial_history(self, plate_number):
        self.initial_plate_input.setText(plate_number)
        self._perform_initial_search()
        
    def _search_from_main_history(self, plate_number):
        self.main_plate_input.setText(plate_number)
        self.search_car()

    def _add_to_history(self, plate_number):
        if plate_number in self.search_history: self.search_history.remove(plate_number)
        self.search_history.insert(0, plate_number)
        self.search_history = self.search_history[:HISTORY_LIMIT]
        self.completer.model().setStringList(self.search_history)
        self.config['search_history'] = self.search_history
        save_config(self.config)
        self._update_history_display()

    def _clear_results_layout(self):
        while self.results_container_layout.count():
            child = self.results_container_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()

    def _select_db_and_proceed(self):
        path, _ = QFileDialog.getOpenFileName(self, "בחר קובץ מסד נתונים", "", "SQLite Database (*.db);;All Files (*)")
        if path:
            self.db_path = path
            self.db_status_label.setText(f"קובץ בשימוש: {os.path.basename(self.db_path)}")
            self.config['last_db_path'] = path
            save_config(self.config)
            self.stacked_widget.setCurrentWidget(self.initial_search_screen)
            self._toggle_clear_button(self.initial_plate_input)
            self._toggle_clear_button(self.main_plate_input)
        elif not self.db_path:
            QMessageBox.warning(self, "לא נבחר קובץ", "יש לבחור קובץ מסד נתונים כדי להמשיך.")

    def _change_db(self):
        current_path = os.path.dirname(self.db_path) if self.db_path else ""
        path, _ = QFileDialog.getOpenFileName(self, "בחר קובץ מסד נתונים חדש", current_path, "SQLite Database (*.db);;All Files (*)")
        if path:
            self.db_path = path
            self.db_status_label.setText(f"קובץ בשימוש: {os.path.basename(self.db_path)}")
            self._clear_results_layout()
            self.config['last_db_path'] = path
            save_config(self.config)
            QMessageBox.information(self, "הצלחה", "מסד הנתונים הוחלף בהצלחה.")

    def _perform_initial_search(self):
        plate_number = self.initial_plate_input.text().strip()
        if not plate_number:
            QMessageBox.warning(self, "קלט חסר", "יש להזין מספר רכב לחיפוש.")
            return
        self.main_plate_input.setText(plate_number)
        self.stacked_widget.setCurrentWidget(self.main_screen)
        self.search_car()

    def search_car(self):
        car_number = self.main_plate_input.text().strip()
        self._clear_results_layout()

        if not self.db_path:
            QMessageBox.critical(self, "שגיאה", "לא נטען קובץ מסד נתונים.")
            self.stacked_widget.setCurrentWidget(self.setup_screen)
            return
        if not car_number:
            QMessageBox.warning(self, "שגיאה", "יש להזין מספר רכב לחיפוש.")
            return
        self._add_to_history(car_number)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cars WHERE mispar_rechev = ?", (car_number,))
            result = cursor.fetchone()
            conn.close()

            if result: self._display_results(result)
            else: QMessageBox.information(self, "לא נמצא", f"לא נמצא רכב עם המספר: {car_number}")
        except sqlite3.Error as e:
            QMessageBox.critical(self, "שגיאת מסד נתונים", f"אירעה שגיאה: {e}")
    
    def _display_results(self, data):
        results_map = {field: value for field, value in zip(COLUMN_NAMES_HEBREW, data)}

        all_content_widget = QWidget()
        all_content_layout = QVBoxLayout(all_content_widget)
        all_content_layout.setSpacing(20)

        for category_title, category_fields in CATEGORIES.items():
            category_cards = []
            for field_name in category_fields:
                value = results_map.get(field_name)
                if value is not None and str(value).strip() != "":
                    card = HoverCard(field_name, value)
                    category_cards.append(card)

            if category_cards:
                title_label = QLabel(category_title)
                title_label.setFont(QFont("Arial", 18, QFont.Bold))
                title_label.setStyleSheet("color: white; margin-bottom: 5px;")
                all_content_layout.addWidget(title_label)

                grid_widget = QWidget()
                grid_layout = QGridLayout(grid_widget)
                grid_layout.setSpacing(15)
                
                col_count = 4
                row, col = 0, 0
                for card in category_cards:
                    grid_layout.addWidget(card, row, col)
                    col += 1
                    if col >= col_count:
                        col = 0; row += 1
                
                all_content_layout.addWidget(grid_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidget(all_content_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background: #1e1e2f; width: 12px; margin: 0px; border-radius: 6px; }
            QScrollBar::handle:vertical { background: #3f51b5; min-height: 24px; border-radius: 6px; }
        """)
        self.results_container_layout.addWidget(scroll_area)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())