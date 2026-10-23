/**
 * app.js - Real-time telemetry & control logic for Fosi Audio DAC Studio Monitor
 */

(function () {
    'use strict';

    // State Variables
    let currentSampleRate = 48000;
    let currentBitDepth = 32;
    let isUserDraggingVolume = false;
    let volumeDebounceTimer = null;
    let peakHoldL = 0;
    let peakHoldR = 0;
    let lastStatusTimestamp = Date.now();

    // DOM Elements
    const elements = {
        sampleRateVal: document.getElementById('sample-rate-val'),
        tierBadge: document.getElementById('tier-badge'),
        bitDepthVal: document.getElementById('bit-depth-val'),
        bitrateVal: document.getElementById('bitrate-val'),
        activeSourceVal: document.getElementById('active-source-val'),
        streamingBadge: document.getElementById('streaming-badge'),
        streamStatusText: document.getElementById('stream-status-text'),
        streamIndicator: document.getElementById('stream-indicator'),
        
        meterFillL: document.getElementById('meter-fill-l'),
        meterFillR: document.getElementById('meter-fill-r'),
        meterPeakL: document.getElementById('meter-peak-l'),
        meterPeakR: document.getElementById('meter-peak-r'),
        peakReading: document.getElementById('peak-reading'),

        volumeSlider: document.getElementById('volume-slider'),
        volumeVal: document.getElementById('volume-val'),
        muteBtn: document.getElementById('mute-btn'),

        ratesGrid: document.getElementById('rates-grid'),
        bitButtons: document.querySelectorAll('.bit-btn'),
        switchingMsg: document.getElementById('switching-msg'),
        sessionsList: document.getElementById('sessions-list'),
        sessionCount: document.getElementById('session-count'),

        testLeftBtn: document.getElementById('test-left-btn'),
        testBothBtn: document.getElementById('test-both-btn'),
        testRightBtn: document.getElementById('test-right-btn'),
        refreshBtn: document.getElementById('refresh-btn'),
        toast: document.getElementById('toast'),
        toastText: document.getElementById('toast-text'),
    };

    /**
     * Map peak linear value (0.0 to 1.0) to VU meter percentage
     * Uses audio logarithmic response so soft sounds are still visible on meter
     */
    function peakToPercent(linear) {
        if (linear <= 0.0001) return 0;
        // dB from -60 to 0
        const db = 20 * Math.log10(linear);
        if (db <= -60) return 0;
        // Map [-60 dB, 0 dB] to [0%, 100%]
        return Math.min(100, Math.max(0, ((db + 60) / 60) * 100));
    }

    /**
     * Show notification toast
     */
    function showToast(message) {
        if (!elements.toast) return;
        elements.toastText.textContent = message;
        elements.toast.classList.add('show');
        setTimeout(() => {
            elements.toast.classList.remove('show');
        }, 3000);
    }

    /**
     * Render telemetry updates to DOM
     */
    function updateUI(data) {
        if (!data || !data.connected) return;

        const fmt = data.format;
        const meter = data.meter;
        const streaming = data.streaming;
        const vol = data.volume;

        currentSampleRate = fmt.sample_rate;
        currentBitDepth = fmt.bit_depth;

        // Rate & Quality Display
        const rateKHz = (fmt.sample_rate / 1000).toFixed(1);
        elements.sampleRateVal.textContent = rateKHz;
        elements.tierBadge.textContent = fmt.quality_tier;
        elements.tierBadge.className = `tier-badge ${fmt.badge_class}`;

        // Bit Depth & Bitrate
        elements.bitDepthVal.textContent = `${fmt.bit_depth}-Bit`;
        elements.bitrateVal.textContent = `${fmt.bitrate_kbps.toLocaleString()} kbps`;

        // Active Source
        const activeApps = streaming.active_sources || [];
        elements.activeSourceVal.textContent = activeApps.length > 0 ? activeApps[0] : (streaming.is_streaming ? 'Active Stream' : 'None');

        // Streaming Badges
        if (streaming.is_streaming) {
            elements.streamingBadge.textContent = 'STREAMING ACTIVE';
            elements.streamingBadge.style.color = 'var(--status-green)';
            elements.streamingBadge.style.borderColor = 'rgba(0, 230, 118, 0.3)';
            elements.streamStatusText.textContent = 'PCM STREAMING';
            elements.streamIndicator.style.opacity = '1';
        } else {
            elements.streamingBadge.textContent = 'STANDBY / IDLE';
            elements.streamingBadge.style.color = 'var(--text-muted)';
            elements.streamingBadge.style.borderColor = 'rgba(255, 255, 255, 0.1)';
            elements.streamStatusText.textContent = 'STANDBY';
            elements.streamIndicator.style.opacity = '0.5';
        }

        // VU Peak Meters
        const pctL = peakToPercent(meter.left);
        const pctR = peakToPercent(meter.right);

        elements.meterFillL.style.width = `${pctL}%`;
        elements.meterFillR.style.width = `${pctR}%`;

        // Peak Hold logic with decay
        if (pctL > peakHoldL) {
            peakHoldL = pctL;
        } else {
            peakHoldL = Math.max(pctL, peakHoldL - 1.2);
        }

        if (pctR > peakHoldR) {
            peakHoldR = pctR;
        } else {
            peakHoldR = Math.max(pctR, peakHoldR - 1.2);
        }

        elements.meterPeakL.style.left = `${peakHoldL}%`;
        elements.meterPeakR.style.left = `${peakHoldR}%`;

        // Peak dB readout
        const maxDb = Math.max(meter.left_db, meter.right_db);
        elements.peakReading.textContent = maxDb <= -59.5 ? '-∞ dB' : `${maxDb.toFixed(1)} dB`;

        // Master Volume (only sync if user is not actively dragging slider)
        if (!isUserDraggingVolume && vol) {
            elements.volumeSlider.value = vol.volume;
            elements.volumeVal.textContent = `${vol.volume}%`;
            elements.muteBtn.classList.toggle('muted', vol.mute);
        }

        // Active Rate Button Highlight
        const rateBtns = document.querySelectorAll('.rate-btn');
        rateBtns.forEach(btn => {
            const btnRate = parseInt(btn.getAttribute('data-rate'), 10);
            btn.classList.toggle('active', btnRate === currentSampleRate);
        });

        // Active Bit Depth Button Highlight
        elements.bitButtons.forEach(btn => {
            const btnBit = parseInt(btn.getAttribute('data-bit'), 10);
            btn.classList.toggle('active', btnBit === currentBitDepth);
        });

        // Sessions List
        if (data.sessions && Array.isArray(data.sessions)) {
            const activeSessions = data.sessions.filter(s => s.name && s.name !== 'System');
            elements.sessionCount.textContent = `${activeSessions.length} Detected`;
            elements.sessionsList.innerHTML = activeSessions.map(s => `
                <div class="session-item ${s.is_streaming ? 'active' : ''}">
                    <div class="session-app-info">
                        <span class="app-icon">${s.is_streaming ? '▶' : '■'}</span>
                        <span class="app-name">${s.name}</span>
                    </div>
                    <span class="session-status ${s.is_streaming ? 'streaming' : 'idle'}">
                        ${s.state}
                    </span>
                </div>
            `).join('');
        }
    }

    /**
     * Poll status API from server
     */
    async function fetchStatus() {
        try {
            const res = await fetch('/api/status');
            if (res.ok) {
                const data = await res.json();
                updateUI(data);
            }
        } catch (err) {
            console.warn('Status fetch error:', err);
        }
    }

    /**
     * Set Hardware Sample Rate and Bit Depth
     */
    async function setFormat(rate, bits) {
        elements.switchingMsg.classList.add('visible');
        try {
            const res = await fetch('/api/set_format', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sample_rate: rate, bit_depth: bits })
            });
            const data = await res.json();
            if (data.success) {
                showToast(`Hardware switched to ${(rate / 1000).toFixed(1)} kHz / ${bits}-bit`);
                updateUI(data.status);
            } else {
                showToast(`Error: ${data.error || 'Failed to switch format'}`);
            }
        } catch (err) {
            showToast(`Connection error switching rate`);
        } finally {
            elements.switchingMsg.classList.remove('visible');
        }
    }

    /**
     * Set Master Volume
     */
    async function setVolume(vol) {
        try {
            await fetch('/api/set_volume', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ volume: vol })
            });
        } catch (err) {
            console.warn('Volume set error:', err);
        }
    }

    /**
     * Toggle Mute
     */
    async function toggleMute() {
        const isMuted = elements.muteBtn.classList.contains('muted');
        const targetMute = !isMuted;
        elements.muteBtn.classList.toggle('muted', targetMute);
        try {
            await fetch('/api/toggle_mute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mute: targetMute })
            });
            showToast(targetMute ? 'Monitors Muted' : 'Monitors Unmuted');
        } catch (err) {
            elements.muteBtn.classList.toggle('muted', isMuted);
        }
    }

    /**
     * Play stereo test chime on Left / Right monitor
     */
    async function playTestTone(channel, freq) {
        try {
            await fetch('/api/test_tone', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel: channel, freq: freq })
            });
        } catch (err) {
            console.warn('Test tone error:', err);
        }
    }

    /**
     * Setup Event Listeners
     */
    function setupListeners() {
        // Rate Buttons
        const rateBtns = document.querySelectorAll('.rate-btn');
        rateBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetRate = parseInt(btn.getAttribute('data-rate'), 10);
                if (targetRate !== currentSampleRate) {
                    setFormat(targetRate, currentBitDepth);
                }
            });
        });

        // Bit Depth Buttons
        elements.bitButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetBit = parseInt(btn.getAttribute('data-bit'), 10);
                if (targetBit !== currentBitDepth) {
                    setFormat(currentSampleRate, targetBit);
                }
            });
        });

        // Volume Slider
        elements.volumeSlider.addEventListener('input', (e) => {
            isUserDraggingVolume = true;
            const val = parseInt(e.target.value, 10);
            elements.volumeVal.textContent = `${val}%`;

            clearTimeout(volumeDebounceTimer);
            volumeDebounceTimer = setTimeout(() => {
                setVolume(val);
                isUserDraggingVolume = false;
            }, 50);
        });

        elements.volumeSlider.addEventListener('change', (e) => {
            isUserDraggingVolume = false;
            setVolume(parseInt(e.target.value, 10));
        });

        // Mute Button
        elements.muteBtn.addEventListener('click', toggleMute);

        // Test Chimes
        elements.testLeftBtn.addEventListener('click', () => playTestTone('left', 440));
        elements.testBothBtn.addEventListener('click', () => playTestTone('both', 554));
        elements.testRightBtn.addEventListener('click', () => playTestTone('right', 880));

        // Refresh Button
        elements.refreshBtn.addEventListener('click', () => {
            fetchStatus();
            showToast('Refreshed DAC Telemetry');
        });
    }

    // Initialize App
    setupListeners();
    fetchStatus();

    // High-frequency polling (120ms) for responsive 60fps VU meter feel
    setInterval(fetchStatus, 120);

})();
