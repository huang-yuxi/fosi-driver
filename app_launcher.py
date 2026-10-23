"""
app_launcher.py - Fosi Audio DAC Monitor with System Tray & Dedicated Window
"""

import sys
import os
import time
import subprocess
import threading
import webbrowser
import logging
import socket
from PIL import Image
import pystray

# Ensure stdout/stderr are valid when compiled with --noconsole
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from server import app, controller

PORT = 5055
URL = f"http://127.0.0.1:{PORT}"

if getattr(sys, 'frozen', False):
    BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ICON_PATH = os.path.join(BASE_DIR, 'fosi_dac.ico')

# Global state
tray_icon = None
active_window_proc = None
is_running = True

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_server():
    try:
        app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
    except Exception:
        pass

def find_browser():
    candidates = [
        os.path.expandvars(r'%ProgramFiles%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%LocalAppData%\Google\Chrome\Application\chrome.exe'),
        os.path.expandvars(r'%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe'),
        os.path.expandvars(r'%ProgramFiles%\Microsoft\Edge\Application\msedge.exe'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def open_window():
    """Open or focus the dashboard window in app mode."""
    global active_window_proc
    # If window is already open, browser will focus it
    browser_exe = find_browser()
    if browser_exe:
        cmd = [
            browser_exe,
            f"--app={URL}",
            "--window-size=1180,860",
            "--window-position=120,80",
        ]
        try:
            active_window_proc = subprocess.Popen(cmd)
            return
        except Exception:
            pass
    # Fallback to default browser
    webbrowser.open(URL)

def set_dac_rate(rate):
    try:
        status = controller.get_full_status()
        if status.get('connected'):
            dev_id = status['device']['id']
            bits = status['format']['bit_depth']
            controller.set_device_format(dev_id, rate, bits)
    except Exception:
        pass

def set_dac_volume(vol_pct):
    try:
        controller.set_volume(vol_pct)
    except Exception:
        pass

def toggle_dac_mute():
    try:
        vol = controller.get_volume_info()
        controller.set_mute(not vol.get('mute', False))
    except Exception:
        pass

def exit_application(icon, item=None):
    global is_running
    is_running = False
    if icon:
        icon.stop()
    os._exit(0)

def update_tray_tooltip_loop(icon):
    """Background worker that continuously updates the tray icon tooltip with live DAC status."""
    while is_running:
        try:
            status = controller.get_full_status()
            if status.get('connected'):
                fmt = status['format']
                rate_khz = fmt['sample_rate_khz']
                bits = fmt['bit_depth']
                bitrate = fmt['bitrate_kbps']
                vol = status['volume']['volume']
                streaming = status['streaming']['is_streaming']
                sources = status['streaming']['active_sources']
                
                src_txt = sources[0] if sources else ('Active' if streaming else 'Standby')
                
                tooltip = (
                    f"Fosi Audio DS3\n"
                    f"{rate_khz} · {bits}-bit ({bitrate:,} kbps)\n"
                    f"Status: {src_txt} | Vol: {vol}%"
                )
            else:
                tooltip = "Fosi Audio DAC: Disconnected"
            
            icon.title = tooltip[:127] # Windows tray tooltip max len 128
        except Exception:
            pass
        time.sleep(1.5)

def setup_tray():
    global tray_icon
    try:
        img = Image.open(ICON_PATH)
    except Exception:
        # Fallback 32x32 orange circle icon
        img = Image.new('RGBA', (32, 32), (255, 106, 0, 255))

    def on_rate_click(rate):
        return lambda icon, item: set_dac_rate(rate)

    def on_vol_click(vol):
        return lambda icon, item: set_dac_volume(vol)

    rate_menu = pystray.Menu(
        pystray.MenuItem('44.1 kHz (CD)', on_rate_click(44100)),
        pystray.MenuItem('48.0 kHz (Studio)', on_rate_click(48000)),
        pystray.MenuItem('88.2 kHz', on_rate_click(88200)),
        pystray.MenuItem('96.0 kHz (Hi-Res)', on_rate_click(96000)),
        pystray.MenuItem('176.4 kHz', on_rate_click(176400)),
        pystray.MenuItem('192.0 kHz (Master)', on_rate_click(192000)),
        pystray.MenuItem('352.8 kHz (DXD)', on_rate_click(352800)),
        pystray.MenuItem('384.0 kHz', on_rate_click(384000)),
        pystray.MenuItem('768.0 kHz (Ultra Hi-Res)', on_rate_click(768000)),
    )

    vol_menu = pystray.Menu(
        pystray.MenuItem('Mute / Unmute', lambda icon, item: toggle_dac_mute()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('100% Volume', on_vol_click(100)),
        pystray.MenuItem('80% Volume', on_vol_click(80)),
        pystray.MenuItem('60% Volume', on_vol_click(60)),
        pystray.MenuItem('40% Volume', on_vol_click(40)),
        pystray.MenuItem('20% Volume', on_vol_click(20)),
    )

    menu = pystray.Menu(
        pystray.MenuItem('Open Studio Dashboard', lambda icon, item: open_window(), default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Sample Rate', rate_menu),
        pystray.MenuItem('Volume & Mute', vol_menu),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Exit Fosi DAC Monitor', exit_application),
    )

    tray_icon = pystray.Icon(
        name='FosiDACMonitor',
        icon=img,
        title='Fosi Audio DAC Monitor',
        menu=menu
    )

    # Start tooltip background updater thread
    tooltip_thread = threading.Thread(target=update_tray_tooltip_loop, args=(tray_icon,), daemon=True)
    tooltip_thread.start()

    # Open dashboard window initially on launch
    threading.Thread(target=lambda: (time.sleep(0.8), open_window()), daemon=True).start()

    # tray_icon.run() blocks the main thread
    tray_icon.run()

if __name__ == '__main__':
    # Start web server in background thread if not already active
    if not is_port_in_use(PORT):
        server_thread = threading.Thread(target=start_server, daemon=True)
        server_thread.start()

    # Start System Tray icon (runs on main thread)
    setup_tray()
