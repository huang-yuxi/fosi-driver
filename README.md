# Fosi Audio DAC Studio Monitor & Controller

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://opensource.org/licenses/MIT)
[![GitHub Release](https://img.shields.io/github/v/release/huang-yuxi/fosi-driver?color=00e676)](https://github.com/huang-yuxi/fosi-driver/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-00d2ff.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.10%2B-ffd600.svg)](https://python.org)

An open-source, audiophile-grade real-time hardware telemetry monitor, sampling rate controller, and Windows System Tray utility built for **Fosi Audio DACs** (DS3, DS2, K5 Pro, SK01/02, ZH350, etc.) and active studio monitors.

---

## Download Standalone App

You do not need Python installed to use the monitor. Download the pre-built Windows executable directly from the Releases page:

**[Download Latest Windows Release (v1.0.0)](https://github.com/huang-yuxi/fosi-driver/releases/latest)**

---

## Features

### 1. Real-Time Hardware Telemetry
* **Live Sampling Rate Display**: Big digital OLED readout indicating the exact active DAC clock (`44.1 kHz` up to `768.0 kHz`).
* **Audiophile Quality Tier Badging**:
  * `STANDARD HI-FI` (44.1k / 48k)
  * `HI-RES AUDIO` (88.2k / 96k)
  * `STUDIO MASTER` (176.4k / 192k)
  * `DXD MASTER` (352.8k / 384k)
  * `ULTRA HI-RES` (705.6k / 768k)
* **Live Bit Depth & Stream Bitrate**: Shows bit container (`16-Bit`, `24-Bit`, `32-Bit Float`) and real-time uncompressed PCM transmission bitrate in `kbps` (e.g. `3,072 kbps`).
* **Streaming Status**: Real-time detection of active streaming vs standby idle mode.
* **Dual Channel Stereo VU Peak Meter**: Real-time calibrated Left (L) & Right (R) channel meters with peak-hold tick indicators and decibel (`dB`) readouts.
* **Active Stream Application Inspector**: Automatically identifies which application is routing sound to the DAC (e.g., `chrome.exe`, `spotify.exe`, `tidal.exe`, `foobar2000.exe`).

### 2. Windows System Tray Integration
* **Live Status Tooltip**: Hovering over the tray icon near the clock displays real-time telemetry (active DAC, sample rate, bit depth, stream status, and volume).
* **Click to Open**: Single click or double click brings up the full Studio Dashboard window.
* **Silent Background Operation**: Closing the dashboard window minimizes the app to the system tray so it remains available without cluttering your taskbar.
* **Right-Click Context Menu**: Instant sample rate switching, volume adjustments, and mute toggle directly from the tray.

### 3. Live Hardware Settings Control
* **On-the-Fly Sampling Rate Switcher**: One-click instant switching between all supported DAC sample rates:
  * `44.1 kHz`, `48.0 kHz`, `88.2 kHz`, `96.0 kHz`, `176.4 kHz`, `192.0 kHz`, `352.8 kHz`, `384.0 kHz`, `705.6 kHz`, `768.0 kHz`.
* **Bit Depth Switcher**: Switch between `16-Bit`, `24-Bit`, and `32-Bit Float`.
* **Master Volume & Mute**: Instant smooth slider with volume percentage and instant mute toggle.
* **Monitor Speaker Alignment & Channel Test**:
  * `Test Left`: Plays a 440 Hz chime exclusively through your Left monitor.
  * `Stereo Center`: Plays a balanced 554 Hz chime across both monitors.
  * `Test Right`: Plays an 880 Hz chime exclusively through your Right monitor.

---

## Running from Source

If you prefer to run from source code:

1. Clone the repository:
   ```bash
   git clone https://github.com/huang-yuxi/fosi-driver.git
   cd fosi-driver
   ```
2. Install dependencies:
   ```bash
   pip install flask pycaw comtypes pystray Pillow psutil
   ```
3. Run the desktop application:
   ```bash
   python app_launcher.py
   ```
   Or double-click `run_monitor.bat`.

---

## Architecture

* `dac_core.py`: Low-level Windows Core Audio interface (WASAPI, `IMMDevice`, `IAudioMeterInformation`, `IAudioEndpointVolume`, and `IPolicyConfig`).
* `server.py`: Local Flask REST API server and test chime generator.
* `app_launcher.py`: System Tray manager (`pystray`) and desktop window controller.
* `templates/index.html`: Audiophile OLED display dashboard.
* `static/style.css`: Custom dark brushed gunmetal / Fosi amber styling.
* `static/app.js`: High-speed client telemetry engine.
* `Fosi_DAC_Monitor.spec`: PyInstaller standalone executable build specification.

---

## Contributing

Contributions, bug reports, and feature suggestions are welcome! Feel free to open an issue or submit a Pull Request.

---

## License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
