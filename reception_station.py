import sys
import socketio
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

class ReceptionSignals(QObject):
    unlock = pyqtSignal()
    show_abort = pyqtSignal()
    abort_success = pyqtSignal()
    full_reset = pyqtSignal()

class ReceptionStation(QWidget):
    def __init__(self, server_url):
        super().__init__()
        self.signals = ReceptionSignals()
        self.signals.unlock.connect(self.unlock_screen)
        self.signals.show_abort.connect(self.show_abort_button)
        self.signals.abort_success.connect(self.show_success)
        self.signals.full_reset.connect(self.reset_to_locked)
        
        self.initUI()
        self.setup_socketio(server_url)
    
    def initUI(self):
        self.setWindowTitle('Reception Terminal')
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        # Locked message
        self.locked_label = QLabel('🔒 SYSTEM LOCKED 🔒', self)
        self.locked_label.setAlignment(Qt.AlignCenter)
        self.locked_label.setStyleSheet("color: #ff0000;")
        font = QFont('Courier New', 80, QFont.Bold)
        self.locked_label.setFont(font)
        layout.addWidget(self.locked_label)
        
        self.message_label = QLabel('ACCESS DENIED', self)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("color: #ff0000;")
        self.message_label.setWordWrap(True)
        msg_font = QFont('Courier New', 40)
        self.message_label.setFont(msg_font)
        layout.addWidget(self.message_label)
        
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
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        
        @self.sio.on('connect')
        def on_connect():
            print('Reception station connected')
            # Register this terminal
            self.sio.emit('register_terminal', {'type': 'reception'})
            # Start sending heartbeats
            self.heartbeat_timer.start(5000)  # Every 5 seconds
        
        @self.sio.on('registration_confirmed')
        def on_registration(data):
            print(f"Registration confirmed: {data['type']}")
        
        @self.sio.on('game_over')
        def on_game_over(data):
            self.signals.unlock.emit()
        
        @self.sio.on('transmission_shutdown')
        def on_transmission_shutdown(data):
            if data.get('success'):
                self.signals.show_abort.emit()
        
        @self.sio.on('self_destruct_aborted')
        def on_aborted(data):
            self.signals.abort_success.emit()
        
        @self.sio.on('game_reset')
        def on_reset(data):
            self.signals.full_reset.emit()
        
        @self.sio.on('timer_stopped')
        def on_stopped(data):
            self.signals.full_reset.emit()
        
        @self.sio.on('abort_failed_full_reset')
        def on_abort_failed_full_reset(data):
            self.signals.full_reset.emit()
        
        try:
            self.sio.connect(server_url)
        except Exception as e:
            print(f"Connection error: {e}")
            self.report_error(f"Connection failed: {e}")
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            self.sio.emit('heartbeat', {'type': 'reception'})
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    def report_error(self, error_msg):
        """Report error to DM"""
        try:
            self.sio.emit('terminal_error', {
                'type': 'reception',
                'error': error_msg
            })
            print(f"Error reported to DM: {error_msg}")
        except Exception as e:
            print(f"Could not report error: {e}")
    
    def unlock_screen(self):
        self.locked_label.setText('✓ SYSTEM UNLOCKED ✓')
        self.locked_label.setStyleSheet("color: #00ff00;")
        self.message_label.setText('ACCESS GRANTED')
        self.message_label.setStyleSheet("color: #00ff00;")
        self.abort_button.hide()
    
    def show_abort_button(self):
        self.locked_label.setText('⚠️ SELF-DESTRUCT ACTIVE ⚠️')
        self.locked_label.setStyleSheet("color: #ff0000;")
        self.message_label.setText('PRESS BUTTON TO ABORT\nI GET BY WITH A LITTLE HELP FROM MY FRIENDS')
        self.message_label.setStyleSheet("color: #ffaa00;")
        self.abort_button.show()
    
    def press_abort_button(self):
        print("Reception abort button pressed!")
        try:
            self.sio.emit('abort_button_press', {'location': 'reception'})
            self.abort_button.setEnabled(False)
            self.message_label.setText('BUTTON PRESSED!\nWAITING FOR SERVER ROOM...')
        except Exception as e:
            error_msg = f"Abort button error: {e}"
            print(error_msg)
            self.report_error(error_msg)
            self.message_label.setText(f'ERROR: {str(e)}')
            self.abort_button.setEnabled(True)
    
    def show_success(self):
        self.locked_label.setText('✓ MISSION COMPLETE ✓')
        self.locked_label.setStyleSheet("color: #00ff00;")
        self.message_label.setText('SELF-DESTRUCT SEQUENCE ABORTED!')
        self.message_label.setStyleSheet("color: #00ff00;")
        self.abort_button.hide()
    
    def reset_to_locked(self):
        self.locked_label.setText('🔒 SYSTEM LOCKED 🔒')
        self.locked_label.setStyleSheet("color: #ff0000;")
        self.message_label.setText('ACCESS DENIED')
        self.message_label.setStyleSheet("color: #ff0000;")
        self.abort_button.hide()
        self.abort_button.setEnabled(True)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        self.heartbeat_timer.stop()
        if hasattr(self, 'sio'):
            self.sio.disconnect()
        event.accept()

if __name__ == '__main__':
    SERVER_URL = 'http://10.0.0.167:5000'  # Update with DM's IP
    
    app = QApplication(sys.argv)
    station = ReceptionStation(SERVER_URL)
    sys.exit(app.exec_())