# WorkTwins.py

from datetime import datetime
import json
import os
import sys
import threading
import logging
from PyQt5.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QAction, QMessageBox, QWidget,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QFileDialog, QSpinBox,
    QHBoxLayout, QCheckBox, QGridLayout, QProgressBar
)
from PyQt5.QtGui import QIcon, QPixmap, QMovie
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QObject
from com_worktwins_data_sources.GitHubDataSource import GitHubDataSource
from com_worktwins_data_sources.GitLabDataSource import GitLabDataSource
from com_worktwins_data_sources.LocalFoldersDataSource import LocalFoldersDataSource

# Configure logging
logging.basicConfig(
    filename='worktwins.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class WorkerSignals(QObject):
    github_progress = pyqtSignal(int)
    gitlab_progress = pyqtSignal(int)
    local_folder_progress = pyqtSignal(int)
    knowledgehooks_progress = pyqtSignal(int)

class DataSourceWorker(threading.Thread):
    def __init__(self, data_source, signals):
        threading.Thread.__init__(self)
        self.data_source = data_source
        self.signals = signals

    def run(self):
        try:
            # Fetch data
            self.data_source.fetch_data()
            # Generate JSON report
            self.data_source.generate_json_report(output_path=None, print_console=True)
            # Generate PDF report
            pdf_output_path = os.path.join(self.data_source.reports_dir, f"report_{self.data_source.data_source_name}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf")
            self.data_source.generate_pdf_report(overall_summary=self.collect_overall_summary(), pdf_output_path=pdf_output_path)
            logging.info(f"Reports generated for data source: {self.data_source.data_source_name}")
        except Exception as e:
            logging.error(f"Error in DataSourceWorker for {self.data_source.data_source_name}: {e}")

    def collect_overall_summary(self):
        # This method should collect the overall summary from the JSON report
        # Assuming generate_json_report saves it, read the latest JSON report
        try:
            latest_json = max([f for f in os.listdir(self.data_source.reports_dir) if f.endswith('.json') and f.startswith(f"report_{self.data_source.data_source_name}_")],
                             key=lambda x: os.path.getmtime(os.path.join(self.data_source.reports_dir, x)))
            json_path = os.path.join(self.data_source.reports_dir, latest_json)
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to collect overall summary for {self.data_source.data_source_name}: {e}")
            return {}

class WorkTwinsApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.tray_icon = QSystemTrayIcon(QIcon("com_worktwins_images/worktwins_play.ico"))  # Corrected path

        # State variable to track whether the app is in "start" (playing) or "stop" mode
        self.is_playing = False  # Start in "stop" mode

        # Create the menu
        self.menu = QMenu()

        # Create actions for the menu
        self.snapshot_action = QAction("Snapshot")
        self.about_action = QAction("About")
        self.exit_action = QAction("Exit")
        self.start_action = QAction("Start Work FootPrint Generation")

        # Connect actions to their slots
        self.snapshot_action.triggered.connect(self.snapshot)
        self.about_action.triggered.connect(self.about)
        self.exit_action.triggered.connect(self.exit)
        self.start_action.triggered.connect(self.toggle_start_stop)

        # Add actions to the menu
        self.menu.addAction(self.snapshot_action)
        self.menu.addSeparator()
        self.menu.addAction(self.about_action)
        self.menu.addSeparator()
        self.menu.addAction(self.start_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        # Set the menu to the tray icon
        self.tray_icon.setContextMenu(self.menu)

        # Connect the tray icon click event to a function
        self.tray_icon.activated.connect(self.toggle_icon)

        # Show the tray icon
        self.tray_icon.show()

        # Show the data source configuration window
        self.show_data_source_window()

        # Initialize worker signals
        self.signals = WorkerSignals()
        self.signals.github_progress.connect(self.github_progress_callback)
        self.signals.gitlab_progress.connect(self.gitlab_progress_callback)
        self.signals.local_folder_progress.connect(self.local_folder_progress_callback)
        self.signals.knowledgehooks_progress.connect(self.knowledgehooks_progress_callback)

    def show_data_source_window(self):
        self.config_window = QWidget()
        self.config_window.setStyleSheet("background-color: #0b0402;")
        self.config_window.setWindowTitle("Set Data Sources")
        self.config_window.setGeometry(100, 100, 600, 700)

        layout = QVBoxLayout()
        grid_layout = QGridLayout()

        # Add image to the top of the window
        image_label = QLabel()
        pixmap = QPixmap("com_worktwins_images/worktwins.png")
        if pixmap.isNull():
            logging.warning("Image 'com_worktwins_images/worktwins.png' not found or is invalid.")
            print("Warning: 'com_worktwins_images/worktwins.png' not found or is invalid.")
        else:
            pixmap = pixmap.scaled(int(pixmap.width() * 0.4), int(pixmap.height() * 0.4))
            image_label.setPixmap(pixmap)
        layout.addWidget(image_label)

        # Add circular profile picture to the top right of the image
        profile_label = QLabel(image_label)
        profile_pixmap = QPixmap("com_worktwins_images/profile.jpg")
        if profile_pixmap.isNull():
            logging.warning("Image 'com_worktwins_images/profile.jpg' not found or is invalid.")
            print("Warning: 'com_worktwins_images/profile.jpg' not found or is invalid.")
        else:
            profile_pixmap = profile_pixmap.scaled(100, 100, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation).copy(0, 0, 100, 100)
            profile_label.setPixmap(profile_pixmap)
            profile_label.setFixedSize(100, 100)
            profile_label.setStyleSheet("border-radius: 50px; border: 2px solid #000; overflow: hidden; background-color: white;")
            profile_label.setParent(image_label)
            profile_label.move(image_label.width() - profile_label.width(), 10)
            profile_label.raise_()

        # GitHub username input with checkbox
        self.github_checkbox = QCheckBox()
        self.github_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: black;
                border: 1px solid black;
            }
        """)
        self.github_checkbox.stateChanged.connect(self.toggle_github_input)
        self.github_username_input = QLineEdit()
        self.github_username_input.mousePressEvent = self.enable_github_checkbox
        self.github_username_input.setEnabled(False)
        self.github_username_input.setStyleSheet("font-size: 15pt; background-color: gray;")

        github_label = QLabel("GitHub Username:")
        github_label.mousePressEvent = lambda event: self.github_checkbox.setChecked(not self.github_checkbox.isChecked())
        github_label.setStyleSheet("font-size: 15pt; color: white;")

        grid_layout.addWidget(self.github_checkbox, 0, 0)
        grid_layout.addWidget(github_label, 0, 1)
        grid_layout.addWidget(self.github_username_input, 0, 2)

        # # GitLab username input with checkbox
        # self.gitlab_checkbox = QCheckBox()
        # self.gitlab_checkbox.setStyleSheet("""
        #     QCheckBox::indicator {
        #         width: 20px;
        #         height: 20px;
        #     }
        #     QCheckBox::indicator:checked {
        #         background-color: black;
        #         border: 1px solid black;
        #     }
        # """)
        # self.gitlab_checkbox.stateChanged.connect(self.toggle_gitlab_input)
        # self.gitlab_username_input = QLineEdit()
        # self.gitlab_username_input.mousePressEvent = self.enable_gitlab_checkbox
        # self.gitlab_username_input.setEnabled(False)
        # self.gitlab_username_input.setStyleSheet("font-size: 15pt; background-color: gray;")

        # gitlab_label = QLabel("GitLab Username:")
        # gitlab_label.mousePressEvent = lambda event: self.gitlab_checkbox.setChecked(not self.gitlab_checkbox.isChecked())
        # gitlab_label.setStyleSheet("font-size: 15pt; color: white;")

        # grid_layout.addWidget(self.gitlab_checkbox, 1, 0)
        # grid_layout.addWidget(gitlab_label, 1, 1)
        # grid_layout.addWidget(self.gitlab_username_input, 1, 2)

        # Local Projects Folder selection with checkbox
        self.local_folder_checkbox = QCheckBox()
        self.local_folder_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: black;
                border: 1px solid black;
            }
        """)
        self.local_folder_checkbox.stateChanged.connect(self.toggle_local_folder_input)

        folder_selection_layout = QHBoxLayout()
        folder_icon_label = QLabel()
        folder_pixmap = QPixmap("com_worktwins_images/folder_icon.png")  # Ensure this image exists
        if folder_pixmap.isNull():
            logging.warning("Image 'com_worktwins_images/folder_icon.png' not found or is invalid.")
            print("Warning: 'com_worktwins_images/folder_icon.png' not found or is invalid.")
        else:
            folder_pixmap = folder_pixmap.scaled(30, 30)
            folder_icon_label.setPixmap(folder_pixmap)
        folder_selection_layout.addWidget(folder_icon_label)

        folder_label = QLabel("Select Project Folder")
        folder_label.mousePressEvent = lambda event: self.local_folder_checkbox.setChecked(not self.local_folder_checkbox.isChecked())
        folder_label.setStyleSheet("font-size: 15pt; color: white;")
        folder_selection_layout.addWidget(folder_label)

        self.local_folder_button = QPushButton("Select Folder")
        self.local_folder_button.setStyleSheet("""
            QPushButton {
                font-size: 15pt;
                color: gray;
                background-color: #444;
                border: 1px solid #666;
                padding: 5px 10px;
            }
            QPushButton:enabled {
                color: white;
            }
        """)
        self.local_folder_button.setEnabled(False)
        self.local_folder_button.clicked.connect(self.select_local_folder)
        self.local_folder_path_label = QLabel("Not selected")
        self.local_folder_path_label.setStyleSheet("font-size: 15pt; color: white;")

        grid_layout.addWidget(self.local_folder_checkbox, 2, 0)
        grid_layout.addLayout(folder_selection_layout, 2, 1)
        grid_layout.addWidget(self.local_folder_button, 2, 2)
        grid_layout.addWidget(self.local_folder_path_label, 3, 1, 1, 2)

        # KnowledgeHooks configuration with checkbox
        self.knowledgehooks_checkbox = QCheckBox()
        self.knowledgehooks_checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
            QCheckBox::indicator:checked {
                background-color: black;
                border: 1px solid black;
            }
        """)
        self.knowledgehooks_checkbox.stateChanged.connect(self.toggle_knowledgehooks_input)
        self.refresh_rate_input = QSpinBox()
        self.refresh_rate_input.mousePressEvent = self.enable_knowledgehooks_checkbox
        self.refresh_rate_input.setEnabled(False)
        self.refresh_rate_input.setStyleSheet("font-size: 15pt; background-color: gray;")
        self.refresh_rate_input.setMinimum(1)
        self.refresh_rate_input.setMaximum(60)
        self.refresh_rate_input.setSuffix(" min")

        knowledgehooks_label = QLabel("KnowledgeHooks Refresh Rate:")
        knowledgehooks_label.mousePressEvent = lambda event: self.knowledgehooks_checkbox.setChecked(not self.knowledgehooks_checkbox.isChecked())
        knowledgehooks_label.setStyleSheet("font-size: 15pt; color: white;")

        grid_layout.addWidget(self.knowledgehooks_checkbox, 4, 0)
        grid_layout.addWidget(knowledgehooks_label, 4, 1)
        grid_layout.addWidget(self.refresh_rate_input, 4, 2)

        # Start button with image inside
        self.start_button = QPushButton()
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #3d281a;
                color: white;
                font-size: 20pt;
                border: none;
                padding-left: 10px;
            }
            QPushButton:hover {
                background-color: #5a3d25;
            }
        """)
        self.start_button.setFixedSize(400, 120)  # Set the button size to fit the text and image
        start_button_layout = QHBoxLayout()

        self.start_button_text = QLabel("Start Work\nFootPrint Generation")
        self.start_button_text.setStyleSheet("color: white; font-size: 20pt;")
        self.start_button_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.footprint_pixmap = QPixmap("com_worktwins_images/feature_footprint.png")
        if self.footprint_pixmap.isNull():
            logging.warning("Image 'com_worktwins_images/feature_footprint.png' not found or is invalid.")
            print("Warning: 'com_worktwins_images/feature_footprint.png' not found or is invalid.")
        else:
            self.footprint_pixmap = self.footprint_pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.footprint_label = QLabel()
            self.footprint_label.setPixmap(self.footprint_pixmap)
            self.footprint_label.setFixedSize(100, 100)

        start_button_layout.addWidget(self.start_button_text)
        if hasattr(self, 'footprint_label'):
            start_button_layout.addWidget(self.footprint_label)
        start_button_layout.setContentsMargins(0, 0, 0, 0)
        start_button_layout.setSpacing(10)
        start_button_layout.setAlignment(Qt.AlignLeft)  # Align text to the left
        self.start_button.setLayout(start_button_layout)
        self.start_button.clicked.connect(self.toggle_start_stop)

        layout.addLayout(grid_layout)
        layout.addWidget(self.start_button, alignment=Qt.AlignRight)

        self.config_window.setLayout(layout)
        self.config_window.show()

    def enable_github_checkbox(self, event):
        self.github_checkbox.setChecked(True)
        QLineEdit.mousePressEvent(self.github_username_input, event)

    def enable_gitlab_checkbox(self, event):
        self.gitlab_checkbox.setChecked(True)
        QLineEdit.mousePressEvent(self.gitlab_username_input, event)

    def enable_knowledgehooks_checkbox(self, event):
        self.knowledgehooks_checkbox.setChecked(True)
        QSpinBox.mousePressEvent(self.refresh_rate_input, event)

    def toggle_github_input(self, state):
        self.github_username_input.setEnabled(state == Qt.Checked)
        self.github_username_input.setStyleSheet("font-size: 15pt; background-color: white;" if state == Qt.Checked else "font-size: 15pt; background-color: gray;")

    def toggle_gitlab_input(self, state):
        self.gitlab_username_input.setEnabled(state == Qt.Checked)
        self.gitlab_username_input.setStyleSheet("font-size: 15pt; background-color: white;" if state == Qt.Checked else "font-size: 15pt; background-color: gray;")

    def toggle_local_folder_input(self, state):
        self.local_folder_button.setEnabled(state == Qt.Checked)
        self.local_folder_button.setStyleSheet("font-size: 15pt; color: white;" if state == Qt.Checked else "font-size: 15pt; color: gray;")

    def select_local_folder(self):
        folder = QFileDialog.getExistingDirectory(None, "Select Local Projects Folder")
        if folder:
            self.local_folder_path_label.setText(folder)
            logging.info(f"Selected local projects folder: {folder}")

    def toggle_knowledgehooks_input(self, state):
        self.refresh_rate_input.setEnabled(state == Qt.Checked)
        self.refresh_rate_input.setStyleSheet("font-size: 15pt; background-color: white;" if state == Qt.Checked else "font-size: 15pt; background-color: gray;")

    def toggle_start_stop(self):
        if self.is_playing:
            self.stop()
        else:
            self.start(
                github_username=self.github_username_input.text() if self.github_checkbox.isChecked() else None,
                gitlab_username=self.gitlab_username_input.text() if self.gitlab_checkbox.isChecked() else None,
                local_folder=self.local_folder_path_label.text() if self.local_folder_checkbox.isChecked() else None,
                refresh_rate=self.refresh_rate_input.value() if self.knowledgehooks_checkbox.isChecked() else None
            )

    def start(self, github_username=None, gitlab_username=None, local_folder=None, refresh_rate=None):
        # Change button text and image to indicate "Stop" state
        self.start_button_text.setText("Stop")
        if hasattr(self, 'footprint_label') and not self.footprint_pixmap.isNull():
            footprint_movie = QMovie("com_worktwins_images/footprint.gif")
            if footprint_movie.isValid():
                footprint_movie.setScaledSize(QSize(100, 100))  # Adjust the size of the GIF
                self.footprint_label.setMovie(footprint_movie)
                footprint_movie.start()
                self.footprint_movie = footprint_movie  # Keep a reference to prevent garbage collection
            else:
                logging.warning("Image 'com_worktwins_images/footprint.gif' not found or is invalid.")
                print("Warning: 'com_worktwins_images/footprint.gif' not found or is invalid.")

        # Add 'Process Progress' label above all progress bars
        if not hasattr(self, 'process_progress_label'):
            self.process_progress_label = QLabel("Process Progress")
            self.process_progress_label.setStyleSheet("font-size: 18pt; color: white;")
            self.config_window.layout().insertWidget(self.config_window.layout().count() - 1, self.process_progress_label)

        # Create progress bars for each selected option
        if not hasattr(self, 'progress_layout'):
            self.progress_layout = QVBoxLayout()
            self.config_window.layout().insertLayout(self.config_window.layout().count() - 1, self.progress_layout)
            self.config_window.adjustSize()

        if github_username:
            github_progress_label = QLabel("GitHub Username Progress:")
            github_progress_label.setStyleSheet("font-size: 15pt; color: white;")
            github_progress = QProgressBar()
            github_progress.setValue(0)
            github_progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: green;
                    width: 20px;
                }
            """)
            self.progress_layout.addWidget(github_progress_label)
            self.progress_layout.addWidget(github_progress)
            self.github_progress = github_progress

        if gitlab_username:
            gitlab_progress_label = QLabel("GitLab Username Progress:")
            gitlab_progress_label.setStyleSheet("font-size: 15pt; color: white;")
            gitlab_progress = QProgressBar()
            gitlab_progress.setValue(0)
            gitlab_progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: green;
                    width: 20px;
                }
            """)
            self.progress_layout.addWidget(gitlab_progress_label)
            self.progress_layout.addWidget(gitlab_progress)
            self.gitlab_progress = gitlab_progress

        if local_folder:
            local_folder_progress_label = QLabel("Local Projects Folder Progress:")
            local_folder_progress_label.setStyleSheet("font-size: 15pt; color: white;")
            local_folder_progress = QProgressBar()
            local_folder_progress.setValue(0)
            local_folder_progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: green;
                    width: 20px;
                }
            """)
            self.progress_layout.addWidget(local_folder_progress_label)
            self.progress_layout.addWidget(local_folder_progress)
            self.local_folder_progress = local_folder_progress

        if refresh_rate:
            knowledgehooks_progress_label = QLabel("KnowledgeHooks Progress:")
            knowledgehooks_progress_label.setStyleSheet("font-size: 15pt; color: white;")
            knowledgehooks_progress = QProgressBar()
            knowledgehooks_progress.setValue(0)
            knowledgehooks_progress.setStyleSheet("""
                QProgressBar {
                    border: 2px solid grey;
                    border-radius: 5px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: green;
                    width: 20px;
                }
            """)
            self.progress_layout.addWidget(knowledgehooks_progress_label)
            self.progress_layout.addWidget(knowledgehooks_progress)
            self.knowledgehooks_progress = knowledgehooks_progress

        self.config_window.adjustSize()

        # Start the data sources
        workers = []
        if github_username:
            source_code_dir = 'com_worktwins_data_github'
            github_data_source = GitHubDataSource(
                usernames=[github_username],
                source_code_dir=source_code_dir,
                progress_callback=self.signals.github_progress.emit,
                compress=0,
                amount_of_chunks=0,
                size_of_chunk=0
            )
            self.github_worker = DataSourceWorker(github_data_source, self.signals)
            self.github_worker.start()
            workers.append(self.github_worker)
            logging.info(f"Started GitHub data source worker for user: {github_username}")

        if gitlab_username:
            source_code_dir = 'com_worktwins_data_gitlab'
            gitlab_data_source = GitLabDataSource(
                usernames=[gitlab_username],
                source_code_dir=source_code_dir,
                progress_callback=self.signals.gitlab_progress.emit,
                compress=0,
                amount_of_chunks=0,
                size_of_chunk=0
            )
            self.gitlab_worker = DataSourceWorker(gitlab_data_source, self.signals)
            self.gitlab_worker.start()
            workers.append(self.gitlab_worker)
            logging.info(f"Started GitLab data source worker for user: {gitlab_username}")

        if local_folder:
            local_folder_data_source = LocalFoldersDataSource(
                source_code_dir=local_folder,
                progress_callback=self.signals.local_folder_progress.emit,
                compress=0,
                amount_of_chunks=0,
                size_of_chunk=0
            )
            self.local_folder_worker = DataSourceWorker(local_folder_data_source, self.signals)
            self.local_folder_worker.start()
            workers.append(self.local_folder_worker)
            logging.info(f"Started Local Folders data source worker for folder: {local_folder}")

        if refresh_rate:
            # Implement KnowledgeHooksDataSource when ready
            logging.info("KnowledgeHooks feature is not yet implemented.")
            print("KnowledgeHooks feature is not yet implemented.")

        print("Work FootPrint Generation started")
        logging.info("Work FootPrint Generation started")
        logging.info(f"GitHub Username: {github_username}")
        logging.info(f"GitLab Username: {gitlab_username}")
        logging.info(f"Local Projects Folder: {local_folder}")
        logging.info(f"KnowledgeHooks Refresh Rate: {refresh_rate}")

        self.is_playing = True

    def stop(self):
        # Change button text and image back to "Start" state
        self.start_button_text.setText("Start Work\nFootPrint Generation")
        if hasattr(self, 'footprint_pixmap') and not self.footprint_pixmap.isNull():
            self.footprint_label.setPixmap(self.footprint_pixmap)
        if hasattr(self, 'footprint_movie'):
            self.footprint_movie.stop()

        print("Work FootPrint Generation stopped")
        logging.info("Work FootPrint Generation stopped")
        self.is_playing = False

    def github_progress_callback(self, progress_value):
        if hasattr(self, 'github_progress'):
            self.github_progress.setValue(progress_value)
            logging.debug(f"GitHub Progress: {progress_value}%")

    def gitlab_progress_callback(self, progress_value):
        if hasattr(self, 'gitlab_progress'):
            self.gitlab_progress.setValue(progress_value)
            logging.debug(f"GitLab Progress: {progress_value}%")

    def local_folder_progress_callback(self, progress_value):
        if hasattr(self, 'local_folder_progress'):
            self.local_folder_progress.setValue(progress_value)
            logging.debug(f"Local Folder Progress: {progress_value}%")

    def knowledgehooks_progress_callback(self, progress_value):
        if hasattr(self, 'knowledgehooks_progress'):
            self.knowledgehooks_progress.setValue(progress_value)
            logging.debug(f"KnowledgeHooks Progress: {progress_value}%")

    def toggle_icon(self, reason):
        if reason == QSystemTrayIcon.Trigger:  # This checks if the icon was clicked
            if self.is_playing:
                self.tray_icon.setIcon(QIcon("com_worktwins_images/worktwins_play.ico"))
                logging.info("Switched to play icon")
                print("Switched to play icon")
            else:
                self.tray_icon.setIcon(QIcon("com_worktwins_images/worktwins_stop.ico"))
                logging.info("Switched to stop icon")
                print("Switched to stop icon")

            # Toggle the state
            self.is_playing = not self.is_playing

    def snapshot(self):
        logging.info("Snapshot action triggered")
        print("Snapshot action triggered")
        # Add your snapshot logic here
        # This could involve generating snapshots independently of the main process

    def about(self):
        QMessageBox.information(None, "About WorkTwins", "WorkTwins is a PyQt5 system tray application.")
        logging.info("About dialog opened")

    def exit(self):
        logging.info("Exiting WorkTwins application")
        QApplication.quit()

    def run(self):
        sys.exit(self.app.exec_())

if __name__ == "__main__":
    app = WorkTwinsApp()
    app.run()
