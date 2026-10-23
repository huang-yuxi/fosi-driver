# Fosi Audio DAC Studio Monitor & Controller

A dedicated, audiophile-grade real-time hardware telemetry monitor and settings controller built for your **Fosi Audio DAC** and monitor speakers on Windows.

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

### 2. Live Settings Control
* **On-the-Fly Sampling Rate Switcher**: One-click instant switching between all supported DAC sample rates:
  * `44.1 kHz`, `48.0 kHz`, `88.2 kHz`, `96.0 kHz`, `176.4 kHz`, `192.0 kHz`, `352.8 kHz`, `384.0 kHz`, `705.6 kHz`, `768.0 kHz`.
* **Bit Depth Switcher**: Switch between `16-Bit`, `24-Bit`, and `32-Bit Float`.
* **Master Volume & Mute**: Instant smooth slider with volume percentage and instant mute toggle.
* **Monitor Speaker Alignment & Channel Test**:
  * `Test Left`: Plays a 440 Hz chime exclusively through your Left monitor.
  * `Stereo Center`: Plays a balanced 554 Hz chime across both monitors.
  * `Test Right`: Plays an 880 Hz chime exclusively through your Right monitor.

---

## How to Run

### Method 1: One-Click Desktop App (Recommended)
Double-click [`run_monitor.bat`](file:///j:/fosi/run_monitor.bat).
This automatically starts the local backend and opens a clean, borderless desktop window.

### Method 2: Command Line
Open PowerShell or Command Prompt in `j:\fosi`:
```powershell
python app_launcher.py
```
Or to run just the web server and view it in your favorite browser:
```powershell
python server.py
```
Then navigate to: **[http://127.0.0.1:5055](http://127.0.0.1:5055)**

---

## File Structure

* [`dac_core.py`](file:///j:/fosi/dac_core.py): Windows Core Audio (WASAPI), `IMMDevice`, `IAudioMeterInformation`, `IAudioEndpointVolume`, and undocumented `IPolicyConfig` COM driver interface.
* [`server.py`](file:///j:/fosi/server.py): Flask REST API & Web Server.
* [`app_launcher.py`](file:///j:/fosi/app_launcher.py): Launches the local server and opens a dedicated app window.
* [`templates/index.html`](file:///j:/fosi/templates/index.html): Audiophile OLED display dashboard.
* [`static/style.css`](file:///j:/fosi/static/style.css): Custom dark brushed gunmetal / Fosi amber theme.
* [`static/app.js`](file:///j:/fosi/static/app.js): High-speed client-side telemetry engine.
* [`run_monitor.bat`](file:///j:/fosi/run_monitor.bat): Windows batch launcher.
