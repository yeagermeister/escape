import sys
import socketio
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt5.QtGui import QFont

class TimerSignals(QObject):
    update_timer = pyqtSignal(int)
    update_status = pyqtSignal(str)

class TimerDisplay(QWidget):
    def __init__(self, server_url):
        super().__init__()
        self.signals = TimerSignals()
        self.signals.update_timer.connect(self.update_display)
        self.signals.update_status.connect(self.update_status_display)
        
        self.initUI()
        self.setup_socketio(server_url)
    
    def initUI(self):
        self.setWindowTitle('Escape Room Timer')
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(50)
        layout.setAlignment(Qt.AlignCenter)
        
        # Timer label
        self.timer_label = QLabel('30:00', self)
        self.timer_label.setAlignment(Qt.AlignCenter)
        self.timer_label.setStyleSheet("""
            color: #00ff00;
            font-weight: bold;
        """)
        font = QFont('Courier New', 200, QFont.Bold)
        self.timer_label.setFont(font)
        layout.addWidget(self.timer_label)
        
        # Status label
        self.status_label = QLabel('READY', self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #00ff00;")
        status_font = QFont('Courier New', 40)
        self.status_label.setFont(status_font)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def setup_socketio(self, server_url):
        self.sio = socketio.Client()
        self.heartbeat_timer = QTimer()
        self.heartbeat_timer.timeout.connect(self.send_heartbeat)
        
        @self.sio.on('connect')
        def on_connect():
            print('Connected to server')
            # Register this terminal
            self.sio.emit('register_terminal', {'type': 'timer_display'})
            # Start sending heartbeats
            self.heartbeat_timer.start(5000)  # Every 5 seconds
            self.signals.update_status.emit('CONNECTED')
        
        @self.sio.on('registration_confirmed')
        def on_registration(data):
            print(f"Registration confirmed: {data['type']}")
        
        @self.sio.on('timer_update')
        def on_timer_update(data):
            self.signals.update_timer.emit(data['time_remaining'])
        
        @self.sio.on('timer_started')
        def on_timer_started(data):
            self.signals.update_status.emit('GAME ACTIVE')
            self.signals.update_timer.emit(data['time_remaining'])
        
        @self.sio.on('timer_paused')
        def on_timer_paused(data):
            self.signals.update_status.emit('PAUSED')
        
        @self.sio.on('timer_resumed')
        def on_timer_resumed(data):
            self.signals.update_status.emit('GAME ACTIVE')
        
        @self.sio.on('game_over')
        def on_game_over(data):
            self.signals.update_status.emit('TIME UP!')
            self.timer_label.setStyleSheet("color: #ff0000; font-weight: bold;")
        
        @self.sio.on('game_reset')
        def on_game_reset(data):
            self.signals.update_status.emit('READY')
            self.signals.update_timer.emit(1800)
            self.timer_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        
        @self.sio.on('timer_stopped')
        def on_timer_stopped(data):
            self.signals.update_status.emit('READY')
            self.signals.update_timer.emit(1800)
            self.timer_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        
        @self.sio.on('self_destruct_aborted')
        def on_aborted(data):
            self.signals.update_status.emit('MISSION COMPLETE!')
            self.timer_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        
        try:
            self.sio.connect(server_url)
        except Exception as e:
            print(f"Connection error: {e}")
            self.report_error(f"Connection failed: {e}")
            self.signals.update_status.emit('CONNECTION FAILED')
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            self.sio.emit('heartbeat', {'type': 'timer_display'})
        except Exception as e:
            print(f"Heartbeat error: {e}")
    
    def report_error(self, error_msg):
        """Report error to DM"""
        try:
            self.sio.emit('terminal_error', {
                'type': 'timer_display',
                'error': error_msg
            })
            print(f"Error reported to DM: {error_msg}")
        except Exception as e:
            print(f"Could not report error: {e}")
    
    def update_display(self, time_remaining):
        minutes = time_remaining // 60
        seconds = time_remaining % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.timer_label.setText(time_str)
        
        # Change color based on time
        if time_remaining <= 60:
            self.timer_label.setStyleSheet("color: #ff0000; font-weight: bold;")
        elif time_remaining <= 300:
            self.timer_label.setStyleSheet("color: #ffaa00; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: #00ff00; font-weight: bold;")
    
    def update_status_display(self, status):
        self.status_label.setText(status)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
    
    def closeEvent(self, event):
        self.heartbeat_timer.stop()
        if hasattr(self, 'sio'):
            self.sio.disconnect()
        event.accept()

if __name__ == '__main__':
    # Change this to your DM Surface Pro's IP address
    # Use 'localhost' if testing on the same machine
    SERVER_URL = 'http://10.0.0.167:5000'  # Update with actual IP for production
    
    app = QApplication(sys.argv)
    timer = TimerDisplay(SERVER_URL)
    sys.exit(app.exec_())