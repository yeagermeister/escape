from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime, timedelta
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'escape_room_secret_2024'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', 
    ping_timeout=60, ping_interval=25)

# Game state
game_state = {
    'timer_running': False,
    'time_remaining': 1800,  # 30 minutes in seconds
    'start_time': None,
    'reception_unlocked': False,
    'transmission_shut_down': False,
    'self_destruct_active': False,
    'self_destruct_aborted': False,
    'abort_buttons': {
        'reception': None,
        'server_room': None
    }
}

# Codes
TRANSMISSION_CODE = "4815162342"
ABORT_WINDOW_SECONDS = 10

def get_serializable_state():
    """Return a JSON-serializable version of game_state"""
    return {
        'timer_running': game_state['timer_running'],
        'time_remaining': game_state['time_remaining'],
        'reception_unlocked': game_state['reception_unlocked'],
        'transmission_shut_down': game_state['transmission_shut_down'],
        'self_destruct_active': game_state['self_destruct_active'],
        'self_destruct_aborted': game_state['self_destruct_aborted']
    }

@app.route('/')
def index():
    return render_template('dm_controller.html')

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('game_state', get_serializable_state())

@socketio.on('start_timer')
def handle_start_timer():
    """Start the 30-minute countdown"""
    game_state['timer_running'] = True
    game_state['start_time'] = datetime.now()
    game_state['time_remaining'] = 1800
    game_state['reception_unlocked'] = False
    game_state['transmission_shut_down'] = False
    game_state['self_destruct_active'] = False
    game_state['self_destruct_aborted'] = False
    game_state['abort_buttons'] = {'reception': None, 'server_room': None}
    
    print("Timer started!")
    
    # Start countdown loop
    socketio.start_background_task(countdown_timer)
    
    # Emit to all clients
    socketio.emit('timer_started', get_serializable_state(), namespace='/')
    socketio.emit('play_audio', {'clip': 'start'}, namespace='/')

def countdown_timer():
    """Background task to update timer every second"""
    while game_state['timer_running'] and game_state['time_remaining'] > 0:
        time.sleep(1)
        game_state['time_remaining'] -= 1
        socketio.emit('timer_update', {
            'time_remaining': game_state['time_remaining']
        }, namespace='/')
    
    if game_state['time_remaining'] <= 0:
        game_state['timer_running'] = False
        game_state['reception_unlocked'] = True
        socketio.emit('game_over', {'success': False}, namespace='/')

@socketio.on('pause_timer')
def handle_pause_timer():
    """Pause the timer (can be resumed)"""
    if game_state['timer_running']:
        game_state['timer_running'] = False
        print(f"Timer paused at {game_state['time_remaining']} seconds")
        socketio.emit('timer_paused', get_serializable_state(), namespace='/')

@socketio.on('resume_timer')
def handle_resume_timer():
    """Resume the timer from where it was paused"""
    if not game_state['timer_running'] and game_state['time_remaining'] > 0:
        game_state['timer_running'] = True
        print(f"Timer resumed at {game_state['time_remaining']} seconds")
        socketio.start_background_task(countdown_timer)
        socketio.emit('timer_resumed', get_serializable_state(), namespace='/')

@socketio.on('stop_timer')
def handle_stop_timer():
    """Emergency stop and complete reset"""
    game_state['timer_running'] = False
    game_state['time_remaining'] = 1800
    game_state['reception_unlocked'] = False
    game_state['transmission_shut_down'] = False
    game_state['self_destruct_active'] = False
    game_state['self_destruct_aborted'] = False
    game_state['abort_buttons'] = {'reception': None, 'server_room': None}
    print("Timer stopped and reset!")
    socketio.emit('timer_stopped', get_serializable_state(), namespace='/')

@socketio.on('reset_game')
def handle_reset_game():
    """Reset everything"""
    game_state['timer_running'] = False
    game_state['time_remaining'] = 1800
    game_state['start_time'] = None
    game_state['reception_unlocked'] = False
    game_state['transmission_shut_down'] = False
    game_state['self_destruct_active'] = False
    game_state['self_destruct_aborted'] = False
    game_state['abort_buttons'] = {'reception': None, 'server_room': None}
    print("Game reset!")
    socketio.emit('game_reset', get_serializable_state(), namespace='/')

@socketio.on('check_transmission_code')
def handle_transmission_code(data):
    """Check if transmission code is correct"""
    code = data.get('code', '')
    
    print(f"Code received: {code}")
    
    # Send verifying message first
    emit('transmission_verifying', {'code': code})
    
    # Simulate verification delay (2 seconds)
    time.sleep(2)
    
    if code == TRANSMISSION_CODE:
        game_state['transmission_shut_down'] = True
        game_state['self_destruct_active'] = True
        game_state['abort_buttons'] = {'reception': None, 'server_room': None}
        
        print("✓ Correct code! Self-destruct initiated!")
        
        # Emit to all clients
        socketio.emit('transmission_shutdown', {
            'success': True,
            'self_destruct_active': True
        }, namespace='/')
        
        # Trigger audio
        socketio.emit('play_audio', {'clip': 'alarm'}, namespace='/')
        
    else:
        print("✗ Invalid code")
        emit('transmission_shutdown', {'success': False, 'message': 'INVALID CODE - ACCESS DENIED'})

@socketio.on('abort_button_press')
def handle_abort_button(data):
    """Handle abort button press from either laptop"""
    location = data.get('location')
    current_time = datetime.now()
    
    if not game_state['self_destruct_active'] or game_state['self_destruct_aborted']:
        return
    
    print(f"Abort button pressed at {location}")
    
    # Record this button press
    game_state['abort_buttons'][location] = current_time
    
    # Check if both buttons have been pressed
    reception_time = game_state['abort_buttons']['reception']
    server_time = game_state['abort_buttons']['server_room']
    
    if reception_time and server_time:
        # Calculate time difference
        time_diff = abs((reception_time - server_time).total_seconds())
        
        if time_diff <= ABORT_WINDOW_SECONDS:
            # SUCCESS!
            game_state['self_destruct_aborted'] = True
            game_state['self_destruct_active'] = False
            game_state['timer_running'] = False
            game_state['reception_unlocked'] = True
            
            socketio.emit('self_destruct_aborted', {
                'success': True,
                'time_diff': round(time_diff, 2)
            }, namespace='/')
            
            print(f"✓ Self-destruct aborted! Time difference: {time_diff:.2f} seconds")
        else:
            # Too far apart - FULL RESET back to beginning
            game_state['abort_buttons'] = {'reception': None, 'server_room': None}
            game_state['self_destruct_active'] = False
            game_state['transmission_shut_down'] = False
            
            socketio.emit('abort_failed_full_reset', {
                'reason': 'not_simultaneous',
                'time_diff': round(time_diff, 2)
            }, namespace='/')
            print(f"✗ Abort failed - buttons pressed {time_diff:.2f} seconds apart - FULL RESET")
    else:
        # First button pressed
        socketio.emit('abort_button_pressed', {
            'location': location,
            'waiting_for': 'reception' if location == 'server_room' else 'server_room'
        }, namespace='/')

@socketio.on('trigger_audio')
def handle_trigger_audio(data):
    """DM can manually trigger audio clips"""
    clip = data.get('clip')
    socketio.emit('play_audio', {'clip': clip}, namespace='/')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

if __name__ == '__main__':
    print("=" * 50)
    print("ESCAPE ROOM SERVER STARTING")
    print("=" * 50)
    print(f"Transmission Shutdown Code: {TRANSMISSION_CODE}")
    print(f"Abort Button Window: {ABORT_WINDOW_SECONDS} seconds")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)