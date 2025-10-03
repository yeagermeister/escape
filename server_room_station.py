import sys
import socketio
import pygame
import os
import random
from threading import Thread, Event
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

class ServerSignals(QObject):
    transmission_verifying = pyqtSignal()
    transmission_success = pyqtSignal()
    transmission_failed = pyqtSignal(str)
    show_abort = pyqtSignal()
    abort_success = pyqtSignal()
    abort_reset = pyqtSignal()
    play_audio = pyqtSignal(str)
    game_reset = pyqtSignal()

class ServerRoomStation(QWidget):
    def __init__(self, server_url):
        super().__init__()
        self.signals = ServerSignals()
        self.signals.transmission_verifying.connect(self.show_verifying)
        self.signals.transmission_success.connect(self.show_self_destruct)
        self.signals.transmission_failed.connect(self.show_failure)
        self.signals.show_abort.connect(self.show_abort_button)
        self.signals.abort_success.connect(self.show_success)
        self.signals.abort_reset.connect(self.reset_abort_button)
        self.signals.play_audio.connect(self.play_sound)
        self.signals.game_reset.connect(self.reset_station)
        
        self.init_audio()
        self.initUI()
        self.setup_socketio(server_url)
        self.start_random_sounds()
    
    def init_audio(self):
        """Initialize pygame mixer for audio"""
        pygame.mixer.init()
        self.audio_path = 'audio/'  # Create this folder and add audio files
        self.stop_sounds = Event()
    
    def initUI(self):
        self.setWindowTitle('Server Room Terminal')
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Title
        self.title_label = QLabel('SERVER CONTROL TERMINAL', self)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("color: #00ff00;")
        title_font = QFont('Courier New', 50, QFont.Bold)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        
        # Instructions
        self.instruction_label = QLabel('ENTER SHUTDOWN CODE:', self)
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("color: #00ff00;")
        inst_font = QFont('Courier New', 30)
        self.instruction_label.setFont(inst_font)
        layout.addWidget(self.instruction_label)
        
        # Code input
        self.code_input = QLineEdit(self)
        self.code_input.setAlignment(Qt.AlignCenter)
        self.code_input.setStyleSheet("""
            QLineEdit {
                background-color: #003300;
                color: #00ff00;
                font-size: 50px;
                padding: 20px;
                border: 3px solid #00ff00;
                font-family: 'Courier New';
            }
        """)
        self.code_input.setMaxLength(20)
        self.code_input.returnPressed.connect(self.submit_code)
        layout.addWidget(self.code_input)
        
        # Submit button
        self.submit_button = QPushButton('SUBMIT', self)
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff00;
                font-size: 40px;
                font-weight: bold;
                padding: 20px 50px;
                border: 3px solid #00ff00;
                border-radius: 10px;
                font-family: 'Courier New';
            }
            QPushButton:hover {
                background-color: #00ff00;
                color: black;
            }
        """)
        self.submit_button.clicked.connect(self.submit_code)
        layout.addWidget(self.submit_button)
        
        # Status message
        self.status_label = QLabel('', self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #ffaa00;")
        self.status_label.setWordWrap(True)
        status_font = QFont('Courier New', 25)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)
        
        # Abort button (hidden initially)
        self.abort_button = QPushButton('ABORT SELF-DESTRUCT', self)
        self.abort_button.setStyleSheet("""
            QPushButton {
                background-color: #ff0000;
                color: white;
                font-size: 60px;
                font-weight: bold;
                padding: 50px;
                border: 5px solid #fff;
                border-radius: 20px;
            }
            QPushButton:hover {
                background-color: #cc0000;
            }
            QPushButton:pressed {
                background-color: #990000;
            }
        """)
        self.abort_button.clicked.connect(self.press_abort_button)
        self.abort_button.hide()
        layout.addWidget(self.abort_button)
        
        self.setLayout(layout)
    
    def setup_socketio(self, server_url):
        self.sio = socketio.Client()
        
        @self.sio.on('connect')
        def on_connect():
            print('Server room station connected')
        
        @self.sio.on('transmission_verifying')
        def on_verifying(data):
            self.signals.transmission_verifying.emit()
        
        @self.sio.on('transmission_shutdown')
        def on_transmission_shutdown(data):
            if data.get('success'):
                self.signals.transmission_success.emit()
                self.signals.show_abort.emit()
            else:
                message = data.get('message', 'INVALID CODE')
                self.signals.transmission_failed.emit(message)
        
        @self.sio.on('self_destruct_aborted')
        def on_aborted(data):
            self.signals.abort_success.emit()
        
        @self.sio.on('game_reset')
        def on_reset(data):
            self.signals.game_reset.emit()
        
        @self.sio.on('timer_stopped')
        def on_stopped(data):
            self.signals.game_reset.emit()
        
        @self.sio.on('abort_failed_full_reset')
        def on_abort_failed_full_reset(data):
            self.signals.game_reset.emit()
        
        @self.sio.on('play_audio')
        def on_play_audio(data):
            clip = data.get('clip')
            self.signals.play_audio.emit(clip)
        
        try:
            self.sio.connect(server_url)
        except Exception as e:
            print(f"Connection error: {e}")
    
    def submit_code(self):
        code = self.code_input.text()
        if not code:
            return
        
        print(f"Submitting code: {code}")
        self.sio.emit('check_transmission_code', {'code': code})
        self.code_input.setEnabled(False)
        self.submit_button.setEnabled(False)
    
    def show_verifying(self):
        self.status_label.setText('VERIFYING CODE...')
        self.status_label.setStyleSheet("color: #ffaa00;")
    
    def show_failure(self, message):
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: #ff0000;")
        self.code_input.clear()
        
        # Re-enable input after 3 seconds
        QTimer.singleShot(3000, self.reset_input)
    
    def reset_input(self):
        self.code_input.setEnabled(True)
        self.submit_button.setEnabled(True)
        self.status_label.setText('')
        self.code_input.setFocus()
    
    def show_self_destruct(self):
        self.title_label.setText('⚠️ TRANSMISSION SHUT DOWN ⚠️')
        self.title_label.setStyleSheet("color: #ff0000;")
        self.instruction_label.setText('SELF-DESTRUCT SEQUENCE INITIATED!')
        self.instruction_label.setStyleSheet("color: #ff0000;")
        self.code_input.hide()
        self.submit_button.hide()
        self.status_label.setText('')
    
    def show_abort_button(self):
        self.status_label.setText('PRESS BUTTON TO ABORT\nI GET BY WITH A LITTLE HELP FROM MY FRIENDS...')
        self.status_label.setStyleSheet("color: #ffaa00;")
        self.abort_button.show()
    
    def press_abort_button(self):
        print("Server room abort button pressed!")
        self.sio.emit('abort_button_press', {'location': 'server_room'})
        self.abort_button.setEnabled(False)
        self.status_label.setText('BUTTON PRESSED!\nI GET BY WITH A LITTLE HELP FROM MY FRIENDS...')
    
    def show_success(self):
        self.title_label.setText('✓ MISSION COMPLETE ✓')
        self.title_label.setStyleSheet("color: #00ff00;")
        self.instruction_label.setText('SELF-DESTRUCT SEQUENCE ABORTED!')
        self.instruction_label.setStyleSheet("color: #00ff00;")
        self.status_label.setText('YOU HAVE SAVED THE FACILITY!')
        self.status_label.setStyleSheet("color: #00ff00;")
        self.abort_button.hide()
        self.stop_sounds.set()
    
    def reset_abort_button(self):
        self.abort_button.setEnabled(True)
        self.status_label.setText('FAILED! TRY AGAIN\n(MUST BE WITHIN 10 SECONDS)')
        self.status_label.setStyleSheet("color: #ff0000;")
    
    def reset_station(self):
        """Reset server room station to initial code entry state"""
        self.title_label.setText('SERVER CONTROL TERMINAL')
        self.title_label.setStyleSheet("color: #00ff00;")
        self.instruction_label.setText('ENTER SHUTDOWN CODE:')
        self.instruction_label.setStyleSheet("color: #00ff00;")
        self.code_input.show()
        self.code_input.setEnabled(True)
        self.code_input.clear()
        self.submit_button.show()
        self.submit_button.setEnabled(True)
        self.status_label.setText('')
        self.abort_button.hide()
        self.abort_button.setEnabled(True)
    
    def play_sound(self, clip_name):
        """Play audio clip"""
        try:
            audio_file = os.path.join(self.audio_path, f'{clip_name}.mp3')
            if os.path.exists(audio_file):
                pygame.mixer.music.load(audio_file)
                pygame.mixer.music.play()
                print(f"Playing: {clip_name}")
            else:
                print(f"Audio file not found: {audio_file}")
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def start_random_sounds(self):
        """Background thread for random creepy sounds"""
        def random_sound_loop():
            creepy_sounds = ['creepy1', 'creepy2', 'whisper', 'footsteps', 'door_creak']
            while not self.stop_sounds.is_set():
                # Wait random interval (30-120 seconds)
                wait_time = random.randint(30, 120)
                if self.stop_sounds.wait(wait_time):
                    break
                
                # Play random creepy sound
                sound = random.choice(creepy_sounds)
                self.play_sound(sound)
        
        sound_thread = Thread(target=random_sound_loop, daemon=True)
        sound_thread.start()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        self.stop_sounds.set()
        if hasattr(self, 'sio'):
            self.sio.disconnect()
        pygame.mixer.quit()
        event.accept()

if __name__ == '__main__':
    SERVER_URL = 'http://localhost:5000'  # Update with DM's IP for production
    
    app = QApplication(sys.argv)
    station = ServerRoomStation(SERVER_URL)
    sys.exit(app.exec_())