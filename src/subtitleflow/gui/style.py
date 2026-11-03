STYLE = """
* { font-family: 'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans CJK SC', sans-serif; font-size: 10pt; }
QMainWindow, QDialog { background: #f4f6fa; }
QWidget#sidebar { background: #101c33; }
QWidget#sidebar QLabel { color: #f2f6ff; }
QWidget#sidebar QPushButton { color: #b9c8e0; background: transparent; border: 0; text-align: left;
 padding: 13px 18px; border-radius: 7px; }
QWidget#sidebar QPushButton:checked { background: #263955; color: white; }
QWidget#sidebar QPushButton:hover { background: #1f304a; }
QLabel#title { font-size: 22pt; font-weight: 600; color: #152742; }
QLabel#muted { color: #63738b; }
QLabel#drop { background: #edf3ff; color: #365991; border: 2px dashed #b7cbed; border-radius: 12px;
 padding: 22px; font-size: 12pt; }
QPushButton { background: white; color: #213550; border: 1px solid #ccd5e3; border-radius: 7px; padding: 9px 15px; }
QPushButton:hover { background: #eaf0fa; border-color: #9dafc7; }
QPushButton:pressed { background: #dce7f7; }
QPushButton:disabled { color: #9ba5b4; background: #edf0f4; border-color: #dde1e8; }
QPushButton#primary { background: #2563eb; color: white; border: 1px solid #2563eb; font-weight: 600; }
QPushButton#primary:hover { background: #1d4ed8; }
QPushButton#primary:disabled { background: #93b0eb; border-color: #93b0eb; }
QLineEdit, QComboBox, QSpinBox { background: white; color: #213550; border: 1px solid #ccd5e3;
 border-radius: 6px; padding: 8px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #2563eb; }
QTableWidget { background: white; alternate-background-color: #f7f9fc; border: 1px solid #dde4ef;
 border-radius: 8px; gridline-color: #edf0f5; selection-background-color: #dbe8ff; selection-color: #12356f; }
QHeaderView::section { background: #edf1f7; color: #52647e; border: 0; padding: 11px; font-weight: 600; }
QProgressBar { border: 0; border-radius: 5px; background: #e0e7f1; min-height: 8px; text-align: center; }
QProgressBar::chunk { background: #2563eb; border-radius: 5px; }
QGroupBox { background: white; border: 1px solid #dce4ef; border-radius: 10px; margin-top: 16px; padding: 18px; }
QGroupBox::title { subcontrol-origin: margin; left: 15px; color: #213550; font-weight: 600; }
QTextBrowser { background: white; border: 1px solid #dce4ef; border-radius: 8px; padding: 15px; }
QCheckBox { spacing: 8px; }
"""
