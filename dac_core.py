"""
dac_core.py - Core Windows Audio & WASAPI interface for Fosi Audio DACs
Handles device discovery, real-time telemetry, volume control, and sample rate switching.
"""

import ctypes
import uuid
import struct
import math
from ctypes import wintypes
import winreg
import psutil
from pycaw.pycaw import AudioUtilities

ole32 = ctypes.windll.ole32

# GUID helpers
def _to_guid(uuid_str):
    return ctypes.create_string_buffer(uuid.UUID(uuid_str).bytes_le)

CLSID_MMDeviceEnumerator = _to_guid('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
IID_IMMDeviceEnumerator = _to_guid('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
IID_IAudioMeterInformation = _to_guid('{C02216F6-8C67-4B5B-9D00-D008E73E0064}')
CLSID_PolicyConfigClient = _to_guid('{870af99c-171d-4f9e-af0d-e63df40c2bc9}')
IID_IPolicyConfig = _to_guid('{f8679f50-850a-41cf-9c72-430f290290c8}')

# SubFormat KSDATAFORMAT_SUBTYPE_PCM: {00000001-0000-0010-8000-00AA00389B71}
SUBFORMAT_PCM = bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10, 0x00, 0x80, 0x00, 0x00, 0xaa, 0x00, 0x38, 0x9b, 0x71])

SUPPORTED_RATES = [44100, 48000, 88200, 96000, 176400, 192000, 352800, 384000, 705600, 768000]
SUPPORTED_BITS = [16, 24, 32]

class FosiDACController:
    def __init__(self):
        # We initialize COM on demand per thread
        pass

    def _ensure_com(self):
        try:
            ole32.CoInitialize(None)
        except Exception:
            pass

    def discover_dac(self):
        """Find the Fosi DAC or default audio output endpoint."""
        self._ensure_com()
        path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render'
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)
        except Exception:
            return None

        candidates = []
        for i in range(winreg.QueryInfoKey(key)[0]):
            subkey = winreg.EnumKey(key, i)
            try:
                pkey = winreg.OpenKey(key, subkey + r'\Properties')
                props = {}
                for j in range(winreg.QueryInfoKey(pkey)[1]):
                    k, v, _ = winreg.EnumValue(pkey, j)
                    props[k] = v
                name = props.get('{a45c254e-df1c-4efd-8020-67d146a850e0},2', '')
                desc = props.get('{b3f8fa53-0004-438e-9003-51a46e139bfc},6', '')
                interface = props.get('{233164c8-1b2c-4c7d-bc68-b671687a2567},1', '')
                dev_id = f'{{0.0.0.00000000}}.{subkey}'
                
                dkey = winreg.OpenKey(key, subkey)
                state = winreg.QueryValueEx(dkey, 'DeviceState')[0]
                
                full_str = (str(name) + ' ' + str(desc) + ' ' + str(interface)).upper()
                is_fosi = ('FOSI' in full_str or 'DS3' in full_str or '152A' in full_str)
                
                if state == 1: # Active
                    candidates.append({
                        'id': dev_id,
                        'name': name or 'Speakers',
                        'desc': desc or 'USB Audio Device',
                        'interface': interface,
                        'is_fosi': is_fosi,
                        'active': True
                    })
            except Exception:
                pass

        # Prioritize active Fosi DAC
        for c in candidates:
            if c['is_fosi']:
                return c
        
        # Fallback to first active audio endpoint
        if candidates:
            return candidates[0]
        return None

    def get_current_format(self, dev_id):
        """Retrieve current sample rate, bit depth, and channels via IPolicyConfig."""
        self._ensure_com()
        try:
            pPolicy = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                CLSID_PolicyConfigClient, None, 1,
                IID_IPolicyConfig, ctypes.byref(pPolicy)
            )
            if hr != 0 or not pPolicy.value:
                return None
            
            vtable = ctypes.cast(ctypes.cast(pPolicy, ctypes.POINTER(ctypes.c_void_p)).contents, ctypes.POINTER(ctypes.c_void_p))
            # Index 4: GetDeviceFormat(PCWSTR wszDeviceId, INT bDefault, WAVEFORMATEX **ppFormat)
            GetDeviceFormat_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
            GetDeviceFormat = GetDeviceFormat_Proto(vtable[4])

            pFmt = ctypes.c_void_p()
            hr = GetDeviceFormat(pPolicy, dev_id, 0, ctypes.byref(pFmt))
            if hr == 0 and pFmt.value:
                raw = (ctypes.c_byte * 40).from_address(pFmt.value)
                tag, ch, rate, avg_bytes, align, bits = struct.unpack_from('<HHIIHH', bytes(raw), 0)
                return {
                    'sample_rate': rate,
                    'bit_depth': bits,
                    'channels': ch,
                    'tag': tag
                }
        except Exception as e:
            print("Error get_current_format:", e)
        return None

    def set_device_format(self, dev_id, sample_rate, bit_depth=32, channels=2):
        """Set DAC sample rate and bit depth via IPolicyConfig::SetDeviceFormat."""
        self._ensure_com()
        if sample_rate not in SUPPORTED_RATES:
            raise ValueError(f"Unsupported sample rate: {sample_rate}")
        if bit_depth not in SUPPORTED_BITS:
            raise ValueError(f"Unsupported bit depth: {bit_depth}")

        pPolicy = ctypes.c_void_p()
        hr = ole32.CoCreateInstance(
            CLSID_PolicyConfigClient, None, 1,
            IID_IPolicyConfig, ctypes.byref(pPolicy)
        )
        if hr != 0 or not pPolicy.value:
            raise RuntimeError(f"Failed to create IPolicyConfig COM instance: {hex(hr & 0xffffffff)}")

        vtable = ctypes.cast(ctypes.cast(pPolicy, ctypes.POINTER(ctypes.c_void_p)).contents, ctypes.POINTER(ctypes.c_void_p))
        # Index 6: SetDeviceFormat(PCWSTR wszDeviceId, WAVEFORMATEX *pEndpointFormat, WAVEFORMATEX *pMixFormat)
        SetDeviceFormat_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p)
        SetDeviceFormat = SetDeviceFormat_Proto(vtable[6])

        block_align = channels * (bit_depth // 8)
        avg_bytes = sample_rate * block_align
        fmt_bytes = struct.pack('<HHIIHHHHI', 0xFFFE, channels, sample_rate, avg_bytes, block_align, bit_depth, 22, bit_depth, 0x3) + SUBFORMAT_PCM
        buf = ctypes.create_string_buffer(fmt_bytes)
        pBuf = ctypes.cast(buf, ctypes.c_void_p)

        hr = SetDeviceFormat(pPolicy, dev_id, pBuf, pBuf)
        if hr != 0:
            raise RuntimeError(f"SetDeviceFormat failed with HRESULT {hex(hr & 0xffffffff)}")
        return True

    def get_peak_meter(self, dev_id):
        """Get Left & Right channel peak values (0.0 to 1.0)."""
        self._ensure_com()
        try:
            pEnum = ctypes.c_void_p()
            hr = ole32.CoCreateInstance(
                CLSID_MMDeviceEnumerator, None, 1,
                IID_IMMDeviceEnumerator, ctypes.byref(pEnum)
            )
            if hr != 0 or not pEnum.value:
                return {'left': 0.0, 'right': 0.0, 'master': 0.0}

            vtable_enum = ctypes.cast(ctypes.cast(pEnum, ctypes.POINTER(ctypes.c_void_p)).contents, ctypes.POINTER(ctypes.c_void_p))
            # 5: GetDevice(LPCWSTR pwstrId, IMMDevice **ppDevice)
            GetDevice_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p))
            GetDevice = GetDevice_Proto(vtable_enum[5])

            pDevice = ctypes.c_void_p()
            hr = GetDevice(pEnum, dev_id, ctypes.byref(pDevice))
            if hr != 0 or not pDevice.value:
                return {'left': 0.0, 'right': 0.0, 'master': 0.0}

            dev_vtable = ctypes.cast(ctypes.cast(pDevice, ctypes.POINTER(ctypes.c_void_p)).contents, ctypes.POINTER(ctypes.c_void_p))
            Activate_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
            Activate = Activate_Proto(dev_vtable[3])

            pMeter = ctypes.c_void_p()
            hr = Activate(pDevice, IID_IAudioMeterInformation, 1, None, ctypes.byref(pMeter))
            if hr != 0 or not pMeter.value:
                return {'left': 0.0, 'right': 0.0, 'master': 0.0}

            meter_vtable = ctypes.cast(ctypes.cast(pMeter, ctypes.POINTER(ctypes.c_void_p)).contents, ctypes.POINTER(ctypes.c_void_p))
            
            # Master Peak (Index 3)
            GetPeakValue_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.POINTER(ctypes.c_float))
            GetPeakValue = GetPeakValue_Proto(meter_vtable[3])
            master_peak = ctypes.c_float()
            GetPeakValue(pMeter, ctypes.byref(master_peak))

            # Channel Peaks (Index 5)
            GetChannelsPeakValues_Proto = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_float))
            GetChannelsPeakValues = GetChannelsPeakValues_Proto(meter_vtable[5])
            peaks = (ctypes.c_float * 2)()
            GetChannelsPeakValues(pMeter, 2, peaks)

            return {
                'left': max(0.0, min(1.0, float(peaks[0]))),
                'right': max(0.0, min(1.0, float(peaks[1]))),
                'master': max(0.0, min(1.0, float(master_peak.value)))
            }
        except Exception as e:
            return {'left': 0.0, 'right': 0.0, 'master': 0.0}

    def get_volume_info(self):
        """Get master volume scalar (0-100) and mute status."""
        self._ensure_com()
        try:
            speakers = AudioUtilities.GetSpeakers()
            volume = speakers.EndpointVolume
            vol_scalar = volume.GetMasterVolumeLevelScalar()
            mute = volume.GetMute()
            return {
                'volume': round(vol_scalar * 100),
                'mute': bool(mute)
            }
        except Exception:
            return {'volume': 50, 'mute': False}

    def set_volume(self, level_percent):
        """Set master volume (0-100)."""
        self._ensure_com()
        scalar = max(0.0, min(1.0, float(level_percent) / 100.0))
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        volume.SetMasterVolumeLevelScalar(scalar, None)
        return round(scalar * 100)

    def set_mute(self, mute_state):
        """Set mute state (bool)."""
        self._ensure_com()
        speakers = AudioUtilities.GetSpeakers()
        volume = speakers.EndpointVolume
        volume.SetMute(1 if mute_state else 0, None)
        return bool(mute_state)

    def get_active_sessions(self):
        """Enumerate active streaming audio applications."""
        self._ensure_com()
        active_apps = []
        try:
            sessions = AudioUtilities.GetAllSessions()
            for s in sessions:
                name = s.Process.name() if s.Process else 'System Sounds'
                pid = s.Process.pid if s.Process else 0
                state_code = getattr(s, 'State', 0)
                vol = round(s.SimpleAudioVolume.GetMasterVolume() * 100) if hasattr(s, 'SimpleAudioVolume') else 100
                is_active = (state_code == 1)
                active_apps.append({
                    'name': name,
                    'pid': pid,
                    'state': 'STREAMING' if is_active else 'IDLE',
                    'is_streaming': is_active,
                    'volume': vol
                })
        except Exception:
            pass
        return active_apps

    def get_full_status(self):
        """Aggregate complete real-time status object for UI dashboard."""
        dac = self.discover_dac()
        if not dac:
            return {
                'connected': False,
                'message': 'No audio output device found'
            }

        dev_id = dac['id']
        fmt = self.get_current_format(dev_id)
        meter = self.get_peak_meter(dev_id)
        vol = self.get_volume_info()
        sessions = self.get_active_sessions()

        sample_rate = fmt['sample_rate'] if fmt else 48000
        bit_depth = fmt['bit_depth'] if fmt else 32
        channels = fmt['channels'] if fmt else 2

        # Calculate uncompressed PCM stream bitrate in kbps
        # (rate * channels * bit_depth) / 1000
        bitrate_kbps = round((sample_rate * channels * bit_depth) / 1000)

        # Hi-Res Badge classification
        if sample_rate >= 705600:
            quality_tier = "ULTRA HI-RES (768k)"
            badge_class = "tier-ultra"
        elif sample_rate >= 352800:
            quality_tier = "DXD MASTER (384k)"
            badge_class = "tier-dxd"
        elif sample_rate >= 176400:
            quality_tier = "STUDIO MASTER (192k)"
            badge_class = "tier-master"
        elif sample_rate >= 88200:
            quality_tier = "HI-RES AUDIO (96k)"
            badge_class = "tier-hires"
        else:
            quality_tier = "STANDARD HI-FI"
            badge_class = "tier-standard"

        # Determine if streaming is currently happening
        streaming_sessions = [s['name'] for s in sessions if s['is_streaming']]
        is_streaming = (meter['master'] > 0.005) or (len(streaming_sessions) > 0)

        # Convert peak to dB (-60 dB floor)
        def to_db(linear):
            if linear <= 0.0001:
                return -60.0
            return max(-60.0, round(20 * math.log10(linear), 1))

        return {
            'connected': True,
            'device': {
                'id': dev_id,
                'name': dac['name'],
                'desc': dac['desc'],
                'is_fosi': dac['is_fosi'],
                'hardware': 'Fosi Audio DS3 (XMOS UAC2)' if dac['is_fosi'] else dac['desc'],
            },
            'format': {
                'sample_rate': sample_rate,
                'sample_rate_khz': f"{sample_rate / 1000:.1f} kHz",
                'bit_depth': bit_depth,
                'channels': channels,
                'bitrate_kbps': bitrate_kbps,
                'quality_tier': quality_tier,
                'badge_class': badge_class,
            },
            'meter': {
                'left': round(meter['left'], 3),
                'right': round(meter['right'], 3),
                'master': round(meter['master'], 3),
                'left_db': to_db(meter['left']),
                'right_db': to_db(meter['right']),
            },
            'streaming': {
                'is_streaming': is_streaming,
                'state_label': 'STREAMING ACTIVE' if is_streaming else 'STANDBY / IDLE',
                'active_sources': streaming_sessions,
            },
            'volume': vol,
            'sessions': sessions,
            'supported_rates': SUPPORTED_RATES,
            'supported_bits': SUPPORTED_BITS,
        }
