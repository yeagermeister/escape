import sys
import socketio
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, pyqtSignal, QObject
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
        self.sio = socketio.Client(logger=False, engineio_logger=False,
            reconnection=True, reconnection_attempts=0,
            reconnection_delay=1, reconnection_delay_max=5)
        
        @self.sio.event
        def connect():
            print('Timer display connected')
            self.signals.update_status.emit('CONNECTED')
        
        @self.sio.event
        def disconnect():
            print('Timer display disconnected')
        
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
            self.signals.update_status.emit('PRESS EXIT BUTTON')
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
            self.signals.update_status.emit('PRESS EXIT BUTTON')
            self.timer_label.setStyleSheet("color: #00ff00; font-weight: bold;")
        
        try:
            print(f"Connecting to {server_url}...")
            self.sio.connect(server_url, namespaces=['/'])
            print("Connected successfully!")
        except Exception as e:
            print(f"Connection error: {e}")
            self.signals.update_status.emit('CONNECTION FAILED')
    
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
        if hasattr(self, 'sio') and self.sio.connected:
            self.sio.disconnect()
        event.accept()

if __name__ == '__main__':
    SERVER_URL = 'http://10.0.0.167:5000'  # DM Mac IP
    
    app = QApplication(sys.argv)
    timer = TimerDisplay(SERVER_URL)
    sys.exit(app.exec_())