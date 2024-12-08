import os
import sys

import ffmpeg
from PyQt5.QtCore import QPoint, QProcess, QSize, Qt
from PyQt5.QtGui import QColor, QFont, QIcon, QPalette
from PyQt5.QtWidgets import (QApplication, QFileDialog, QFrame, QHBoxLayout,
                             QLabel, QLineEdit, QMessageBox, QPushButton,
                             QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)


def get_total_frames(input_mp4):
    try:
        probe = ffmpeg.probe(input_mp4)
        video_stream = next(
            (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None)
        if video_stream:
            if 'nb_frames' in video_stream and video_stream['nb_frames'].isdigit():
                return int(video_stream['nb_frames'])
            if 'duration' in video_stream and 'r_frame_rate' in video_stream:
                duration = float(video_stream['duration'])
                num, den = video_stream['r_frame_rate'].split('/')
                fps = float(num) / float(den)
                return int(duration * fps)
    except Exception as e:
        print("Error probing video:", e)
    return None


class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.dragging = False
        self.offset = QPoint(0, 0)

        self.setAutoFillBackground(True)
        p = self.palette()
        p.setColor(QPalette.Window, QColor("#202225"))
        self.setPalette(p)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)

        self.title_label = QLabel("MP4 to WEBM Converter")
        self.title_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        layout.addWidget(self.title_label)
        layout.addItem(QSpacerItem(
            40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        # Minimize Button
        self.min_btn = QPushButton("-")
        self.min_btn.setFixedSize(30, 30)
        self.min_btn.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background-color: #2F3136;
                border: none;
                font-weight: bold;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #3A3C40;
            }
        """)
        self.min_btn.clicked.connect(self.minimize_window)
        layout.addWidget(self.min_btn)

        # Close Button
        self.close_btn = QPushButton("x")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setStyleSheet("""
            QPushButton {
                color: #ffffff;
                background-color: #2F3136;
                border: none;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #D83C3E;
            }
        """)
        self.close_btn.clicked.connect(self.close_window)
        layout.addWidget(self.close_btn)

        self.setLayout(layout)

    def minimize_window(self):
        self.parent().showMinimized()

    def close_window(self):
        self.parent().close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = event.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.parent().move(self.parent().pos() + event.pos() - self.offset)

    def mouseReleaseEvent(self, event):
        self.dragging = False


class ConverterGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint |
                            Qt.WindowSystemMenuHint | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setWindowTitle("MP4 to WEBM Converter")
        self.setMinimumSize(QSize(600, 250))

        self.input_file_path = ""
        self.total_frames = None
        self.ffmpeg_process = QProcess(self)
        self.current_frame = 0

        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # Main content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        input_layout = QHBoxLayout()
        self.input_label = QLabel("Input MP4:")
        self.input_lineedit = QLineEdit()
        self.input_lineedit.setPlaceholderText("Select an MP4 file")
        self.input_browse_btn = QPushButton("Browse...")
        self.input_browse_btn.clicked.connect(self.browse_input_file)
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_lineedit)
        input_layout.addWidget(self.input_browse_btn)

        output_layout = QHBoxLayout()
        self.output_label = QLabel("Output Name:")
        self.output_lineedit = QLineEdit()
        self.output_lineedit.setPlaceholderText(
            "Leave blank to use input name")
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_lineedit)

        bitrate_layout = QHBoxLayout()
        self.bitrate_label = QLabel("Bitrate:")
        self.bitrate_lineedit = QLineEdit()
        self.bitrate_lineedit.setText("1000")
        bitrate_layout.addWidget(self.bitrate_label)
        bitrate_layout.addWidget(self.bitrate_lineedit)

        self.convert_button = QPushButton("Convert")
        self.convert_button.setFixedHeight(40)
        self.convert_button.clicked.connect(self.start_conversion)
        self.set_button_progress(0)

        content_layout.addLayout(input_layout)
        content_layout.addLayout(output_layout)
        content_layout.addLayout(bitrate_layout)
        content_layout.addWidget(self.convert_button, alignment=Qt.AlignCenter)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        self.setLayout(main_layout)

        self.ffmpeg_process.readyReadStandardOutput.connect(
            self.read_ffmpeg_output)
        self.ffmpeg_process.finished.connect(self.ffmpeg_finished)

        # Apply dark theme colors
        self.apply_dark_theme()

    def apply_dark_theme(self):
        dark_bg = "#2F3136"
        dark_bg_alt = "#36393F"
        text_color = "#FFFFFF"
        disabled_text_color = "#AAAAAA"

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(dark_bg))
        palette.setColor(QPalette.WindowText, QColor(text_color))
        palette.setColor(QPalette.Base, QColor(dark_bg_alt))
        palette.setColor(QPalette.AlternateBase, QColor(dark_bg))
        palette.setColor(QPalette.ToolTipBase, QColor(text_color))
        palette.setColor(QPalette.ToolTipText, QColor(text_color))
        palette.setColor(QPalette.Text, QColor(text_color))
        palette.setColor(QPalette.Button, QColor(dark_bg_alt))
        palette.setColor(QPalette.ButtonText, QColor(text_color))
        palette.setColor(QPalette.Disabled, QPalette.Text,
                         QColor(disabled_text_color))
        palette.setColor(QPalette.Disabled, QPalette.ButtonText,
                         QColor(disabled_text_color))
        palette.setColor(QPalette.Highlight, QColor("#3ba55d"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        self.setPalette(palette)

        self.setStyleSheet("""
            QWidget {
                background-color: #2F3136;
                color: #FFFFFF;
            }
            QLineEdit {
                background-color: #36393F;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton {
                background-color: #36393F;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 6px;
            }
            QPushButton:hover {
                border: 1px solid #3ba55d;
            }
            QLabel {
                color: #FFFFFF;
            }
            QMessageBox {
                background-color: #2F3136;
            }
        """)

    def browse_input_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select MP4 file", "", "MP4 files (*.mp4)")
        if file_name:
            self.input_lineedit.setText(file_name)
            self.input_file_path = file_name

    def start_conversion(self):
        input_mp4 = self.input_lineedit.text().strip()
        output_name = self.output_lineedit.text().strip()
        bitrate = self.bitrate_lineedit.text().strip()

        if not input_mp4 or not os.path.isfile(input_mp4):
            QMessageBox.warning(
                self, "Error", "Please select a valid input MP4 file.")
            return

        if not output_name:
            base_name = os.path.splitext(os.path.basename(input_mp4))[0]
            output_name = base_name + ".webm"
        else:
            if not output_name.lower().endswith(".webm"):
                output_name += ".webm"

        if os.path.exists(output_name):
            overwrite = QMessageBox.question(
                self,
                "File Exists",
                f"The file '{output_name}' already exists. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if overwrite != QMessageBox.Yes:
                return  # User chose not to overwrite

        # Ensure bitrate input is in the correct format
        if not bitrate.isdigit():
            QMessageBox.warning(
                self, "Error", "Please enter a valid bitrate in kilobits (e.g., 1000).")
            return

        bitrate += "k"  # Append 'k' for FFmpeg input

        self.total_frames = get_total_frames(input_mp4)
        self.current_frame = 0
        self.convert_button.setEnabled(False)
        self.convert_button.setText("Converting...")
        self.set_button_progress(0)

        cmd = [
            'ffmpeg',
            '-y',  # Automatically overwrite existing files
            '-i', input_mp4,
            '-c:v', 'libvpx-vp9',
            '-b:v', bitrate,
            '-speed', '5',
            '-threads', '24',
            '-tile-columns', '2',
            '-tile-rows', '1',
            '-progress', 'pipe:1',
            '-loglevel', 'error',
            output_name
        ]

        self.ffmpeg_process.setProcessChannelMode(QProcess.MergedChannels)
        self.ffmpeg_process.start(cmd[0], cmd[1:])

    def read_ffmpeg_output(self):
        while self.ffmpeg_process.canReadLine():
            line = self.ffmpeg_process.readLine().data().decode(
                'utf-8', errors='replace').strip()
            if line.startswith('frame='):
                parts = line.split('=')
                if len(parts) == 2:
                    try:
                        self.current_frame = int(parts[1].strip())
                        self.update_button_progress()
                    except ValueError:
                        pass

    def update_button_progress(self):
        if self.total_frames and self.total_frames > 0:
            progress = int((self.current_frame / self.total_frames) * 100)
            self.convert_button.setText(f"Converting... {progress}%")
            self.set_button_progress(progress)
        else:
            self.convert_button.setText(
                f"Converting... frame {self.current_frame}")

    def set_button_progress(self, percentage):
        dark_bg = "#2F3136"
        green_accent = "#3ba55d"

        self.convert_button.setStyleSheet(f"""
            QPushButton {{
                color: #ffffff;
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {green_accent},
                    stop:{percentage/100.0} {green_accent},
                    stop:{percentage/100.0} {dark_bg},
                    stop:1 {dark_bg}
                );
            }}
            QPushButton:disabled {{
                color: #aaaaaa;
            }}
        """)

    def ffmpeg_finished(self, exit_code, exit_status):
        self.convert_button.setEnabled(True)
        if exit_code == 0:
            self.convert_button.setText("Done!")
            self.set_button_progress(100)
            QMessageBox.information(
                self, "Success", "Conversion completed successfully!")
        else:
            self.convert_button.setText("Convert")
            self.set_button_progress(0)
            QMessageBox.critical(
                self, "Error", "FFmpeg encountered an error. Check the console for details.")


def main():
    app = QApplication(sys.argv)
    window = ConverterGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
