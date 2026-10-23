"""
server.py - Flask Web Server & API for Fosi Audio DAC Monitor
"""

import sys
import os
import io
import wave
import math
import struct
import winsound
from flask import Flask, render_template, jsonify, request
from dac_core import FosiDACController

if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

template_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
controller = FosiDACController()

def generate_tone_wav(freq=440, duration=0.4, channel='both'):
    sample_rate = 48000
    n_samples = int(sample_rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        ramp = int(sample_rate * 0.04) # 40ms attack/decay
        for i in range(n_samples):
            env = 1.0
            if i < ramp:
                env = i / ramp
            elif i > (n_samples - ramp):
                env = (n_samples - i) / ramp
            val = int(env * 0.28 * 32767.0 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
            left = val if channel in ('left', 'both') else 0
            right = val if channel in ('right', 'both') else 0
            frames.append(struct.pack('<hh', left, right))
        wav.writeframes(b''.join(frames))
    return buf.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    try:
        status = controller.get_full_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/set_format', methods=['POST'])
def set_format():
    try:
        data = request.get_json() or {}
        sample_rate = int(data.get('sample_rate', 48000))
        bit_depth = int(data.get('bit_depth', 32))
        
        status = controller.get_full_status()
        if not status.get('connected'):
            return jsonify({'success': False, 'error': 'No DAC connected'}), 400
        
        dev_id = status['device']['id']
        controller.set_device_format(dev_id, sample_rate, bit_depth)
        
        # Return updated status
        new_status = controller.get_full_status()
        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/set_volume', methods=['POST'])
def set_volume():
    try:
        data = request.get_json() or {}
        vol = int(data.get('volume', 50))
        actual = controller.set_volume(vol)
        return jsonify({'success': True, 'volume': actual})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/toggle_mute', methods=['POST'])
def toggle_mute():
    try:
        data = request.get_json() or {}
        mute = bool(data.get('mute', False))
        actual = controller.set_mute(mute)
        return jsonify({'success': True, 'mute': actual})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_tone', methods=['POST'])
def test_tone():
    try:
        data = request.get_json() or {}
        channel = data.get('channel', 'both').lower()
        freq = int(data.get('freq', 440))
        
        wav_data = generate_tone_wav(freq=freq, duration=0.35, channel=channel)
        winsound.PlaySound(wav_data, winsound.SND_MEMORY | winsound.SND_ASYNC)
        return jsonify({'success': True, 'channel': channel, 'freq': freq})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = 5055
    print(f"==================================================")
    print(f"  FOSI AUDIO DAC STUDIO MONITOR & CONTROLLER")
    print(f"  Running locally at: http://127.0.0.1:{port}")
    print(f"==================================================")
    app.run(host='127.0.0.1', port=port, debug=False)
