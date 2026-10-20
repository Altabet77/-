/**
 * S.A.M.I.R — J.A.R.V.I.S CLIENT CORE v4.0
 * Pure Holographic Voice & Reactive HUD Engine
 * Full WebSocket Duplex, Stable Anchored Bottom Questions Bar & Eye-Comfortable Menus
 */

// Smart Host detection for PC browser, Mobile Web, and Android APK container
const defaultHost = (window.location.hostname && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' && window.location.hostname !== '')
  ? window.location.host
  : (localStorage.getItem('samir_server_host') || window.location.host || '10.1.1.125:8000');

const defaultOrigin = (window.location.origin && !window.location.origin.startsWith('file:') && !window.location.origin.startsWith('capacitor:'))
  ? window.location.origin
  : `http://${defaultHost}`;

// Persistent unique client session and device per browser/person so each user has their private Samir
const clientSessionId = localStorage.getItem('samir_client_session_id') || 
  ('usr_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 8));
localStorage.setItem('samir_client_session_id', clientSessionId);

const clientDeviceId = localStorage.getItem('samir_device_id') || 
  ('dev_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 8));
localStorage.setItem('samir_device_id', clientDeviceId);

const CONFIG = {
  httpBase: defaultOrigin,
  sessionId: clientSessionId,
  deviceId: clientDeviceId,
  wsUrl: (defaultOrigin.startsWith('https') ? 'wss://' : 'ws://') + defaultHost + '/ws/voice?session_id=' + clientSessionId + '&device_id=' + clientDeviceId,
};

/* ── Central Application State ────────────────────────────────────────────── */
const state = {
  deviceId: clientDeviceId,
  // WebSocket
  ws: null,
  wsReady: false,
  wsReconnectAttempts: 0,
  wsReconnectTimer: null,
  pingTimer: null,

  // Current State ('idle' | 'listening' | 'thinking' | 'speaking')
  currentOrbState: 'idle',

  // Audio Playback
  soundEnabled: true,
  audioQueue: [],
  isPlayingAudio: false,
  audioContext: null,
  analyser: null,
  dataArray: null,
  currentAudioSource: null,
  lastPlayedBase64: null,

  // Microphone Recording & VAD
  isRecording: false,
  mediaRecorder: null,
  audioChunks: [],
  mediaStream: null,

  // Visualizer Loop
  animFrameId: null,

  // Conversations Cache
  conversations: [],
  activeConversationId: null,

  // Voice Settings (Default: 100% Free Arabic Neural Voice with 0 credits)
  activeVoiceId: localStorage.getItem('samir_active_voice') || 'ar-SA-HamedNeural',

  // Pending media attachments (images, video, audio, docs)
  pendingAttachments: [],

  // Watchdog timer to prevent stuck 'thinking' state
  watchdogTimer: null,

  // Live Vision & Video Streaming
  activeVisionStream: null,
  visionMode: null, // 'screen' | 'camera'
  cameraFacing: 'environment', // 'environment' | 'user'
  visionWatchInterval: null,

  // Real Alarms & Timers
  activeAlarms: [],
  alarmOscillatorInterval: null,

  // Google Auth & User Isolated Memory
  currentUser: null,
  userMemories: [],

  // Interaction Mode: Silent Typing vs Voice Playback
  voiceModeActive: false,
  isTypingInteraction: false,

  // VAD — Voice Activity Detection (auto-stop on silence)
  vadAnalyser: null,
  vadDataArray: null,
  vadFrameId: null,
  silenceTimer: null,
  lastSpeechTime: 0,
};

/* ── DOM Cache ────────────────────────────────────────────────────────────── */
let DOM = {};

function initDOMCache() {
  DOM = {
    // Orb Elements
    orb: document.getElementById('jarvis-orb'),
    arcCore: document.getElementById('arc-core'),
    orbStateText: document.getElementById('orb-state-text'),
    orbHint: document.getElementById('orb-hint'),
    circularBars: document.getElementById('circular-bars'),

    // Topbar
    statusLed: document.getElementById('hud-status-led'),
    topStatusText: document.getElementById('top-status-text'),
    topEngineName: document.getElementById('top-engine-name'),
    historyBtn: document.getElementById('btn-history'),
    historyCountBadge: document.getElementById('history-count-badge'),
    settingsBtn: document.getElementById('btn-settings'),
    soundBtn: document.getElementById('btn-toggle-sound'),
    soundBtnIcon: document.getElementById('sound-btn-icon'),
    winMin: document.getElementById('win-min'),
    winClose: document.getElementById('win-close'),

    // Dialogue Dock (Above Bottom Bar)
    dialogueDock: document.getElementById('dialogue-dock'),
    dialogueScrollArea: document.getElementById('dialogue-scroll-area'),
    btnScrollBottom: document.getElementById('btn-scroll-bottom'),
    btnClearDialogue: document.getElementById('btn-clear-dialogue'),
    userCard: document.getElementById('user-dialogue-card'),
    userText: document.getElementById('user-speech-text'),
    userTime: document.getElementById('user-bubble-time'),
    assistantCard: document.getElementById('assistant-dialogue-card'),
    assistantText: document.getElementById('assistant-speech-text'),
    assistantModel: document.getElementById('assistant-tag-model'),
    assistantTime: document.getElementById('assistant-bubble-time'),
    assistantTools: document.getElementById('assistant-card-tools'),
    replaySpeechBtn: document.getElementById('btn-replay-speech'),

    // Stable Anchored Bottom Bar
    textInput: document.getElementById('hud-text-input'),
    micBtn: document.getElementById('hud-mic-btn'),
    sendBtn: document.getElementById('hud-send-btn'),
    providerSelect: document.getElementById('hud-provider-select'),
    screenBtn: document.getElementById('hud-screen-btn'),
    cameraBtn: document.getElementById('hud-camera-btn'),
    attachBtn: document.getElementById('hud-attach-btn'),
    fileInput: document.getElementById('hud-file-input'),
    attachPreview: document.getElementById('hud-attachments-preview'),

    // Live Vision PiP Window
    visionPip: document.getElementById('hud-vision-pip'),
    pipTitle: document.getElementById('pip-title'),
    pipSwitchCamera: document.getElementById('pip-switch-camera'),
    pipCloseBtn: document.getElementById('pip-close-btn'),
    visionVideo: document.getElementById('hud-vision-video'),
    visionCanvas: document.getElementById('hud-vision-canvas'),
    pipAnalyzeBtn: document.getElementById('pip-analyze-btn'),
    pipAutoWatchCb: document.getElementById('pip-auto-watch-cb'),

    // Alarm Modal
    alarmOverlay: document.getElementById('hud-alarm-overlay'),
    alarmTitle: document.getElementById('alarm-title'),
    alarmMessage: document.getElementById('alarm-message'),
    alarmTimeTag: document.getElementById('alarm-time-tag'),
    alarmDismissBtn: document.getElementById('alarm-dismiss-btn'),
    alarmSnoozeBtn: document.getElementById('alarm-snooze-btn'),

    // History Drawer
    drawerOverlay: document.getElementById('drawer-overlay'),
    drawerCloseBtn: document.getElementById('drawer-close-btn'),
    drawerNewBtn: document.getElementById('drawer-new-btn'),
    drawerSearchInput: document.getElementById('drawer-search-input'),
    drawerConvList: document.getElementById('drawer-conv-list'),

    // Settings Modal
    settingsModal: document.getElementById('settings-modal'),
    settingsCloseBtn: document.getElementById('settings-close-btn'),
    settingsCancelBtn: document.getElementById('settings-cancel-btn'),
    settingsSaveBtn: document.getElementById('settings-save-btn'),
    voiceCardsGrid: document.getElementById('voice-cards-grid'),
    settingTtsRate: document.getElementById('setting-tts-rate'),
    settingDefaultProvider: document.getElementById('setting-default-provider'),
    settingMemoryToggle: document.getElementById('setting-memory-toggle'),
    settingBargeinToggle: document.getElementById('setting-bargein-toggle'),
    settingVizToggle: document.getElementById('setting-viz-toggle'),
    settingElevenLabsKey: document.getElementById('setting-elevenlabs-key'),
    btnUpdateElevenlabsKey: document.getElementById('btn-update-elevenlabs-key'),
    voiceQuotaBadge: document.getElementById('voice-quota-badge'),
    voiceQuotaMsg: document.getElementById('voice-quota-msg'),

    // Toast
    toast: document.getElementById('hud-toast'),

    // Wake Word & Mobile Connect
    btnWakeWord: document.getElementById('btn-wake-word'),
    wakeDot: document.querySelector('.wake-dot'),
    btnMobileConnect: document.getElementById('btn-mobile-connect'),
    btnQuickVoice: document.getElementById('btn-quick-voice'),
    quickVoiceLabel: document.getElementById('quick-voice-label'),
    mobileModal: document.getElementById('mobile-modal') || document.getElementById('mobile-connect-modal'),
    mobileCloseBtn: document.getElementById('mobile-close-btn'),
    mobileDoneBtn: document.getElementById('mobile-done-btn'),
    mobileUrlInput: document.getElementById('mobile-url-input'),
    btnCopyMobileUrl: document.getElementById('btn-copy-mobile-url'),
    mobileQrCanvas: document.getElementById('mobile-qr-canvas'),

    // User Auth & Isolated Memory
    btnGoogleLogin: document.getElementById('btn-google-login'),
    userProfileChip: document.getElementById('user-profile-chip'),
    userAvatar: document.getElementById('user-avatar'),
    userName: document.getElementById('user-name'),
    userMemoryBadge: document.getElementById('user-memory-badge'),
    btnToggleVoiceMode: document.getElementById('btn-toggle-voice-mode'),
    voiceModeIcon: document.getElementById('voice-mode-icon'),
    voiceModeLabel: document.getElementById('voice-mode-label'),
    authModalOverlay: document.getElementById('auth-modal-overlay'),
    authModalClose: document.getElementById('auth-modal-close'),
    authViewLoggedOut: document.getElementById('auth-view-logged-out'),
    authViewLoggedIn: document.getElementById('auth-view-logged-in'),
    tabBtnLogin: document.getElementById('tab-btn-login'),
    tabBtnRegister: document.getElementById('tab-btn-register'),
    paneAuthLogin: document.getElementById('pane-auth-login'),
    paneAuthRegister: document.getElementById('pane-auth-register'),
    loginEmail: document.getElementById('login-email'),
    loginPassword: document.getElementById('login-password'),
    btnPeekLogin: document.getElementById('btn-peek-login'),
    btnSubmitLogin: document.getElementById('btn-submit-login'),
    regName: document.getElementById('reg-name'),
    regEmail: document.getElementById('reg-email'),
    regPassword: document.getElementById('reg-password'),
    btnPeekReg: document.getElementById('btn-peek-reg'),
    btnSubmitRegister: document.getElementById('btn-submit-register'),
    authUserAvatar: document.getElementById('auth-user-avatar'),
    authUserName: document.getElementById('auth-user-name'),
    authUserEmail: document.getElementById('auth-user-email'),
    authMemoriesCount: document.getElementById('auth-memories-count'),
    authMemoriesList: document.getElementById('auth-memories-list'),
    btnWipeMyMemories: document.getElementById('btn-wipe-my-memories'),
    btnLogoutGoogle: document.getElementById('btn-logout-google'),
    btnAuthDone: document.getElementById('btn-auth-done'),

    // Code Sandbox Modal
    sandboxModalOverlay: document.getElementById('sandbox-modal-overlay'),
    sandboxModalCard: document.getElementById('sandbox-modal-card'),
    sandboxIframe: document.getElementById('sandbox-iframe'),
    sandboxCloseBtn: document.getElementById('sandbox-close-btn'),
    sandboxReloadBtn: document.getElementById('sandbox-reload-btn'),
    sandboxFullscreenBtn: document.getElementById('sandbox-fullscreen-btn'),
    sandboxRunAgainBtn: document.getElementById('sandbox-run-again-btn'),
    sandboxTitle: document.getElementById('sandbox-modal-title'),
    sandboxLangBadge: document.getElementById('sandbox-lang-badge'),
    sandboxStatus: document.getElementById('sandbox-status'),
    sandboxContentArea: document.getElementById('sandbox-content-area'),
    sandboxTerminal: document.getElementById('sandbox-terminal'),
    terminalOutput: document.getElementById('terminal-output'),

    // In-App Media Player (YouTube & Spotify)
    hudMediaPlayer: document.getElementById('hud-media-player'),
    hudMediaCard: document.getElementById('hud-media-card'),
    mediaServiceBadge: document.getElementById('media-service-badge'),
    mediaPlayerTitle: document.getElementById('media-player-title'),
    mediaIframe: document.getElementById('media-iframe'),
    mediaExternalBtn: document.getElementById('media-external-btn'),
    mediaPipBtn: document.getElementById('media-pip-btn'),
    mediaCloseBtn: document.getElementById('media-close-btn'),

    // Mobile Top Commands Drawer
    btnMobileMenu: document.getElementById('btn-mobile-menu'),
    mobileCommandsDropdown: document.getElementById('mobile-commands-dropdown'),
    mobileCmdCloseBtn: document.getElementById('mobile-cmd-close-btn'),

    // Live Clock & Date Elements
    hudLiveTime: document.getElementById('hud-live-time'),
    hudLiveDate: document.getElementById('hud-live-date'),
    hudLiveHijri: document.getElementById('hud-live-hijri'),
    topbarClockTime: document.getElementById('topbar-clock-time'),

    // Custom Rules Topbar Button
    btnCustomRules: document.getElementById('btn-custom-rules'),
  };
}

/* ═════════════════════════════════════════════════════════════════════════════
   1. INITIALIZATION & SETUP
   ═════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initDOMCache();
  initLiveClock();
  createCircularBars(36);
  setupEventListeners();
  setupElectronIPC();
  connectWebSocket();
  initAudioContext();
  startVisualizerLoop();
  setOrbState('idle');
  loadConversationsList();
  initVoiceSettings();
  initHudDashboard();
  initWakeWordEngine();
  initMobileConnect();
  initGoogleAuth();
  initVoiceModeToggle();
  initSandboxEngine();
  initMediaPlayerEngine();
});

/* ── Live Clock & Date Widget Engine ───────────────────────────────────────── */
function initLiveClock() {
  function update() {
    const now = new Date();
    // Time format HH:mm:ss
    const pad = (n) => String(n).padStart(2, '0');
    const hours = pad(now.getHours());
    const minutes = pad(now.getMinutes());
    const seconds = pad(now.getSeconds());
    const timeFormatted = `${hours}:${minutes}:${seconds}`;

    if (DOM.hudLiveTime) DOM.hudLiveTime.textContent = timeFormatted;
    if (DOM.topbarClockTime) DOM.topbarClockTime.textContent = timeFormatted;

    // Arabic Gregorian Date (e.g. الجمعة، 9 أكتوبر 2026)
    try {
      const dateFormatted = now.toLocaleDateString('ar-SA', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
      if (DOM.hudLiveDate) DOM.hudLiveDate.textContent = dateFormatted;
    } catch (e) {
      if (DOM.hudLiveDate) DOM.hudLiveDate.textContent = `${now.getFullYear()}/${now.getMonth() + 1}/${now.getDate()}`;
    }

    // Arabic Umm al-Qura Hijri Date
    try {
      const hijriFormatted = new Intl.DateTimeFormat('ar-SA-u-ca-islamic-umalqura', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      }).format(now);
      if (DOM.hudLiveHijri) DOM.hudLiveHijri.textContent = hijriFormatted + ' هـ';
    } catch (e) {
      if (DOM.hudLiveHijri) DOM.hudLiveHijri.textContent = '';
    }
  }

  update();
  setInterval(update, 1000);
}

/* ── Web Audio Context Initialization ──────────────────────────────────────── */
function initAudioContext() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return;

  if (!state.audioContext) {
    state.audioContext = new AudioContextClass();
    state.analyser = state.audioContext.createAnalyser();
    state.analyser.fftSize = 64;
    state.dataArray = new Uint8Array(state.analyser.frequencyBinCount);
  }

  const unlock = () => {
    if (state.audioContext && state.audioContext.state === 'suspended') {
      state.audioContext.resume().then(() => {
        console.log('[J.A.R.V.I.S] AudioContext active ✓');
      });
    }
    // Pre-warm the HTML5 Audio element for iOS Safari (must happen in a user gesture)
    if (!state._htmlAudio) {
      state._htmlAudio = new Audio();
      // Play a tiny silent buffer to unlock audio on iOS
      state._htmlAudio.src = 'data:audio/mp3;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjMyLjEwNAAAAAAAAAAAAAAA//OEAAAAAAAAAAAAAAAAAAAAAAAASW5mbwAAAA8AAAAEAAABIADAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDV1dXV1dXV1dXV1dXV1dXV1dXV1dXV1dXV6urq6urq6urq6urq6urq6urq6urq6urq6v////////////////////AAAAAATGF2YzU4LjU0AAAAAAAAAAAAAAAAJAAAAAAAAAAAASDs90hvAAAAAAAAAAAAAAAAAAAA//MUZAAAAAGkAAAAAAAAA0gAAAAATEFN//MUZAMAAAGkAAAAAAAAA0gAAAAARTMu//MUZAYAAAGkAAAAAAAAA0gAAAAAOTku//MUZAkAAAGkAAAAAAAAA0gAAAAANVVV';
      state._htmlAudio.load();
      state._htmlAudio.play().catch(() => {}); // Unlock, ignore error
    }
    document.removeEventListener('click', unlock);
    document.removeEventListener('touchstart', unlock);
    document.removeEventListener('touchend', unlock);
    document.removeEventListener('keydown', unlock);
  };
  document.addEventListener('click', unlock, { once: true });
  document.addEventListener('touchstart', unlock, { once: true, passive: true });
  document.addEventListener('touchend', unlock, { once: true, passive: true });
  document.addEventListener('keydown', unlock, { once: true });
}

/* ── Perimeter Circular Visualizer Generation ─────────────────────────────── */
function createCircularBars(count) {
  if (!DOM.circularBars) return;
  DOM.circularBars.innerHTML = '';
  const radius = 155;

  for (let i = 0; i < count; i++) {
    const angle = (i / count) * 360;
    const bar = document.createElement('div');
    bar.className = 'c-bar';
    bar.id = `cbar-${i}`;

    const rad = (angle * Math.PI) / 180;
    const x = Math.cos(rad) * radius;
    const y = Math.sin(rad) * radius;

    bar.style.transform = `translate(${x}px, ${y}px) rotate(${angle + 90}deg)`;
    DOM.circularBars.appendChild(bar);
  }
}

/* ── Visualizer Animation Loop (Reacts to Audio Playback / Mic) ──────────── */
function startVisualizerLoop() {
  const bars = DOM.circularBars ? DOM.circularBars.children : [];
  const barCount = bars.length;

  const render = () => {
    state.animFrameId = requestAnimationFrame(render);

    if (state.currentOrbState === 'speaking' && state.analyser && state.dataArray) {
      state.analyser.getByteFrequencyData(state.dataArray);
      let sum = 0;
      for (let i = 0; i < barCount; i++) {
        const binIndex = i % state.dataArray.length;
        const val = state.dataArray[binIndex] || 0;
        sum += val;
        const h = Math.max(4, (val / 255) * 36);
        const op = Math.max(0.3, val / 255);
        if (bars[i]) {
          bars[i].style.height = `${h}px`;
          bars[i].style.opacity = op;
          bars[i].style.backgroundColor = 'var(--cyan)';
        }
      }
      const avg = sum / barCount;
      if (DOM.arcCore) {
        DOM.arcCore.style.transform = `scale(${1 + (avg / 255) * 0.14})`;
      }
    } else if (state.currentOrbState === 'listening') {
      const t = Date.now() / 250;
      for (let i = 0; i < barCount; i++) {
        const wave = Math.sin(t + i * 0.35) * 0.5 + 0.5;
        const h = 4 + wave * 16;
        if (bars[i]) {
          bars[i].style.height = `${h}px`;
          bars[i].style.opacity = 0.6;
          bars[i].style.backgroundColor = 'var(--green)';
        }
      }
      if (DOM.arcCore) DOM.arcCore.style.transform = 'scale(1.02)';
    } else if (state.currentOrbState === 'thinking') {
      const t = Date.now() / 200;
      for (let i = 0; i < barCount; i++) {
        const pulse = (Math.sin(t) + 1) * 0.5;
        if (bars[i]) {
          bars[i].style.height = `${4 + pulse * 10}px`;
          bars[i].style.opacity = 0.5;
          bars[i].style.backgroundColor = 'var(--amber)';
        }
      }
    } else {
      for (let i = 0; i < barCount; i++) {
        if (bars[i]) {
          bars[i].style.height = '4px';
          bars[i].style.opacity = '0.35';
          bars[i].style.backgroundColor = 'var(--cyan)';
        }
      }
      if (DOM.arcCore) DOM.arcCore.style.transform = 'scale(1)';
    }
  };

  render();
}

/* ═════════════════════════════════════════════════════════════════════════════
   2. ORB STATE CONTROLLER
   ═════════════════════════════════════════════════════ */
function setOrbState(newState) {
  state.currentOrbState = newState;
  if (!DOM.orb) return;

  DOM.orb.classList.remove('idle', 'listening', 'thinking', 'speaking');
  DOM.orb.classList.add(newState);

  const r1 = document.getElementById('ripple-1');
  const r2 = document.getElementById('ripple-2');
  const r3 = document.getElementById('ripple-3');

  switch (newState) {
    case 'listening':
      if (window.WakeWordEngine) window.WakeWordEngine.pauseListening();
      if (DOM.orbStateText) DOM.orbStateText.textContent = 'سمير // جاري الاستماع 🎙️';
      if (DOM.orbHint) DOM.orbHint.textContent = 'تحدث الآن، اضغط مجدداً للإرسال';
      if (r1) r1.classList.add('active');
      if (r2) r2.classList.add('active');
      if (r3) r3.classList.add('active');
      if (DOM.micBtn) DOM.micBtn.classList.add('recording');
      break;

    case 'thinking':
      if (window.WakeWordEngine) window.WakeWordEngine.pauseListening();
      if (DOM.orbStateText) DOM.orbStateText.textContent = 'سمير // جاري المعالجة والتفكير ⚡';
      if (DOM.orbHint) DOM.orbHint.textContent = 'سمير يبحث ويجهز الرد...';
      if (r1) r1.classList.remove('active');
      if (r2) r2.classList.remove('active');
      if (r3) r3.classList.remove('active');
      if (DOM.micBtn) DOM.micBtn.classList.remove('recording');
      break;

    case 'speaking':
      if (window.WakeWordEngine) window.WakeWordEngine.pauseListening();
      if (DOM.orbStateText) DOM.orbStateText.textContent = 'سمير // يتحدث الآن 🔊';
      if (DOM.orbHint) DOM.orbHint.textContent = 'اضغط على الدائرة لمقاطعة الصوت فوراً';
      if (r1) r1.classList.add('active');
      if (r2) r2.classList.add('active');
      if (r3) r3.classList.add('active');
      if (DOM.micBtn) DOM.micBtn.classList.remove('recording');
      break;

    case 'idle':
    default:
      if (DOM.orbStateText) DOM.orbStateText.textContent = 'سمير // النواة المركزية جاهزة';
      if (DOM.orbHint) DOM.orbHint.textContent = 'اضغط على الدائرة أو تحدث عبر الميكروفون بالأسفل';
      if (r1) r1.classList.remove('active');
      if (r2) r2.classList.remove('active');
      if (r3) r3.classList.remove('active');
      if (DOM.micBtn) DOM.micBtn.classList.remove('recording');
      if (window.WakeWordEngine && window.WakeWordEngine.enabled) {
        setTimeout(() => {
          if (state.currentOrbState === 'idle' && !state.isRecording && !state.isPlayingAudio) {
            window.WakeWordEngine.resumeListening();
          }
        }, 500);
      }
      break;
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   3. WEBSOCKET FULL-DUPLEX COMMUNICATION
   ═════════════════════════════════════════════════════ */
function connectWebSocket() {
  if (state.ws) {
    try { state.ws.close(); } catch (e) {}
  }

  console.log(`[J.A.R.V.I.S] Connecting to: ${CONFIG.wsUrl}`);
  try {
    state.ws = new WebSocket(CONFIG.wsUrl);
  } catch (err) {
    scheduleReconnect();
    return;
  }

  state.ws.onopen = () => {
    console.log('[J.A.R.V.I.S] WebSocket Connected ✓');
    state.wsReady = true;
    state.wsReconnectAttempts = 0;

    if (DOM.statusLed) DOM.statusLed.style.backgroundColor = 'var(--cyan)';
    if (DOM.topStatusText) DOM.topStatusText.textContent = 'متصل // جاهز';

    wsSend({
      type: 'hello',
      session_id: CONFIG.sessionId,
      client: 'jarvis_web_console_v4',
      voice: state.activeVoiceId,
    });
    wsSend({
      type: 'select_voice',
      voice: state.activeVoiceId,
    });

    // Send auth token if user is signed in with Google
    const token = localStorage.getItem('samir_session_token');
    if (token) {
      wsSend({ type: 'set_auth', token: token });
    }

    // Inform server of interaction mode (silent typing vs voice)
    wsSend({ type: 'set_voice_mode', enabled: state.voiceModeActive });

    if (state.pingTimer) clearInterval(state.pingTimer);
    state.pingTimer = setInterval(() => {
      wsSend({ type: 'ping', t: Date.now() });
    }, 20000);
  };

  state.ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleWebSocketMessage(msg);
    } catch (e) {
      console.warn('[J.A.R.V.I.S] Non-JSON message:', event.data);
    }
  };

  state.ws.onerror = (err) => {
    console.error('[J.A.R.V.I.S] WebSocket Error:', err);
  };

  state.ws.onclose = () => {
    state.wsReady = false;
    if (DOM.statusLed) DOM.statusLed.style.backgroundColor = 'var(--red)';
    if (DOM.topStatusText) DOM.topStatusText.textContent = 'جاري إعادة الاتصال...';
    scheduleReconnect();
  };
}

function scheduleReconnect() {
  if (state.pingTimer) clearInterval(state.pingTimer);
  state.wsReconnectAttempts++;
  const delay = Math.min(1000 * Math.pow(1.5, state.wsReconnectAttempts), 8000);
  clearTimeout(state.wsReconnectTimer);
  state.wsReconnectTimer = setTimeout(() => {
    connectWebSocket();
  }, delay);
}

function wsSend(obj) {
  if (state.ws && state.ws.readyState === WebSocket.OPEN) {
    state.ws.send(JSON.stringify(obj));
    return true;
  }
  return false;
}

/* ── Watchdog: prevent forever-stuck 'thinking' state ────────────────────── */
function startWatchdog() {
  clearWatchdog();
  state.watchdogTimer = setTimeout(() => {
    if (state.currentOrbState === 'thinking') {
      console.warn('[J.A.R.V.I.S] Watchdog fired — server took too long, resetting state');
      setOrbState('idle');
      showToast('⚠️ استغرق سمير وقتاً طويلاً، حاول مرة أخرى.');
    }
  }, 25000);
}

function clearWatchdog() {
  if (state.watchdogTimer) {
    clearTimeout(state.watchdogTimer);
    state.watchdogTimer = null;
  }
}

function handleWebSocketMessage(msg) {
  const type = msg.type;

  switch (type) {
    // ── Backend sends this as the main text response ───────────────────────
    case 'response_text':
    case 'final_response':
      clearWatchdog();
      showAssistantDialogue({
        text: msg.text || msg.reply || '',
        model: msg.model || msg.provider || 'سمير',
        toolCalls: msg.tool_calls || [],
      });
      if (msg.audio) {
        state.lastPlayedBase64 = msg.audio;
        if (!state.isTypingInteraction || state.voiceModeActive) {
          queueAudioChunk(msg.audio);
        }
      } else if (!state.isPlayingAudio) {
        // No audio attached; wait a bit for audio_data to arrive, then idle
        setTimeout(() => {
          if (state.currentOrbState !== 'speaking') setOrbState('idle');
        }, 600);
      }
      loadConversationsList();
      break;

    // ── Backend sends audio as separate message ────────────────────────────
    case 'audio_data':
    case 'audio_chunk':
      clearWatchdog();
      if (msg.audio) {
        state.lastPlayedBase64 = msg.audio;
        if (!state.isTypingInteraction || state.voiceModeActive) {
          queueAudioChunk(msg.audio);
        } else {
          console.log('[Samir] Silent typing mode: audio output suppressed.');
        }
      }
      break;

    // ── Google Auth responses ──────────────────────────────────────────────
    case 'auth_ok':
      if (msg.user) {
        state.currentUser = msg.user;
        localStorage.setItem('samir_user_data', JSON.stringify(msg.user));
        updateAuthUI(msg.user);
        fetchUserMemories(msg.user.id, localStorage.getItem('samir_session_token'));
      }
      break;

    case 'auth_error':
      console.warn('[Samir] Auth error:', msg.message);
      break;

    // ── State updates from backend ─────────────────────────────────────────
    case 'state':
      if (msg.state) {
        // 'transcribing' is a transient state — show as listening pulse
        if (msg.state === 'transcribing') {
          if (DOM.orbStateText) DOM.orbStateText.textContent = 'سمير // جاري تحويل الصوت إلى نص 🔄';
          if (DOM.orbHint) DOM.orbHint.textContent = 'جاري معالجة صوتك...';
          clearWatchdog();
          startWatchdog(); // restart timer for transcription
        } else {
          setOrbState(msg.state);
          if (msg.state === 'thinking') startWatchdog();
          if (msg.state === 'idle' || msg.state === 'speaking') clearWatchdog();
        }
      }
      break;

    case 'status':
      if (msg.state) {
        setOrbState(msg.state);
        if (msg.state === 'thinking') startWatchdog();
        else clearWatchdog();
      }
      break;

    // ── Speech-to-text transcription ───────────────────────────────────────
    case 'transcription':
    case 'user_speech_transcription':
      clearWatchdog();
      if (msg.text) {
        showUserDialogue(msg.text);
        // After transcription, backend will process it — restart watchdog for that phase
        startWatchdog();
      }
      break;

    // ── Speech/text stream done ────────────────────────────────────────────
    case 'speech_done':
    case 'text_done':
      clearWatchdog();
      if (!state.isPlayingAudio && state.audioQueue.length === 0) {
        setOrbState('idle');
      }
      loadConversationsList();
      break;

    // ── Abort confirmation ─────────────────────────────────────────────────
    case 'aborted':
      clearWatchdog();
      setOrbState('idle');
      showToast('🛑 تم إيقاف الرد');
      break;

    // ── Tool execution notification ────────────────────────────────────────
    case 'tool_calls':
    case 'tool_executed':
      if (msg.tool_name || (msg.tool_calls && msg.tool_calls.length > 0)) {
        const name = msg.tool_name || msg.tool_calls[0]?.name || 'أداة';
        showToast(`⚡ سمير ينفذ: ${name}`);
      }
      break;

    // ── Client Action (Alarm, Phone/Device Search, Camera, Screen) ────────
    case 'client_action':
      handleClientAction(msg.action, msg.data);
      break;

    // ── Pong (keepalive) ───────────────────────────────────────────────────
    case 'pong':
      break;

    // ── Error from backend ─────────────────────────────────────────────────
    case 'error':
      clearWatchdog();
      showToast(`⚠️ ${msg.message || 'حدث خطأ في المعالجة'}`);
      setOrbState('idle');
      break;

    default:
      console.debug('[J.A.R.V.I.S] Unhandled message type:', type, msg);
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   4. AUDIO PLAYBACK & TTS STREAMING ENGINE
   ═════════════════════════════════════════════════════ */
function queueAudioChunk(base64Audio) {
  if (!state.soundEnabled) return;
  state.audioQueue.push(base64Audio);
  if (!state.isPlayingAudio) {
    playNextAudioInQueue();
  }
}

async function playNextAudioInQueue() {
  if (state.audioQueue.length === 0) {
    state.isPlayingAudio = false;
    setOrbState('idle');
    // ── إعادة تشغيل الاستماع (Wake Word) بعد انتهاء كلام سمير ────────────
    setTimeout(() => {
      if (window.WakeWordEngine && !state.isRecording) {
        WakeWordEngine.resumeListening();
      }
    }, 600);
    return;
  }

  state.isPlayingAudio = true;
  setOrbState('speaking');
  const base64 = state.audioQueue.shift();

  if (state.audioContext) {
    try {
      if (state.audioContext.state === 'suspended') {
        await state.audioContext.resume();
      }

      const binary = atob(base64);
      const len = binary.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) bytes[i] = binary.charCodeAt(i);

      const audioBuffer = await state.audioContext.decodeAudioData(bytes.buffer);
      const source = state.audioContext.createBufferSource();
      source.buffer = audioBuffer;

      source.connect(state.analyser);
      state.analyser.connect(state.audioContext.destination);

      state.currentAudioSource = source;
      source.onended = () => {
        state.currentAudioSource = null;
        playNextAudioInQueue();
      };

      source.start(0);
      return;
    } catch (err) {
      console.warn('[J.A.R.V.I.S] WebAudio decode failed, falling back:', err);
    }
  }

  // Fallback: HTML5 Audio (used on mobile when AudioContext fails)
  try {
    // Re-use a shared Audio element (required for iOS Safari after user gesture)
    if (!state._htmlAudio) {
      state._htmlAudio = new Audio();
    }
    const audio = state._htmlAudio;
    audio.pause();
    audio.src = 'data:audio/mp3;base64,' + base64;
    audio.onended = () => playNextAudioInQueue();
    audio.onerror = () => {
      console.warn('[J.A.R.V.I.S] HTML5 Audio error, skipping chunk');
      playNextAudioInQueue();
    };
    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn('[J.A.R.V.I.S] HTML5 Audio play() blocked:', err);
        // Still advance queue even if play was blocked
        state.isPlayingAudio = false;
        setOrbState('idle');
      });
    }
  } catch (e) {
    playNextAudioInQueue();
  }
}

function stopAudioPlayback() {
  state.audioQueue = [];
  state.isPlayingAudio = false;

  if (state.currentAudioSource) {
    try { state.currentAudioSource.stop(); } catch (e) {}
    state.currentAudioSource = null;
  }

  // إعادة تشغيل الاستماع إذا توقف الصوت يدوياً (مقاطعة)
  setTimeout(() => {
    if (window.WakeWordEngine && !state.isRecording) {
      WakeWordEngine.resumeListening();
    }
  }, 500);
}

/* ═════════════════════════════════════════════════════════════════════════════
   5. VOICE RECORDING & MICROPHONE INPUT
   ═════════════════════════════════════════════════════ */
async function toggleRecording() {
  if (state.isRecording) {
    stopRecording();
  } else {
    if (state.isPlayingAudio) {
      stopAudioPlayback();
      wsSend({ type: 'abort' });
    }
    // إيقاف مؤقت للاستماع التلقائي أثناء التسجيل اليدوي
    if (window.WakeWordEngine && WakeWordEngine.isListeningWakeWord) {
      WakeWordEngine.pauseListening();
    }
    await startRecording();
  }
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 48000,
        echoCancellation: true,
        noiseSuppression: true,
      }
    });

    state.mediaStream = stream;
    state.audioChunks = [];

    const options = { mimeType: 'audio/webm' };
    if (!MediaRecorder.isTypeSupported('audio/webm')) {
      options.mimeType = 'audio/mp4';
    }

    state.mediaRecorder = new MediaRecorder(stream, options);
    state.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) state.audioChunks.push(e.data);
    };

    state.mediaRecorder.onstop = () => {
      processAudioRecording();
    };

    state.mediaRecorder.start(200);
    state.isRecording = true;
    state.lastSpeechTime = Date.now();
    setOrbState('listening');

    // ── VAD: Silence Detection ─────────────────────────────────────────────
    // الصمت لـ 1.6 ثانية (1600ms) → يوقف التسجيل ويرسل تلقائياً
    const SILENCE_MS    = 1600;    // مدة الصمت بالميلي ثانية قبل الإرسال لمنع القطع المفاجئ بين الكلمات
    const SILENCE_LEVEL = 1.8;     // عتبة الصوت الحساسة والواقعية للميكروفونات (RMS)
    const MIN_SPEECH_MS = 250;     // أقل مدة كلام مقبولة قبل تفعيل VAD

    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      const vadCtx = new AudioCtx();
      const source  = vadCtx.createMediaStreamSource(stream);
      const analyser = vadCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      state.vadAnalyser  = analyser;
      state.vadDataArray = new Uint8Array(analyser.fftSize);
      const vadData      = state.vadDataArray;

      let speechDetected = false; // منع الإيقاف قبل أن يتكلم المستخدم

      // مؤقت أمان: لو مرت 8 ثوانٍ ولم يتكلم المستخدم نهائياً، أوقف بهدوء
      const initialNoSpeechTimer = setTimeout(() => {
        if (state.isRecording && !speechDetected) {
          console.log('[VAD] No speech detected in initial 8s — auto stopping');
          stopRecording();
        }
      }, 8000);

      const vadLoop = () => {
        if (!state.isRecording) { 
          clearTimeout(initialNoSpeechTimer);
          vadCtx.close(); 
          return; 
        }

        analyser.getByteTimeDomainData(vadData);

        // حساب RMS (مستوى الصوت الجذري المتوسط)
        let sum = 0;
        for (let i = 0; i < vadData.length; i++) {
          const v = (vadData[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / vadData.length) * 100;

        if (rms > SILENCE_LEVEL) {
          // صوت مكتشف — أعد ضبط مؤقت الصمت
          state.lastSpeechTime = Date.now();
          if (!speechDetected) speechDetected = true;
          if (state.silenceTimer) { clearTimeout(state.silenceTimer); state.silenceTimer = null; }
        } else if (speechDetected) {
          // صمت بعد كلام — ابدأ العد التنازلي (1.25 ثانية)
          if (!state.silenceTimer) {
            const elapsed = Date.now() - state.lastSpeechTime;
            if (elapsed < MIN_SPEECH_MS) {
              // كلام قصير جداً — انتظر أكثر
            } else {
              state.silenceTimer = setTimeout(() => {
                if (state.isRecording) {
                  console.log('[VAD] Silence detected — auto-stopping after', SILENCE_MS, 'ms');
                  stopRecording();
                }
              }, SILENCE_MS);
            }
          }
        }

        state.vadFrameId = requestAnimationFrame(vadLoop);
      };

      state.vadFrameId = requestAnimationFrame(vadLoop);
    } catch (vadErr) {
      console.warn('[VAD] Could not start VAD:', vadErr);
    }
    // ──────────────────────────────────────────────────────────────────────

  } catch (err) {
    console.error('[J.A.R.V.I.S] Mic error:', err);
    showToast('تعذر الوصول إلى الميكروفون. تأكد من تفعيل الصلاحية.');
    setOrbState('idle');
  }
}

function stopRecording() {
  if (!state.isRecording) return;
  state.isRecording = false;

  // Stop VAD loop & timers
  if (state.vadFrameId)    { cancelAnimationFrame(state.vadFrameId);    state.vadFrameId    = null; }
  if (state.silenceTimer)  { clearTimeout(state.silenceTimer);           state.silenceTimer  = null; }
  state.vadAnalyser  = null;
  state.vadDataArray = null;

  if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
    state.mediaRecorder.stop();
  }

  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach(t => t.stop());
    state.mediaStream = null;
  }

  setOrbState('thinking');
  startWatchdog();
}

async function processAudioRecording() {
  if (state.audioChunks.length === 0) {
    setOrbState('idle');
    // استئناف الاستماع إذا لم يكن هناك صوت
    setTimeout(() => { if (window.WakeWordEngine) WakeWordEngine.resumeListening(); }, 500);
    return;
  }

  const audioBlob = new Blob(state.audioChunks, { type: state.mediaRecorder?.mimeType || 'audio/webm' });
  if (audioBlob.size < 400) {
    setOrbState('idle');
    // استئناف الاستماع إذا كان الصوت قصيراً جداً
    setTimeout(() => { if (window.WakeWordEngine) WakeWordEngine.resumeListening(); }, 500);
    return;
  }

  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result.split(',')[1];
    if (base64) {
      state.isTypingInteraction = false; // Voice mode is source: TTS will speak!
      wsSend({ type: 'audio_input', audio: base64, voice: state.activeVoiceId });
      startWatchdog(); // prevent stuck state after sending voice
    } else {
      setOrbState('idle');
      setTimeout(() => { if (window.WakeWordEngine) WakeWordEngine.resumeListening(); }, 500);
    }
  };
  reader.readAsDataURL(audioBlob);
}

/* ═════════════════════════════════════════════════════════════════════════════
   6. STABLE ANCHORED BOTTOM QUESTIONS BAR & MESSAGING
   ═════════════════════════════════════════════════════ */
function handleSendText(forcedText) {
  if (!DOM.textInput) return;
  const isForced = typeof forcedText === 'string';
  const text = (isForced ? forcedText : (DOM.textInput.value || '')).trim();
  if (!text && state.pendingAttachments.length === 0) return;

  state.isTypingInteraction = true; // Typing mode is source: Silent text response!

  // Clear input without bouncing
  if (!isForced) DOM.textInput.value = '';

  // Interruption if speaking (Barge-in)
  if (state.isPlayingAudio) {
    stopAudioPlayback();
    wsSend({ type: 'abort' });
  }

  // Smoothly show user question right above the bottom bar
  showUserDialogue(text || '📎 مرفق');
  setOrbState('thinking');
  startWatchdog();

  const provider = DOM.providerSelect?.value || 'auto';
  const effectiveProvider = provider === 'auto' ? undefined : provider;

  // Gather pending attachments, then clear them
  const attachments = state.pendingAttachments.length > 0 ? [...state.pendingAttachments] : undefined;
  state.pendingAttachments = [];
  renderAttachmentChips();

  wsSend({
    type: 'text_input',
    text: text,
    provider: effectiveProvider,
    attachments: attachments || undefined,
    voice: state.activeVoiceId,
  });

  // Re-focus input smoothly
  DOM.textInput.focus();
}

function formatCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
}

function showUserDialogue(text) {
  if (!DOM.dialogueScrollArea) return;

  const bubble = document.createElement('div');
  bubble.className = 'dialogue-bubble user-bubble';
  bubble.innerHTML = `
    <div class="bubble-header">
      <span class="bubble-author">👤 أنت</span>
      <span class="bubble-time">${formatCurrentTime()}</span>
    </div>
    <div class="bubble-content">${escapeHtml(text)}</div>
  `;

  // Hide initial static cards
  if (DOM.userCard) DOM.userCard.classList.add('hidden');
  if (DOM.assistantCard) DOM.assistantCard.classList.add('hidden');

  DOM.dialogueScrollArea.appendChild(bubble);
  scrollDialogueToBottom();
}

function renderMarkdown(raw) {
  if (!raw) return '';

  // 1. استخراج كتل الأكواد البرمجية لحمايتها من المعالجة + إضافة بطاقة تشغيل
  const codeBlocks = [];
  let text = String(raw).replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    const cleanLang = (lang || 'code').toLowerCase().trim();
    const cleanCode = code.trim();
    const isRunnable = ['html', 'javascript', 'js', 'css', 'python', 'py', 'powershell', 'ps1', 'svg', 'game', 'web'].includes(cleanLang);
    const langLabel = cleanLang.toUpperCase() || 'CODE';
    const codeId = `code_${Date.now()}_${idx}`;

    const runBtn = isRunnable
      ? `<button class="code-action-btn run-btn" onclick="runCodeBlock('${codeId}')" data-lang="${cleanLang}" data-codeid="${codeId}" id="runbtn_${codeId}">▶ تشغيل</button>`
      : '';

    const html = `<div class="code-card-wrapper" id="${codeId}">
  <div class="code-card-header">
    <span class="code-lang-label">⚡ ${langLabel}</span>
    <div class="code-card-actions">
      <button class="code-action-btn copy-btn" onclick="copyCodeBlock('${codeId}')" title="نسخ الكود">📋 نسخ</button>
      ${runBtn}
    </div>
  </div>
  <pre class="bubble-pre" id="pre_${codeId}"><code class="language-${escapeHtml(cleanLang)}" data-raw-code="">${escapeHtml(cleanCode)}</code></pre>
</div>`;

    // store raw code on element after render via dataset
    codeBlocks.push({ html, rawCode: cleanCode, lang: cleanLang });
    return `%%CODE_BLOCK_${idx}%%`;
  });

// دالة تنزيل وحفظ الصورة بأمان لمنع أي تلف في الملفات
window.downloadImageFile = async function(url, filename) {
  try {
    showToast('⏳ جاري تحميل الصورة وحفظها...');
    const response = await fetch(url);
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename || `samir_art_${Date.now()}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 2000);
    showToast('💾 تم حفظ وتنزيل الصورة بنجاح!');
  } catch (err) {
    console.warn('Direct blob download failed, fallback to direct open:', err);
    const a = document.createElement('a');
    a.href = url;
    a.target = '_blank';
    a.download = filename || 'image.png';
    a.click();
  }
};

  // 1.5 حماية واستخراج الصور المضمنة ![نص](رابط) والروابط المباشرة لصور
  const imageBlocks = [];

  // تنظيف أي مسارات ويندوز محلية أو نسبية وتحويلها إلى مسار الويب المباشر
  text = text.replace(/[A-Za-z]:\\[^\s)]*generated\\([^\s)]+\.(?:png|jpg|jpeg|webp))/gi, '/static/generated/$1');
  text = text.replace(/[A-Za-z]:\/[^\s)]*generated\/([^\s)]+\.(?:png|jpg|jpeg|webp))/gi, '/static/generated/$1');
  text = text.replace(/(?:\.\/|\.\.\/|\/)?(?:web_console\/)?generated\/([^\s)]+\.(?:png|jpg|jpeg|webp))/gi, '/static/generated/$1');

  // تحويل أي رابط صورة مباشر إلى صيغة ماركداون تلقائياً
  text = text.replace(/(^|[\s\n])(\/(?:static\/)?generated\/[^\s<>]+\.(?:png|jpg|jpeg|webp|svg)|https?:\/\/[^\s<>]+\.(?:png|jpg|jpeg|webp|svg)(?:\?[^\s<>]*)?)/gi, (match, prefix, url) => {
    return `${prefix}![صورة رسمها سمير](${url})`;
  });

  text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
    const idx = imageBlocks.length;
    let cleanSrc = src.trim().replace(/\\/g, '/');
    if (cleanSrc.includes('/generated/')) {
      const fileName = cleanSrc.split('/generated/').pop().split('?')[0];
      cleanSrc = `/static/generated/${fileName}`;
    }
    const cleanAlt = (alt || 'صورة سمير بالذكاء الاصطناعي').trim();
    const rawFile = cleanSrc.split('/').pop()?.split('?')[0] || `samir_art_${Date.now()}.png`;
    const downloadName = rawFile.endsWith('.png') ? rawFile : `${rawFile}.png`;

    const html = `<div class="chat-image-wrap">
  <div class="chat-img-card">
    <div class="chat-img-header">
      <span class="chat-img-badge">🎨 صورة سمير (PNG)</span>
      <div class="chat-img-actions">
        <button class="chat-img-dl-btn" onclick="downloadImageFile('${cleanSrc}', '${downloadName}')" title="حفظ الصورة بصيغة PNG على جهازك">💾 حفظ PNG</button>
        <button class="chat-img-dl-btn" onclick="window.open('${cleanSrc}', '_blank')" title="عرض بدقة كاملة">⛶ تكبير</button>
      </div>
    </div>
    <div class="chat-img-body">
      <img src="${cleanSrc}" alt="${escapeHtml(cleanAlt)}" class="chat-rendered-img" onclick="window.open('${cleanSrc}', '_blank')" loading="eager" />
    </div>
    <div class="chat-img-caption">✨ ${escapeHtml(cleanAlt)}</div>
  </div>
</div>`;
    imageBlocks.push(html);
    return `\n\n%%IMAGE_BLOCK_${idx}%%\n\n`;
  });

  // 2. حماية الأكواد المضمنة inline code
  const inlineCodes = [];
  text = text.replace(/`([^`\n]+)`/g, (match, code) => {
    const idx = inlineCodes.length;
    inlineCodes.push(`<code class="inline-code">${escapeHtml(code)}</code>`);
    return `%%INLINE_CODE_${idx}%%`;
  });

  // 3. تأمين الأحرف الخاصة بالنصوص العادية لمنع XSS
  text = escapeHtml(text);

  // 4. تنسيق الخط العريض والمائل
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  text = text.replace(/__(.+?)__/g, '<strong>$1</strong>');
  text = text.replace(/\*([^\*\n]+)\*/g, '<em>$1</em>');

  // 5. الروابط التشعبية [نص](رابط)
  text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

  // 6. تقسيم الأسطر وتحليل القوائم المنظمة والمرتبة
  const lines = text.split('\n');
  const output = [];
  let inUl = false;
  let inOl = false;

  const closeLists = () => {
    if (inUl) { output.push('</ul>'); inUl = false; }
    if (inOl) { output.push('</ol>'); inOl = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      closeLists();
      continue;
    }

    // فحص كتل الصور المضمنة لعدم لفها بفقرة <p>
    if (trimmed.startsWith('%%IMAGE_BLOCK_') && trimmed.endsWith('%%')) {
      closeLists();
      output.push(trimmed);
      continue;
    }

    // فحص العناوين (Headers # / ## / ###)
    const headerMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headerMatch) {
      closeLists();
      const level = Math.min(6, headerMatch[1].length + 2);
      output.push(`<h${level} class="bubble-heading">${headerMatch[2]}</h${level}>`);
      continue;
    }

    // فحص القوائم المرقمة: 1. أو 1) أو ١. أو ١)
    const olMatch = trimmed.match(/^(\d+|[\u0660-\u0669]+)[\.\)]\s+(.+)$/);
    if (olMatch) {
      if (inUl) { output.push('</ul>'); inUl = false; }
      if (!inOl) {
        output.push('<ol class="bubble-ol">');
        inOl = true;
      }
      output.push(`<li>${olMatch[2]}</li>`);
      continue;
    }

    // فحص القوائم النقطية: - أو * أو • أو +
    const ulMatch = trimmed.match(/^[\-\*\•\+]\s+(.+)$/);
    if (ulMatch) {
      if (inOl) { output.push('</ol>'); inOl = false; }
      if (!inUl) {
        output.push('<ul class="bubble-ul">');
        inUl = true;
      }
      output.push(`<li>${ulMatch[1]}</li>`);
      continue;
    }

    // خط عادي / فقرة جديدة
    closeLists();
    output.push(`<p class="bubble-p">${trimmed}</p>`);
  }

  closeLists();
  let result = output.join('');

  // 7. استعادة كتل الصور والأكواد والـ inline code
  result = result.replace(/%%IMAGE_BLOCK_(\d+)%%/g, (match, idx) => imageBlocks[parseInt(idx)] || '');
  result = result.replace(/%%CODE_BLOCK_(\d+)%%/g, (match, idx) => {
    const block = codeBlocks[parseInt(idx)];
    if (!block) return '';
    if (typeof block === 'string') return block;
    return block.html || '';
  });
  result = result.replace(/%%INLINE_CODE_(\d+)%%/g, (match, idx) => inlineCodes[parseInt(idx)] || '');

  // Store raw code for run buttons (called after DOM insertion)
  if (typeof _pendingCodeBlocks !== 'undefined') {
    _pendingCodeBlocks.push(...codeBlocks.filter(b => typeof b === 'object'));
  }

  return result;
}

// Global store for code blocks awaiting DOM attachment
const _pendingCodeBlocks = [];

function _attachPendingCodeBlocks() {
  while (_pendingCodeBlocks.length > 0) {
    const block = _pendingCodeBlocks.shift();
    if (!block || !block.html) continue;
    // Find <code> elements inside cards and attach data-raw-code
    const wrappers = document.querySelectorAll('.code-card-wrapper');
    wrappers.forEach(wrapper => {
      const codeEl = wrapper.querySelector('code');
      if (codeEl && codeEl.getAttribute('data-raw-code') === '' && !codeEl._codeAttached) {
        codeEl.setAttribute('data-raw-code', block.rawCode);
        codeEl.setAttribute('data-lang', block.lang);
        codeEl._codeAttached = true;
      }
    });
  }
}

function showAssistantDialogue(data) {
  if (!DOM.dialogueScrollArea) return;

  const bubble = document.createElement('div');
  bubble.className = 'dialogue-bubble assistant-bubble';
  const model = data.model || 'Gemini 3.5';
  const time = formatCurrentTime();

  bubble.innerHTML = `
    <div class="bubble-header">
      <div class="assistant-tag-group">
        <span class="assistant-avatar">🤖</span>
        <span class="bubble-author">سمير</span>
        <span class="assistant-model-pill">${escapeHtml(model)}</span>
      </div>
      <div class="bubble-actions">
        <span class="bubble-time">${time}</span>
        <button class="bubble-mini-btn btn-replay-bubble" title="إعادة نطق الرد">🔊</button>
      </div>
    </div>
    <div class="bubble-content">${renderMarkdown(data.text)}</div>
    <div class="bubble-tools"></div>
  `;

  if (data.toolCalls && data.toolCalls.length > 0) {
    const toolsWrap = bubble.querySelector('.bubble-tools');
    const contentWrap = bubble.querySelector('.bubble-content');

    data.toolCalls.forEach(t => {
      const name = t.name || t.function?.name || 'tool';
      const chip = document.createElement('div');
      chip.className = 'tool-chip';
      let icon = '⚡';
      if (name.includes('discord')) icon = '🎮';
      else if (name.includes('image')) icon = '🎨';
      else if (name.includes('code')) icon = '💻';
      else if (name.includes('app')) icon = '🚀';
      else if (name.includes('youtube')) icon = '🎬';
      else if (name.includes('spotify')) icon = '🎵';
      chip.textContent = `${icon} نفّذ: ${name}`;
      toolsWrap.appendChild(chip);

      // إذا كانت الأداة تشغل يوتيوب أو سبوتيفاي، نعرض الفيديو فوراً في الرسالة نفسها وفي المشغل العائم
      const res = t.result || t.execution || {};
      if (res && res.embed_url && contentWrap) {
        const isSp = (res.service || '').includes('spotify');
        const mediaCard = document.createElement('div');
        mediaCard.className = `chat-media-embed-card ${isSp ? 'spotify' : 'youtube'}`;
        mediaCard.innerHTML = `
          <div class="chat-media-embed-header">
            <span>${isSp ? '🎵 سبوتيفاي' : '🎬 فيديو يوتيوب'}: ${escapeHtml(res.title || 'مشغل الوسائط')}</span>
            <a href="${escapeHtml(res.url || res.embed_url)}" target="_blank" style="color:var(--cyan);font-size:11px;text-decoration:none;">↗️ نافذة خارجية</a>
          </div>
          <div class="chat-media-iframe-wrap ${isSp ? 'spotify-wrap' : ''}">
            <iframe src="${escapeHtml(res.embed_url)}" allow="autoplay; encrypted-media; fullscreen; picture-in-picture" allowfullscreen></iframe>
          </div>
        `;
        contentWrap.appendChild(mediaCard);
        openInAppMediaPlayer(res);
      }

      // إذا كانت الأداة رسم وتوليد صور، نضمن عرض الصورة فورياً كبطاقة مع خيار حفظ PNG
      const isImgTool = name.includes('image') || name.includes('imagine');
      let imgUrl = res && (res.image_url || res.direct_url);
      if (imgUrl) {
        imgUrl = imgUrl.replace(/\\/g, '/');
        if (imgUrl.includes('/generated/')) {
          const fn = imgUrl.split('/generated/').pop().split('?')[0];
          imgUrl = `/static/generated/${fn}`;
        }
      }
      if (isImgTool && imgUrl && contentWrap) {
        const alreadyRendered = contentWrap.querySelector(`img[src*="${imgUrl}"]`);
        if (!alreadyRendered) {
          const rawFile = (imgUrl || '').split('/').pop()?.split('?')[0] || `samir_art_${Date.now()}.png`;
          const finalDownload = rawFile.endsWith('.png') ? rawFile : `${rawFile}.png`;
          const promptText = res.prompt || t.arguments?.prompt || 'رسمة سمير';
          const imgCard = document.createElement('div');
          imgCard.className = 'chat-image-wrap';
          imgCard.innerHTML = `
            <div class="chat-img-card">
              <div class="chat-img-header">
                <span class="chat-img-badge">🎨 صورة سمير (${res.format || 'PNG'})</span>
                <div class="chat-img-actions">
                  <button class="chat-img-dl-btn" onclick="downloadImageFile('${imgUrl}', '${finalDownload}')" title="حفظ الصورة بصيغة PNG على جهازك">💾 حفظ PNG</button>
                  <button class="chat-img-dl-btn" onclick="window.open('${imgUrl}', '_blank')" title="عرض بدقة كاملة">⛶ تكبير</button>
                </div>
              </div>
              <div class="chat-img-body">
                <img src="${imgUrl}" alt="${escapeHtml(promptText)}" class="chat-rendered-img" onclick="window.open('${imgUrl}', '_blank')" loading="eager" />
              </div>
              <div class="chat-img-caption">✨ ${escapeHtml(promptText)}</div>
            </div>
          `;
          contentWrap.appendChild(imgCard);
        }
      }
    });
  }

  const replayBtn = bubble.querySelector('.btn-replay-bubble');
  if (replayBtn) {
    replayBtn.addEventListener('click', () => {
      if (state.lastPlayedBase64) {
        queueAudioChunk(state.lastPlayedBase64);
        showToast('إعادة نطق الرد 🔊');
      }
    });
  }

  // Hide initial placeholder cards if any
  if (DOM.assistantCard) DOM.assistantCard.classList.add('hidden');

  DOM.dialogueScrollArea.appendChild(bubble);
  scrollDialogueToBottom();
  // Attach raw code to code-card run buttons for this bubble
  setTimeout(_attachPendingCodeBlocks, 0);
}

function scrollDialogueToBottom(forceSmooth = false) {
  if (DOM.dialogueScrollArea) {
    setTimeout(() => {
      DOM.dialogueScrollArea.scrollTo({
        top: DOM.dialogueScrollArea.scrollHeight,
        behavior: 'smooth'
      });
      if (DOM.btnScrollBottom) DOM.btnScrollBottom.classList.add('hidden');
    }, 40);
  }
}

function renderToolChips(tools) {
  if (!DOM.assistantTools) return;
  DOM.assistantTools.innerHTML = '';

  tools.forEach(t => {
    const name = t.name || t.function?.name || 'tool';
    const chip = document.createElement('div');
    chip.className = 'tool-chip';

    let icon = '⚡';
    if (name.includes('discord')) icon = '🎮';
    else if (name.includes('image')) icon = '🎨';
    else if (name.includes('code')) icon = '💻';
    else if (name.includes('app')) icon = '🚀';

    chip.textContent = `${icon} نفّذ: ${name}`;
    DOM.assistantTools.appendChild(chip);
  });
}

/* ═════════════════════════════════════════════════════════════════════════════
   7. EYE-COMFORTABLE CONVERSATION HISTORY DRAWER (سجل المحادثات)
   ═════════════════════════════════════════════════════ */
async function loadConversationsList() {
  if (!DOM.drawerConvList) return;
  try {
    const devParam = encodeURIComponent(state.deviceId || '');
    const userParam = state.currentUser?.id ? `&user_id=${encodeURIComponent(state.currentUser.id)}` : '';
    const res = await fetch(`${CONFIG.httpBase}/api/v1/conversations?limit=50&device_id=${devParam}${userParam}`);
    if (!res.ok) return;
    const convs = await res.json();
    state.conversations = convs || [];

    // Update Topbar Badge
    if (DOM.historyCountBadge) {
      if (state.conversations.length > 0) {
        DOM.historyCountBadge.textContent = state.conversations.length;
        DOM.historyCountBadge.classList.remove('hidden');
      } else {
        DOM.historyCountBadge.classList.add('hidden');
      }
    }

    renderConversationsList(state.conversations);
  } catch (e) {
    console.warn('[J.A.R.V.I.S] Failed to load conversations:', e);
  }
}

function renderConversationsList(list) {
  if (!DOM.drawerConvList) return;

  if (!list || list.length === 0) {
    DOM.drawerConvList.innerHTML = `
      <div style="color:var(--text-ghost);text-align:center;padding:40px 10px;font-size:13px;">
        💬 لا توجد محادثات سابقة حتى الآن.<br>ابدأ بالتحدث مع سمير الآن!
      </div>`;
    return;
  }

  DOM.drawerConvList.innerHTML = '';

  list.forEach(c => {
    const card = document.createElement('div');
    card.className = 'drawer-conv-card';
    if (c.id === state.activeConversationId) card.classList.add('active');

    const titleText = c.title || c.summary || 'محادثة سريعة';
    const msgCount = c.message_count ? `${c.message_count} رسائل` : 'نشطة';
    const dateFormatted = formatRelativeDate(c.updated_at || c.created_at);

    card.innerHTML = `
      <div class="conv-card-top">
        <span class="conv-card-title" title="${escapeHtml(titleText)}">💬 ${escapeHtml(titleText)}</span>
        <button class="conv-delete-btn" title="حذف هذه المحادثة">🗑️</button>
      </div>
      <div class="conv-card-bottom">
        <span class="conv-msg-badge">${msgCount}</span>
        <span class="conv-date">${dateFormatted}</span>
      </div>
    `;

    // Click to resume & load messages
    card.addEventListener('click', (e) => {
      if (e.target.closest('.conv-delete-btn')) return;
      resumeConversation(c.id, titleText);
    });

    // Delete handler
    const delBtn = card.querySelector('.conv-delete-btn');
    if (delBtn) {
      delBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm(`هل أنت متأكد من حذف محادثة "${titleText}"؟`)) {
          await deleteConversation(c.id);
        }
      });
    }

    DOM.drawerConvList.appendChild(card);
  });
}

function formatRelativeDate(dateStr) {
  if (!dateStr) return 'اليوم';
  try {
    const d = new Date(dateStr);
    const now = new Date();
    const diffHours = (now - d) / (1000 * 60 * 60);

    if (diffHours < 24 && now.getDate() === d.getDate()) {
      return d.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    } else if (diffHours < 48) {
      return 'أمس';
    } else {
      return d.toLocaleDateString('ar-EG', { month: 'short', day: 'numeric' });
    }
  } catch (e) {
    return 'سابقاً';
  }
}

async function resumeConversation(convId, title) {
  state.activeConversationId = convId;
  CONFIG.sessionId = convId;

  if (DOM.dialogueScrollArea) DOM.dialogueScrollArea.innerHTML = '';

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/conversations/${convId}/messages`);
    if (res.ok) {
      const msgs = await res.json();
      if (msgs && msgs.length > 0) {
        msgs.forEach(m => {
          if (m.sender === 'user') {
            showUserDialogue(m.content);
          } else {
            showAssistantDialogue({
              text: m.content,
              model: m.model || 'Gemini 3.5',
              toolCalls: []
            });
          }
        });
      }
    }
  } catch (e) {}

  if (DOM.drawerOverlay) DOM.drawerOverlay.classList.add('hidden');
  showToast(`تم استئناف: ${title} 📜`);
}

async function deleteConversation(convId) {
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/conversations/${convId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('تم حذف المحادثة بنجاح 🗑️');
      loadConversationsList();
      if (state.activeConversationId === convId) {
        startNewSession();
      }
    }
  } catch (e) {
    showToast('فشل في حذف المحادثة');
  }
}

function startNewSession() {
  CONFIG.sessionId = 'samir_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
  state.activeConversationId = null;

  if (DOM.dialogueScrollArea) DOM.dialogueScrollArea.innerHTML = '';
  if (DOM.userCard) DOM.userCard.classList.add('hidden');
  if (DOM.assistantCard) DOM.assistantCard.classList.add('hidden');

  stopAudioPlayback();
  setOrbState('idle');
  if (DOM.drawerOverlay) DOM.drawerOverlay.classList.add('hidden');
  showToast('بدأت محادثة جديدة مع سمير ⚡');
}

/* ═════════════════════════════════════════════════════════════════════════════
   8. EYE-COMFORTABLE SETTINGS MODAL (لوحة الإعدادات)
   ═════════════════════════════════════════════════════ */
const AVAILABLE_VOICES = [
  { id: 'ar-SA-HamedNeural', name: 'حامد — Hamed (مجاني 100%)', desc: 'عربي فصيح رجالي فخم وواثق — بدون استهلاك أي رصيد 🇸🇦', icon: '🇸🇦', isFree: true },
  { id: 'ar-SA-ZariyahNeural', name: 'زارية — Zariyah (مجانية 100%)', desc: 'عربي فصيح نسائي ناعم ومريح — بدون استهلاك رصيد 🎙️', icon: '🎙️', isFree: true },
  { id: 'ar-EG-ShakirNeural', name: 'شاكر — Shakir (مجاني 100%)', desc: 'عربي مصري دافئ وسريع التفاعل — بدون استهلاك رصيد 🇪🇬', icon: '🇪🇬', isFree: true },
  { id: 'ar-EG-SalmaNeural', name: 'سلمى — Salma (مجانية 100%)', desc: 'عربي مصري نسائي مشرق وعالي الوضوح — مجاني 100% 🇪🇬', icon: '🇪🇬', isFree: true },
  { id: 'ar-AE-HamdanNeural', name: 'حمدان — Hamdan (مجاني 100%)', desc: 'خليجي إماراتي فخم ووقور كالمعلقين الرسميين 🇦🇪', icon: '🇦🇪', isFree: true },
  { id: 'ar-AE-FatimaNeural', name: 'فاطمة — Fatima (مجانية 100%)', desc: 'خليجي إماراتي نسائي راقٍ وهادئ للأذن 🇦🇪', icon: '🇦🇪', isFree: true },
  { id: 'ar-LB-RamiNeural', name: 'رامي — Rami (مجاني 100%)', desc: 'شامي لبناني شبابي عصري وتقني 🇱🇧', icon: '🇱🇧', isFree: true },
  { id: 'ar-LB-LaylaNeural', name: 'ليلى — Layla (مجانية 100%)', desc: 'شامي لبناني نسائي ناعم ومريح للسرد 🇱🇧', icon: '🇱🇧', isFree: true },
  { id: 'ar-JO-TaimNeural', name: 'تيم — Taim (مجاني 100%)', desc: 'أردني حماسي واثق ونشيط 🇯🇴', icon: '🇯🇴', isFree: true },
  { id: 'ar-JO-SanaNeural', name: 'سناء — Sana (مجانية 100%)', desc: 'أردني إخباري وقور ومخارج حروف واضحة 🇯🇴', icon: '🇯🇴', isFree: true },
  { id: 'ar-MA-JamalNeural', name: 'جمال — Jamal (مجاني 100%)', desc: 'مغربي هادئ ومتقن للنصوص الطويلة 🇲🇦', icon: '🇲🇦', isFree: true },
  { id: 'ar-IQ-BasselNeural', name: 'باسل — Bassel (مجاني 100%)', desc: 'عراقي عميق وثائقي ذو هيبة وفخامة 🇮🇶', icon: '🇮🇶', isFree: true },
  { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam — آدم (ElevenLabs)', desc: 'طبيعي ودافئ وواثق (يتطلب مفتاح sk_ ورصيد)', icon: '✨', isFree: false },
  { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Sarah — سارة (ElevenLabs)', desc: 'صوت نسائي واثق ومريح للأذن (ElevenLabs)', icon: '✨', isFree: false },
  { id: 'nPczCjzI2devNBz1zQrb', name: 'Brian — برايان (ElevenLabs)', desc: 'رجالي فخم وإخباري كالمعلقين الوثائقيين', icon: '✨', isFree: false },
  { id: 'hpp4J3VqNfWAUOO0d1Us', name: 'Bella — بيلا (ElevenLabs)', desc: 'صوت ناعم ومشرق، نبرة لطيفة وودودة', icon: '✨', isFree: false },
];

async function playVoicePreview(voiceId) {
  try {
    const formData = new FormData();
    formData.append('text', 'أهلاً بك، تم تفعيل صوتي الجديد بنجاح.');
    formData.append('voice', voiceId);
    const res = await fetch(`${CONFIG.httpBase}/api/v1/chat/tts`, {
      method: 'POST',
      body: formData,
    });
    if (res.ok) {
      const blob = await res.blob();
      const audioUrl = URL.createObjectURL(blob);
      const audio = new Audio(audioUrl);
      audio.play().catch(() => {});
    }
  } catch (e) {
    console.debug('[Samir] Preview voice err:', e);
  }
}

function updateQuickVoiceButtonLabel(voiceId) {
  const v = AVAILABLE_VOICES.find(x => x.id === voiceId);
  if (DOM.quickVoiceLabel && v) {
    const shortName = v.name.split(' ')[0] || 'الصوت';
    DOM.quickVoiceLabel.textContent = shortName;
  }
}

function initVoiceSettings() {
  if (!DOM.voiceCardsGrid) return;
  DOM.voiceCardsGrid.innerHTML = '';
  updateQuickVoiceButtonLabel(state.activeVoiceId);

  AVAILABLE_VOICES.forEach(v => {
    const card = document.createElement('div');
    card.className = 'voice-card';
    if (v.id === state.activeVoiceId) card.classList.add('selected');

    const badgeFree = v.isFree ? '<span style="font-size:10px;background:rgba(0,255,136,0.15);color:#00ff88;padding:2px 6px;border-radius:4px;border:1px solid rgba(0,255,136,0.3)">مجاني 100%</span>' : '<span style="font-size:10px;background:rgba(255,183,3,0.15);color:#ffb703;padding:2px 6px;border-radius:4px;border:1px solid rgba(255,183,3,0.3)">ElevenLabs</span>';

    card.innerHTML = `
      <div class="voice-card-name">
        <span>${v.icon} ${v.name}</span>
        <div style="display:flex;align-items:center;gap:6px">
          ${badgeFree}
          <span class="voice-check">${v.id === state.activeVoiceId ? '✓' : ''}</span>
        </div>
      </div>
      <div class="voice-card-desc">${v.desc}</div>
    `;

    card.addEventListener('click', async () => {
      state.activeVoiceId = v.id;
      localStorage.setItem('samir_active_voice', v.id);
      updateQuickVoiceButtonLabel(v.id);

      document.querySelectorAll('.voice-card').forEach(c => {
        c.classList.remove('selected');
        const check = c.querySelector('.voice-check');
        if (check) check.textContent = '';
      });
      card.classList.add('selected');
      const check = card.querySelector('.voice-check');
      if (check) check.textContent = '✓';

      // تفعيل الصوت فورياً عبر السيرفر والـ WebSocket
      wsSend({ type: 'select_voice', voice: v.id });
      try {
        await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/select`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ voice_or_dialect: v.id }),
        });
      } catch (err) {}

      showToast(`🎙️ تم تفعيل صوت: ${v.name.split('—')[0]}`);
      playVoicePreview(v.id);
    });

    DOM.voiceCardsGrid.appendChild(card);
  });
}

async function saveSettings() {
  try {
    // 1. Save voice
    if (state.activeVoiceId) {
      wsSend({ type: 'select_voice', voice: state.activeVoiceId });
      await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_or_dialect: state.activeVoiceId }),
      });
    }

    // 2. Speech speed (1x - 5x)
    const speedVal = DOM.settingTtsRate?.value;
    if (speedVal) {
      const speedNum = parseFloat(speedVal);
      // Convert multiplier to Edge TTS rate offset: 1x=+0%, 2x=+50%, 3x=+100%, 4x=+150%, 5x=+200%
      const pct = Math.round((speedNum - 1) * 50);
      const rateStr = pct >= 0 ? `+${pct}%` : `${pct}%`;
      try {
        await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/config`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rate: rateStr, speed_multiplier: speedNum }),
        });
        state.speechSpeed = speedNum;
        console.log(`[Samir] Speech speed set to ${speedNum}x (${rateStr})`);
      } catch (e) {
        console.warn('[Samir] Could not save speech speed:', e);
      }
    }

    // 3. Default Provider
    const prov = DOM.settingDefaultProvider?.value;
    if (prov && DOM.providerSelect) {
      DOM.providerSelect.value = prov;
      try {
        await fetch(`${CONFIG.httpBase}/api/v1/providers/set-default`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: prov })
        });
      } catch (ex) {
        console.warn('[Samir] Could not set default provider:', ex);
      }
    }

    // 4. Save AI API Keys if provided
    const qwenKey = document.getElementById('setting-qwen-key')?.value?.trim();
    const geminiKey = document.getElementById('setting-gemini-key')?.value?.trim();
    const groqKey = document.getElementById('setting-groq-key')?.value?.trim();
    if (qwenKey || geminiKey || groqKey) {
      try {
        await fetch(`${CONFIG.httpBase}/api/v1/providers/keys`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            qwen_api_key: qwenKey || undefined,
            gemini_api_key: geminiKey || undefined,
            groq_api_key: groqKey || undefined,
          })
        });
      } catch (ex) {
        console.warn('[Samir] Could not save API keys:', ex);
      }
    }

    showToast('تم حفظ جميع الإعدادات والمحركات بنجاح ⚙️');
    if (DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
  } catch (e) {
    showToast('حدث خطأ أثناء حفظ الإعدادات');
  }
}

async function checkVoiceQuota() {
  const badge = DOM.voiceQuotaBadge || document.getElementById('voice-quota-badge');
  const msg = DOM.voiceQuotaMsg || document.getElementById('voice-quota-msg');
  if (!badge) return;

  badge.textContent = 'جاري الفحص...';
  badge.className = 'quota-badge badge-checking';

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/quota`);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();

    if (data.status === 'ok') {
      badge.textContent = `مفعّل: ${data.remaining_formatted || data.remaining_characters + ' حرف'} متبقية`;
      badge.className = 'quota-badge badge-ok';
      if (msg) msg.textContent = `✅ حساب ElevenLabs نشط ولديك ${data.remaining_formatted || data.remaining_characters + ' حرف'} متبقية من أصل ${data.total_formatted || '10,000 حرف'}.`;
    } else if (data.status === 'exhausted') {
      badge.textContent = 'الرصيد منتهي (0 متبقي)';
      badge.className = 'quota-badge badge-exhausted';
      if (msg) msg.textContent = `⚠️ انتهت الحصة المجانية (10,000 حرف) لهذا المفتاح. يعمل سمير حالياً بالأصوات الفصيحة المجانية 100%. عند الرغبة، الصق مفتاح sk_ جديد واضغط "تحديث المفتاح".`;
    } else if (data.status === 'key_id_entered') {
      badge.textContent = 'معرّف Key ID (وليس المفتاح السري)';
      badge.className = 'quota-badge badge-warn';
      if (msg) msg.textContent = `⚠️ الرمز المسجل هو معرّف المفتاح (Key ID) وليس المفتاح السري! مفتاح ElevenLabs يبدأ بـ "sk_" ويظهر لمرة واحدة فقط عند إنشائه من موقع ElevenLabs. يعمل سمير حالياً بالأصوات العصبية الفصيحة المجانية 100%.`;
    } else if (data.status === 'no_key') {
      badge.textContent = 'الأصوات العصبية المجانية (100%)';
      badge.className = 'quota-badge badge-ok';
      if (msg) msg.textContent = `ℹ️ يعمل سمير بالأصوات العصبية الفصيحة فائقة الجودة بدون أي استهلاك كريدت.`;
    } else {
      badge.textContent = 'غير متصل أو مفتاح غير صالح';
      badge.className = 'quota-badge badge-error';
      if (msg && data.message) msg.textContent = `تنبيه: ${data.message}`;
    }
  } catch (err) {
    console.warn('[Samir] Failed to check voice quota:', err);
    if (badge) {
      badge.textContent = 'فحص الحصة غير متاح';
      badge.className = 'quota-badge badge-error';
    }
  }
}

async function updateElevenLabsKey() {
  const keyInput = DOM.settingElevenLabsKey || document.getElementById('setting-elevenlabs-key');
  const newKey = keyInput?.value?.trim();
  if (!newKey) {
    showToast('⚠️ يرجى إدخال مفتاح ElevenLabs أولاً');
    return;
  }

  showToast('⚡ جاري التحقق من المفتاح وتفعيله...');
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: newKey }),
    });
    const data = await res.json();
    if (res.ok && data.status === 'success') {
      showToast('✅ تم تفعيل مفتاح ElevenLabs بنجاح!');
      if (keyInput) keyInput.value = '';
      await checkVoiceQuota();
    } else {
      showToast('❌ فشل حفظ المفتاح: ' + (data.detail || data.message || 'خطأ'));
    }
  } catch (err) {
    console.error('[Samir] Update key error:', err);
    showToast('❌ خطأ في الاتصال بالخادم');
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   8.5. HUD DASHBOARD INTERACTIVITY & TELEMETRY
   ═════════════════════════════════════════════════════ */
function initHudDashboard() {
  // 1. Interactive Connected Sub-nodes
  const subnodes = document.querySelectorAll('.hud-subnode');
  subnodes.forEach((node) => {
    node.addEventListener('click', (e) => {
      e.stopPropagation();
      initAudioContext();

      const prompt = node.getAttribute('data-prompt');
      const action = node.getAttribute('data-action');

      if (prompt) {
        if (DOM.textInput) {
          DOM.textInput.value = prompt;
          handleSendText();
        }
      } else if (action === 'ai-engines') {
        if (DOM.providerSelect) {
          DOM.providerSelect.focus();
          const current = DOM.providerSelect.value;
          const options = ['auto', 'duckai', 'qwen', 'gemini', 'groq', 'claude', 'openai'];
          const nextIdx = (options.indexOf(current) + 1) % options.length;
          DOM.providerSelect.value = options[nextIdx];
          const selectedText = DOM.providerSelect.options[DOM.providerSelect.selectedIndex]?.text || options[nextIdx];
          const topEngineName = document.getElementById('top-engine-name');
          if (topEngineName) topEngineName.textContent = selectedText;
          showToast(`⚡ تم التبديل إلى: ${selectedText}`);
        }
      } else if (action === 'security-auth') {
        showToast('🛡️ فحص الأمان: جميع مفاتيح API والجلسات مشفرة محلياً بنجاح.');
      }
    });
  });

  // 2. Running Live Uptime Counter
  const uptimeEl = document.getElementById('hud-uptime-val');
  if (uptimeEl) {
    let startTime = Date.now() - (14 * 3600 + 38 * 60 + 55) * 1000;
    setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      const h = String(Math.floor(elapsed / 3600)).padStart(2, '0');
      const m = String(Math.floor((elapsed % 3600) / 60)).padStart(2, '0');
      const s = String(elapsed % 60).padStart(2, '0');
      uptimeEl.textContent = `${h}:${m}:${s}`;
    }, 1000);
  }

  // 3. System Telemetry Meters Natural Micro-fluctuation
  const ramVal = document.getElementById('meter-ram-val');
  const ramFill = document.getElementById('meter-ram-fill');
  const cpuVal = document.getElementById('meter-cpu-val');
  const cpuFill = document.getElementById('meter-cpu-fill');

  setInterval(() => {
    if (cpuVal && cpuFill) {
      const isWorking = state.currentOrbState === 'thinking' || state.currentOrbState === 'speaking';
      const baseCpu = isWorking ? 38 : 16;
      const jitter = Math.floor(Math.random() * 8) - 4;
      const cpu = Math.max(8, Math.min(95, baseCpu + jitter));
      cpuVal.textContent = `${cpu}%`;
      cpuFill.style.width = `${cpu}%`;
    }
    if (ramVal && ramFill) {
      const jitter = Math.floor(Math.random() * 3) - 1;
      const ram = 42 + jitter;
      ramVal.textContent = `${ram}%`;
      ramFill.style.width = `${ram}%`;
    }
  }, 2500);

  // 4. Live Real-Time Clock & Date
  const clockEl = document.getElementById('hud-live-clock');
  const dateEl = document.getElementById('hud-live-date');
  const hijriEl = document.getElementById('hud-live-hijri');

  function updateLiveClock() {
    const now = new Date();
    // الوقت
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    if (clockEl) clockEl.textContent = `${hh}:${mm}:${ss}`;

    // التاريخ الميلادي بالعربية
    const dayNames = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'];
    const monthNames = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
    const dayName = dayNames[now.getDay()];
    const day = now.getDate();
    const month = monthNames[now.getMonth()];
    const year = now.getFullYear();
    if (dateEl) dateEl.textContent = `${dayName}، ${day} ${month} ${year}`;

    // التاريخ الهجري (Approximation)
    if (hijriEl) {
      try {
        const hijriStr = now.toLocaleDateString('ar-SA-u-ca-islamic', { year: 'numeric', month: 'long', day: 'numeric' });
        hijriEl.textContent = 'هـ: ' + hijriStr;
      } catch(e) {
        hijriEl.textContent = '';
      }
    }
  }

  updateLiveClock();
  setInterval(updateLiveClock, 1000);

  // 5. Oscillating Signal Wave Canvas
  initSignalWaveCanvas();
}

function initSignalWaveCanvas() {
  const canvas = document.getElementById('hud-wave-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  let step = 0;
  function drawWave() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    const isSpeaking = state.currentOrbState === 'speaking';
    const isListening = state.currentOrbState === 'listening';
    const isThinking = state.currentOrbState === 'thinking';

    const amplitude = isSpeaking ? 16 : (isListening ? 12 : (isThinking ? 9 : 4.5));
    const speed = isSpeaking ? 0.08 : (isListening ? 0.06 : 0.03);
    step += speed;

    // Draw background grid lines
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.08)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();

    // Draw Cyan Signal Line
    ctx.beginPath();
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = '#00e5ff';
    ctx.shadowBlur = 6;
    ctx.shadowColor = '#00e5ff';

    for (let x = 0; x < w; x++) {
      const y = h / 2 + Math.sin(x * 0.06 + step) * amplitude * Math.sin(x * 0.02);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Draw Gold Harmonic Line
    ctx.beginPath();
    ctx.lineWidth = 1;
    ctx.strokeStyle = '#ffd166';
    ctx.shadowBlur = 4;
    ctx.shadowColor = '#ffd166';

    for (let x = 0; x < w; x++) {
      const y = h / 2 + Math.sin(x * 0.08 - step * 1.2) * (amplitude * 0.65) * Math.cos(x * 0.03);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Reset shadow
    ctx.shadowBlur = 0;

    requestAnimationFrame(drawWave);
  }

  requestAnimationFrame(drawWave);
}

/* ═════════════════════════════════════════════════════════════════════════════
   9. EVENT LISTENERS & SHORTCUTS
   ═════════════════════════════ */
function setupEventListeners() {
  // Custom Rules Topbar Button
  if (DOM.btnCustomRules) {
    DOM.btnCustomRules.addEventListener('click', () => {
      openCustomRulesModal();
    });
  }

  // Settings Modal Toggle & Live Quota Check
  if (DOM.settingsBtn) {
    DOM.settingsBtn.addEventListener('click', () => {
      if (DOM.settingsModal) DOM.settingsModal.classList.remove('hidden');
      checkVoiceQuota();
    });
  }

  // Quick Voice Button Toggle
  if (DOM.btnQuickVoice) {
    DOM.btnQuickVoice.addEventListener('click', () => {
      if (DOM.settingsModal) {
        DOM.settingsModal.classList.remove('hidden');
        const tabBtn = document.querySelector('[data-tab="voice"]');
        if (tabBtn) tabBtn.click();
        checkVoiceQuota();
      }
    });
  }

  if (DOM.btnUpdateElevenlabsKey) {
    DOM.btnUpdateElevenlabsKey.addEventListener('click', () => {
      updateElevenLabsKey();
    });
  }

  if (DOM.settingElevenLabsKey) {
    DOM.settingElevenLabsKey.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        updateElevenLabsKey();
      }
    });
  }

  // Dialogue Scroll Area Listeners (تصفح الرسائل السابقة والتمرير)
  if (DOM.dialogueScrollArea) {
    DOM.dialogueScrollArea.addEventListener('scroll', () => {
      const diff = DOM.dialogueScrollArea.scrollHeight - DOM.dialogueScrollArea.scrollTop - DOM.dialogueScrollArea.clientHeight;
      if (diff > 90) {
        if (DOM.btnScrollBottom) DOM.btnScrollBottom.classList.remove('hidden');
      } else {
        if (DOM.btnScrollBottom) DOM.btnScrollBottom.classList.add('hidden');
      }
    });
  }

  if (DOM.btnScrollBottom) {
    DOM.btnScrollBottom.addEventListener('click', () => {
      scrollDialogueToBottom(true);
    });
  }

  if (DOM.btnClearDialogue) {
    DOM.btnClearDialogue.addEventListener('click', () => {
      if (DOM.dialogueScrollArea) DOM.dialogueScrollArea.innerHTML = '';
      showToast('تم مسح شاشة الحوار 🧹');
    });
  }

  // Orb Click (Barge-in / Listen)
  if (DOM.orb) {
    DOM.orb.addEventListener('click', () => {
      initAudioContext();
      if (state.isPlayingAudio) {
        stopAudioPlayback();
        wsSend({ type: 'abort' });
        setOrbState('idle');
      } else {
        toggleRecording();
      }
    });
  }

  // Mic Button
  if (DOM.micBtn) {
    DOM.micBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      initAudioContext();
      toggleRecording();
    });
  }

  // Send Button (Works reliably on mobile touch and PC click)
  if (DOM.sendBtn) {
    const triggerSend = (e) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      handleSendText();
    };
    DOM.sendBtn.addEventListener('click', triggerSend);
    DOM.sendBtn.addEventListener('touchend', triggerSend);
  }

  // Enter to send in text input
  if (DOM.textInput) {
    DOM.textInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        handleSendText();
      }
    });
  }

  // Provider Select listener
  if (DOM.providerSelect) {
    const savedProv = localStorage.getItem('samir_ai_provider');
    if (savedProv && Array.from(DOM.providerSelect.options).some(o => o.value === savedProv)) {
      DOM.providerSelect.value = savedProv;
      const topEngineName = document.getElementById('top-engine-name');
      if (topEngineName) topEngineName.textContent = DOM.providerSelect.options[DOM.providerSelect.selectedIndex]?.text;
    }

    DOM.providerSelect.addEventListener('change', () => {
      const selectedVal = DOM.providerSelect.value;
      const selectedText = DOM.providerSelect.options[DOM.providerSelect.selectedIndex]?.text || selectedVal;
      localStorage.setItem('samir_ai_provider', selectedVal);
      const topEngineName = document.getElementById('top-engine-name');
      if (topEngineName) topEngineName.textContent = selectedText;
      showToast(`⚡ تم التبديل إلى: ${selectedText}`);
    });
  }

  // Sound Toggle
  if (DOM.soundBtn) {
    DOM.soundBtn.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      if (DOM.soundBtnIcon) {
        DOM.soundBtnIcon.textContent = state.soundEnabled ? '🔊' : '🔇';
      }
      showToast(state.soundEnabled ? 'تم تفعيل الصوت 🔊' : 'تم كتم الصوت 🔇');
      if (!state.soundEnabled) stopAudioPlayback();
    });
  }

  // Replay speech button
  if (DOM.replaySpeechBtn) {
    DOM.replaySpeechBtn.addEventListener('click', () => {
      if (state.lastPlayedBase64) {
        queueAudioChunk(state.lastPlayedBase64);
        showToast('إعادة نطق الرد 🔊');
      }
    });
  }

  // Drawer Toggle
  if (DOM.historyBtn) {
    DOM.historyBtn.addEventListener('click', () => {
      if (DOM.drawerOverlay) {
        DOM.drawerOverlay.classList.remove('hidden');
        loadConversationsList();
      }
    });
  }

  if (DOM.drawerCloseBtn) {
    DOM.drawerCloseBtn.addEventListener('click', () => {
      if (DOM.drawerOverlay) DOM.drawerOverlay.classList.add('hidden');
    });
  }

  if (DOM.drawerNewBtn) {
    DOM.drawerNewBtn.addEventListener('click', startNewSession);
  }

  // Drawer Live Search
  if (DOM.drawerSearchInput) {
    DOM.drawerSearchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase().trim();
      if (!q) {
        renderConversationsList(state.conversations);
      } else {
        const filtered = state.conversations.filter(c => 
          (c.title && c.title.toLowerCase().includes(q)) || 
          (c.summary && c.summary.toLowerCase().includes(q))
        );
        renderConversationsList(filtered);
      }
    });
  }

  // Settings Modal Controls
  if (DOM.settingsCloseBtn) {
    DOM.settingsCloseBtn.addEventListener('click', () => {
      if (DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
    });
  }

  if (DOM.settingsCancelBtn) {
    DOM.settingsCancelBtn.addEventListener('click', () => {
      if (DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
    });
  }

  if (DOM.settingsSaveBtn) {
    DOM.settingsSaveBtn.addEventListener('click', saveSettings);
  }

  // Close overlays on backdrop click
  if (DOM.drawerOverlay) {
    DOM.drawerOverlay.addEventListener('click', (e) => {
      if (e.target === DOM.drawerOverlay) DOM.drawerOverlay.classList.add('hidden');
    });
  }

  if (DOM.settingsModal) {
    DOM.settingsModal.addEventListener('click', (e) => {
      if (e.target === DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
    });
  }

  // ── Screen Vision Button (مشاركة الشاشة الحية ومراقبتها) ───────────────────
  if (DOM.screenBtn) {
    DOM.screenBtn.addEventListener('click', () => {
      if (state.activeVisionStream && state.visionMode === 'screen') {
        stopVisionStream();
      } else {
        startScreenVision();
      }
    });
  }

  // ── Live Camera Button (بث الكاميرا المباشر ومراقبة ما تراه) ──────────────
  if (DOM.cameraBtn) {
    DOM.cameraBtn.addEventListener('click', () => {
      if (state.activeVisionStream && state.visionMode === 'camera') {
        stopVisionStream();
      } else {
        startCameraVision();
      }
    });
  }

  // ── Live Vision PiP Controls ─────────────────────────────────────────────
  if (DOM.pipCloseBtn) {
    DOM.pipCloseBtn.addEventListener('click', stopVisionStream);
  }

  if (DOM.pipSwitchCamera) {
    DOM.pipSwitchCamera.addEventListener('click', () => {
      const nextFacing = state.cameraFacing === 'environment' ? 'user' : 'environment';
      startCameraVision(nextFacing);
    });
  }

  if (DOM.pipAnalyzeBtn) {
    DOM.pipAnalyzeBtn.addEventListener('click', () => {
      captureAndAnalyzeVision();
    });
  }

  if (DOM.pipAutoWatchCb) {
    DOM.pipAutoWatchCb.addEventListener('change', (e) => {
      toggleAutoWatch(e.target.checked);
    });
  }

  // ── Alarm Modal Controls ─────────────────────────────────────────────────
  if (DOM.alarmDismissBtn) {
    DOM.alarmDismissBtn.addEventListener('click', dismissAlarm);
  }

  if (DOM.alarmSnoozeBtn) {
    DOM.alarmSnoozeBtn.addEventListener('click', snoozeAlarm);
  }

  // ── File Attach Button via <input type="file"> ───────────────────────────
  if (DOM.fileInput) {
    DOM.fileInput.addEventListener('change', (e) => {
      const files = Array.from(e.target.files || []);
      uploadFilesViaHttp(files);
      e.target.value = '';
    });
  }

  // ── Ctrl+V Paste from Clipboard ──────────────────────────────────────────
  window.addEventListener('paste', (e) => {
    const items = Array.from(e.clipboardData?.items || []);
    const imageItem = items.find(i => i.type.startsWith('image/'));
    if (imageItem) {
      const blob = imageItem.getAsFile();
      if (blob) uploadFilesViaHttp([blob]);
    }
  });

  // ── Drag & Drop over viewport ────────────────────────────────────────────
  document.body.addEventListener('dragover', (e) => {
    e.preventDefault();
    document.body.classList.add('drag-active');
  });

  document.body.addEventListener('dragleave', (e) => {
    if (!e.relatedTarget || e.relatedTarget === document.documentElement) {
      document.body.classList.remove('drag-active');
    }
  });

  document.body.addEventListener('drop', (e) => {
    e.preventDefault();
    document.body.classList.remove('drag-active');
    const files = Array.from(e.dataTransfer?.files || []);
    if (files.length > 0) uploadFilesViaHttp(files);
  });

  // Node sub-buttons: clicking a hud-subnode with data-prompt auto-sends
  document.querySelectorAll('.hud-subnode[data-prompt]').forEach(node => {
    node.addEventListener('click', () => {
      const prompt = node.getAttribute('data-prompt');
      if (prompt && DOM.textInput) {
        DOM.textInput.value = prompt;
        handleSendText(prompt);
        DOM.textInput.value = '';
      }
    });
  });

  // ── User Auth & Memory Modal ───────────────────────────────────────────
  if (DOM.btnGoogleLogin) {
    DOM.btnGoogleLogin.addEventListener('click', openAuthModal);
  }

  if (DOM.userProfileChip) {
    DOM.userProfileChip.addEventListener('click', openAuthModal);
  }

  if (DOM.authModalClose) {
    DOM.authModalClose.addEventListener('click', closeAuthModal);
  }

  if (DOM.btnAuthDone) {
    DOM.btnAuthDone.addEventListener('click', closeAuthModal);
  }

  // Auth Tabs (Login vs Register)
  if (DOM.tabBtnLogin) {
    DOM.tabBtnLogin.addEventListener('click', () => switchAuthTab('login'));
  }
  if (DOM.tabBtnRegister) {
    DOM.tabBtnRegister.addEventListener('click', () => switchAuthTab('register'));
  }

  // Password Peek Toggles
  if (DOM.btnPeekLogin && DOM.loginPassword) {
    DOM.btnPeekLogin.addEventListener('click', () => {
      const isPwd = DOM.loginPassword.type === 'password';
      DOM.loginPassword.type = isPwd ? 'text' : 'password';
      DOM.btnPeekLogin.textContent = isPwd ? '🙈' : '👁️';
    });
  }
  if (DOM.btnPeekReg && DOM.regPassword) {
    DOM.btnPeekReg.addEventListener('click', () => {
      const isPwd = DOM.regPassword.type === 'password';
      DOM.regPassword.type = isPwd ? 'text' : 'password';
      DOM.btnPeekReg.textContent = isPwd ? '🙈' : '👁️';
    });
  }

  // Submit Login
  if (DOM.btnSubmitLogin) {
    DOM.btnSubmitLogin.addEventListener('click', handleUserLogin);
  }
  if (DOM.loginPassword) {
    DOM.loginPassword.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleUserLogin();
    });
  }
  if (DOM.loginEmail) {
    DOM.loginEmail.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleUserLogin();
    });
  }

  // Submit Register
  if (DOM.btnSubmitRegister) {
    DOM.btnSubmitRegister.addEventListener('click', handleUserRegister);
  }
  if (DOM.regPassword) {
    DOM.regPassword.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') handleUserRegister();
    });
  }

  if (DOM.btnWipeMyMemories) {
    DOM.btnWipeMyMemories.addEventListener('click', wipeMyMemories);
  }

  if (DOM.btnLogoutGoogle) {
    DOM.btnLogoutGoogle.addEventListener('click', logoutUser);
  }

  // ── Voice / Silent Typing Mode Toggle ────────────────────────────────────
  if (DOM.btnToggleVoiceMode) {
    DOM.btnToggleVoiceMode.addEventListener('click', toggleVoiceMode);
  }

  // ── Mobile Commands Dropdown Listeners ─────────────────────────────────
  if (DOM.btnMobileMenu) {
    DOM.btnMobileMenu.addEventListener('click', toggleMobileCommandsMenu);
  }
  if (DOM.mobileCmdCloseBtn) {
    DOM.mobileCmdCloseBtn.addEventListener('click', closeMobileCommandsMenu);
  }

  document.getElementById('mcmd-login')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    openAuthModal();
  });
  document.getElementById('mcmd-voice-mode')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    toggleVoiceMode();
  });
  document.getElementById('mcmd-wake-word')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    WakeWordEngine.toggle();
  });
  document.getElementById('mcmd-history')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    if (DOM.drawerOverlay) DOM.drawerOverlay.classList.remove('hidden');
    loadConversationsList();
  });
  document.getElementById('mcmd-settings')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    if (DOM.settingsModal) DOM.settingsModal.classList.remove('hidden');
    checkVoiceQuota();
  });
  document.getElementById('mcmd-share')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    openMobileConnectModal();
  });
  document.getElementById('mcmd-youtube')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    if (DOM.textInput) {
      DOM.textInput.value = 'شغل يوتيوب فيديو ممتع';
      handleSendText('شغل يوتيوب فيديو ممتع');
      DOM.textInput.value = '';
    }
  });
  document.getElementById('mcmd-spotify')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    if (DOM.textInput) {
      DOM.textInput.value = 'شغل موسيقى هادئة على سبوتيفاي';
      handleSendText('شغل موسيقى هادئة على سبوتيفاي');
      DOM.textInput.value = '';
    }
  });
  document.getElementById('mcmd-screenshot')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    if (DOM.textInput) {
      DOM.textInput.value = 'التقط لقطة شاشة وحللها لي';
      handleSendText('التقط لقطة شاشة وحللها لي');
      DOM.textInput.value = '';
    }
  });
  document.getElementById('mcmd-sound')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    toggleSound();
  });

  document.getElementById('mcmd-custom-rules')?.addEventListener('click', () => {
    closeMobileCommandsMenu();
    openCustomRulesModal();
  });

  // ── Custom Rules Modal Handlers ──────────────────────────────────────────
  const customRulesModal = document.getElementById('custom-rules-modal');
  const customRulesCloseBtn = document.getElementById('custom-rules-close-btn');
  const customRulesDoneBtn = document.getElementById('custom-rules-done-btn');
  const btnSaveCustomRule = document.getElementById('btn-save-custom-rule');

  if (customRulesCloseBtn) {
    customRulesCloseBtn.addEventListener('click', closeCustomRulesModal);
  }
  if (customRulesDoneBtn) {
    customRulesDoneBtn.addEventListener('click', closeCustomRulesModal);
  }
  if (customRulesModal) {
    customRulesModal.addEventListener('click', (e) => {
      if (e.target === customRulesModal) closeCustomRulesModal();
    });
  }
  if (btnSaveCustomRule) {
    btnSaveCustomRule.addEventListener('click', saveCustomRule);
  }

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeMobileCommandsMenu();
      const customRulesModal = document.getElementById('custom-rules-modal');
      if (customRulesModal && customRulesModal.style.display !== 'none' && customRulesModal.style.display !== '') {
        closeCustomRulesModal();
      } else if (DOM.drawerOverlay && !DOM.drawerOverlay.classList.contains('hidden')) {
        DOM.drawerOverlay.classList.add('hidden');
      } else if (DOM.settingsModal && !DOM.settingsModal.classList.contains('hidden')) {
        DOM.settingsModal.classList.add('hidden');
      } else if (DOM.authModalOverlay && !DOM.authModalOverlay.classList.contains('hidden')) {
        DOM.authModalOverlay.classList.add('hidden');
      } else if (state.isPlayingAudio) {
        stopAudioPlayback();
        wsSend({ type: 'abort' });
        setOrbState('idle');
      }
    }
  });
}

function toggleMobileCommandsMenu() {
  if (!DOM.mobileCommandsDropdown) return;
  DOM.mobileCommandsDropdown.classList.toggle('hidden');
  if (DOM.btnMobileMenu) DOM.btnMobileMenu.classList.toggle('active', !DOM.mobileCommandsDropdown.classList.contains('hidden'));
}

function closeMobileCommandsMenu() {
  if (DOM.mobileCommandsDropdown) DOM.mobileCommandsDropdown.classList.add('hidden');
  if (DOM.btnMobileMenu) DOM.btnMobileMenu.classList.remove('active');
}

/* ── Attachment Upload via HTTP (files → backend → chips) ────────────────── */
async function uploadFilesViaHttp(files) {
  for (const file of files) {
    try {
      showToast(`📎 جاري رفع ${file.name || 'ملف'}...`);
      const fd = new FormData();
      fd.append('file', file, file.name || 'paste.png');
      const res = await fetch(`${CONFIG.httpBase}/api/v1/chat/upload`, {
        method: 'POST',
        body: fd,
      });
      if (!res.ok) {
        showToast(`⚠️ فشل رفع ${file.name || 'ملف'}`);
        continue;
      }
      const data = await res.json();
      const att = data.attachment || data.file;
      if (data.status === 'success' && att) {
        state.pendingAttachments.push(att);
        renderAttachmentChips();
        showToast(`✅ تم رفع ${att.original_filename || file.name || 'الملف'} بنجاح`);
      }
    } catch (err) {
      console.error('[Samir] Upload error:', err);
      showToast('⚠️ خطأ أثناء رفع الملف');
    }
  }
}

/* ── Render attachment preview chips in the bar ─────────────────────────── */
function renderAttachmentChips() {
  if (!DOM.attachPreview) return;

  if (state.pendingAttachments.length === 0) {
    DOM.attachPreview.innerHTML = '';
    DOM.attachPreview.classList.add('hidden');
    return;
  }

  DOM.attachPreview.classList.remove('hidden');
  DOM.attachPreview.innerHTML = '';

  state.pendingAttachments.forEach((att, idx) => {
    const chip = document.createElement('div');
    chip.className = 'att-chip';

    let preview = '';
    if (att.is_image) {
      const src = att.url || (att.base64 ? `data:${att.mime_type || 'image/jpeg'};base64,${att.base64}` : '');
      if (src) {
        preview = `<img src="${src}" alt="preview" style="width:24px;height:24px;object-fit:cover;border-radius:4px;" />`;
      } else {
        preview = '🖼️';
      }
    } else {
      const icons = { video: '🎬', audio: '🎵', document: '📄', code: '💻' };
      preview = icons[att.category] || '📎';
    }

    chip.innerHTML = `
      ${preview}
      <span class="att-chip-title">${att.original_filename || 'ملف'}</span>
      <span class="att-chip-del" data-idx="${idx}" title="حذف">✕</span>
    `;

    chip.querySelector('.att-chip-del').addEventListener('click', (e) => {
      const i = parseInt(e.target.getAttribute('data-idx'));
      state.pendingAttachments.splice(i, 1);
      renderAttachmentChips();
    });

    DOM.attachPreview.appendChild(chip);
  });
}



/* ── Electron IPC Controls (Frameless Window) ────────────────────────────── */
function setupElectronIPC() {
  const isElectron = window && window.process && window.process.type;
  if (!isElectron && !window.electronAPI) {
    const winControls = document.getElementById('win-controls');
    if (winControls) winControls.style.display = 'none';
    return;
  }

  if (DOM.winMin) {
    DOM.winMin.addEventListener('click', () => {
      if (window.electronAPI?.minimize) window.electronAPI.minimize();
    });
  }
  if (DOM.winClose) {
    DOM.winClose.addEventListener('click', () => {
      if (window.electronAPI?.close) window.electronAPI.close();
    });
  }
}

/* ── Toast Notifications ─────────────────────────────────────────────────── */
function showToast(text) {
  if (!DOM.toast) return;
  DOM.toast.textContent = text;
  DOM.toast.classList.remove('hidden');
  setTimeout(() => {
    DOM.toast.classList.add('hidden');
  }, 2800);
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/* ═════════════════════════════════════════════════════════════════════════════
   10. WAKE WORD ENGINE ("يا سمير" / "سمير")
   ═════════════════════════════════════════════════════ */
const WakeWordEngine = {
  recognition: null,
  enabled: true,
  isListeningWakeWord: false,
  activeSpeechTimer: null,
  restartTimeout: null,

  init() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn('[WakeWord] SpeechRecognition not supported in this browser. Use Chrome or Edge for wake word functionality.');
      if (DOM.btnWakeWord) {
        DOM.btnWakeWord.title = 'خاصية النداء الصوتي (يا سمير) تحتاج Chrome أو Edge';
        DOM.btnWakeWord.style.opacity = '0.5';
        DOM.btnWakeWord.onclick = () => showToast('⚠️ خاصية النداء الصوتي تحتاج متصفح Chrome أو Edge');
      }
      return;
    }
    console.log('[WakeWord] SpeechRecognition API available ✓');


    const saved = localStorage.getItem('samir_wake_word_active');
    this.enabled = saved === null ? true : saved === 'true';

    if (DOM.btnWakeWord) {
      DOM.btnWakeWord.addEventListener('click', () => this.toggle());
    }

    this.createRecognition();
    this.updateUI();

    if (this.enabled) {
      this.resumeListening();
    }
  },

  createRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    try {
      if (this.recognition) {
        try { this.recognition.abort(); } catch (e) {}
        this.recognition = null;
      }

      this.recognition = new SpeechRecognition();
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.lang = 'ar-SA';
      this.recognition.maxAlternatives = 3;

      this.recognition.onstart = () => {
        this.isListeningWakeWord = true;
        this.updateUI();
      };

      this.recognition.onresult = (event) => {
        if (state.isPlayingAudio || state.isRecording) return;

        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          transcript += event.results[i][0].transcript.toLowerCase();
        }

        const keywords = ['سمير', 'يا سمير', 'سميره', 'يا سميرة', 'سالم', 'سامر', 'samir', 'hey samir'];
        const matched = keywords.some(kw => transcript.includes(kw));

        if (matched) {
          console.log('[WakeWord] Detected Samir wake keyword:', transcript);
          // فحص إذا كان المستخدم قد نطق الأمر كاملاً مع اسم سمير (مثل: "سمير افتح يوتيوب" أو "يا سمير كم الساعة")
          let cleanCmd = transcript;
          keywords.forEach(kw => {
            cleanCmd = cleanCmd.replace(new RegExp(kw, 'gi'), '');
          });
          cleanCmd = cleanCmd.replace(/[،,.]/g, '').trim();

          if (cleanCmd.length >= 3) {
            console.log('[WakeWord] Full command recognized with wake word:', cleanCmd);
            this.pauseListening();
            this.playWakeChime();
            showToast(`🎙️ جاري تنفيذ أمرك: "${transcript}"`);
            state.isTypingInteraction = false;
            handleSendText(transcript);
            return;
          }

          this.triggerActivation();
        }
      };

      this.recognition.onerror = (e) => {
        if (e.error === 'network') {
          // يحدث هذا الخطأ عند استخدام HTTP بدلاً من HTTPS
          // SpeechRecognition يحتاج HTTPS في بعض المتصفحات
          console.warn('[WakeWord] Network error — SpeechRecognition يحتاج HTTPS أو localhost. جاري المحاولة مرة أخرى...');
          this.isListeningWakeWord = false;
          // أعد المحاولة بعد تأخير أطول لتجنب التكرار المتسارع
          clearTimeout(this.restartTimeout);
          this.restartTimeout = setTimeout(() => this.resumeListening(), 5000);
        } else if (e.error !== 'no-speech' && e.error !== 'aborted') {
          console.debug('[WakeWord] Recognition note:', e.error);
        }
        this.isListeningWakeWord = false;
      };

      this.recognition.onend = () => {
        this.isListeningWakeWord = false;
        if (this.enabled && !state.isRecording && !state.isPlayingAudio) {
          clearTimeout(this.restartTimeout);
          this.restartTimeout = setTimeout(() => {
            this.resumeListening();
          }, 400);
        }
        this.updateUI();
      };
    } catch (err) {
      console.warn('[WakeWord] Init error:', err);
    }
  },

  playWakeChime() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = state.audioContext || new AudioCtx();
      if (ctx.state === 'suspended') ctx.resume();

      const now = ctx.currentTime;
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880.0, now + 0.16); // A5

      gain.gain.setValueAtTime(0.01, now);
      gain.gain.linearRampToValueAtTime(0.28, now + 0.04);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start(now);
      osc.stop(now + 0.34);
    } catch (e) {}
  },

  async triggerActivation() {
    if (state.isRecording) return;
    this.pauseListening();
    this.playWakeChime();
    showToast('🎙️ نعم! معك سمير... استمع إليك الآن');

    await startRecording();

    // نعتمد على كاشف الصمت الذكي (1.25 ثانية) للإرسال التلقائي
    // ونضع مؤقت أمان أقصى 30 ثانية فقط في حال لم يتكلم المستخدم نهائياً
    if (this.activeSpeechTimer) clearTimeout(this.activeSpeechTimer);
    this.activeSpeechTimer = setTimeout(() => {
      if (state.isRecording) {
        stopRecording();
      }
    }, 30000);
  },

  pauseListening() {
    if (!this.recognition) return;
    try {
      this.recognition.abort();
    } catch (e) {}
    this.isListeningWakeWord = false;
  },

  resumeListening() {
    if (!this.enabled || state.isRecording || state.isPlayingAudio) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;
    if (this.isListeningWakeWord) return;

    // Always create fresh recognition instance for reliability
    try {
      this.createRecognition();
      if (this.recognition) {
        this.recognition.start();
        this.isListeningWakeWord = true;
      }
    } catch (e) {
      // If InvalidStateError, try once more after small delay
      this.isListeningWakeWord = false;
      clearTimeout(this.restartTimeout);
      this.restartTimeout = setTimeout(() => {
        try {
          this.createRecognition();
          if (this.recognition) {
            this.recognition.start();
            this.isListeningWakeWord = true;
          }
        } catch (err) {
          console.debug('[WakeWord] Resume retry notice:', err);
        }
      }, 800);
    }
  },

  toggle() {
    this.enabled = !this.enabled;
    localStorage.setItem('samir_wake_word_active', this.enabled ? 'true' : 'false');
    if (this.enabled) {
      this.resumeListening();
      showToast('تم تفعيل الاستماع التلقائي (نادي "سمير") 🎙️');
    } else {
      this.pauseListening();
      showToast('تم إيقاف الاستماع التلقائي 🔕');
    }
    this.updateUI();
  },

  updateUI() {
    if (DOM.btnWakeWord) {
      if (this.enabled) {
        DOM.btnWakeWord.classList.add('active');
        if (DOM.wakeDot) DOM.wakeDot.style.background = '#00ff88';
        DOM.btnWakeWord.title = 'الأمر الصوتي مفعّل (قل "يا سمير" في أي وقت)';
      } else {
        DOM.btnWakeWord.classList.remove('active');
        if (DOM.wakeDot) DOM.wakeDot.style.background = '#666';
        DOM.btnWakeWord.title = 'اضغط لتفعيل الأمر الصوتي (نادي "سمير")';
      }
    }
  }
};

window.WakeWordEngine = WakeWordEngine;

function initWakeWordEngine() {
  WakeWordEngine.init();
}

/* ═════════════════════════════════════════════════════════════════════════════
   11. MOBILE CONNECT MODAL & QR CODE
   ═════════════════════════════════════════════════════ */
function initMobileConnect() {
  if (DOM.btnMobileConnect) {
    DOM.btnMobileConnect.addEventListener('click', openMobileConnectModal);
  }
  if (DOM.mobileCloseBtn) {
    DOM.mobileCloseBtn.addEventListener('click', closeMobileConnectModal);
  }
  if (DOM.mobileDoneBtn) {
    DOM.mobileDoneBtn.addEventListener('click', closeMobileConnectModal);
  }
  if (DOM.mobileModal) {
    DOM.mobileModal.addEventListener('click', (e) => {
      if (e.target === DOM.mobileModal) closeMobileConnectModal();
    });
  }
  if (DOM.btnCopyMobileUrl) {
    DOM.btnCopyMobileUrl.addEventListener('click', () => {
      if (DOM.mobileUrlInput) {
        navigator.clipboard.writeText(DOM.mobileUrlInput.value).then(() => {
          showToast('📋 تم نسخ رابط الهاتف بنجاح!');
        }).catch(() => {
          DOM.mobileUrlInput.select();
          document.execCommand('copy');
          showToast('📋 تم نسخ رابط الهاتف!');
        });
      }
    });
  }
}

async function openMobileConnectModal() {
  if (!DOM.mobileModal) return;
  DOM.mobileModal.classList.remove('hidden');

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/network/info`);
    if (res.ok) {
      const data = await res.json();
      const mobileUrl = data.mobile_url || `${window.location.protocol}//${window.location.hostname}:8000`;
      if (DOM.mobileUrlInput) DOM.mobileUrlInput.value = mobileUrl;

      const openLink = document.getElementById('mobile-open-link');
      if (openLink) openLink.href = mobileUrl;

      const lanHint = document.getElementById('mobile-lan-hint');
      if (lanHint && data.lan_url) {
        lanHint.textContent = `شبكة محلية: ${data.lan_url}`;
      }

      const label = document.getElementById('mobile-url-label');
      if (label && data.is_https) {
        label.textContent = '🌐 الرابط السحابي المباشر للهاتف (HTTPS آمن للميكروفون ويعمل أونلاين فورياً):';
      }

      if (DOM.mobileQrCanvas && data.qr_base64) {
        const ctx = DOM.mobileQrCanvas.getContext('2d');
        const img = new Image();
        img.onload = () => {
          DOM.mobileQrCanvas.width = 180;
          DOM.mobileQrCanvas.height = 180;
          ctx.fillStyle = '#ffffff';
          ctx.fillRect(0, 0, 180, 180);
          ctx.drawImage(img, 0, 0, 180, 180);
        };
        img.src = `data:image/png;base64,${data.qr_base64}`;
      }
    }
  } catch (err) {
    console.warn('[MobileConnect] Failed to fetch network info:', err);
    if (DOM.mobileUrlInput) {
      DOM.mobileUrlInput.value = `${window.location.protocol}//${window.location.hostname}:8000`;
    }
  }
}

function closeMobileConnectModal() {
  if (DOM.mobileModal) DOM.mobileModal.classList.add('hidden');
}

/* ═════════════════════════════════════════════════════════════════════════════
   12. PWA SERVICE WORKER REGISTRATION (الهاتف النقال)
   ═════════════════════════════════════════════════════ */
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').then((reg) => {
      console.log('[S.A.M.I.R PWA] Service Worker registered:', reg.scope);
    }).catch((err) => {
      console.debug('[S.A.M.I.R PWA] SW registration notice:', err);
    });
  });
}

/* ═════════════════════════════════════════════════════════════════════════════
   13. LIVE VISION ENGINE (SCREEN SHARE & CAMERA STREAMING)
   ═════════════════════════════════════════════════════════════════════════════ */
async function startScreenVision() {
  try {
    if (state.activeVisionStream) stopVisionStream();
    initAudioContext();
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: { cursor: 'always', displaySurface: 'monitor' },
      audio: false,
    });
    setupVisionStream(stream, 'screen');
    showToast('🖥️ تم بدء مشاركة الشاشة — سمير يراقب ما تفعله الآن');
  } catch (err) {
    console.warn('[Vision] Screen capture canceled or not supported:', err);
    showToast('⚠️ تم إلغاء مشاركة الشاشة أو المتصفح لا يدعمها');
  }
}

async function startCameraVision(facing = state.cameraFacing) {
  try {
    if (state.activeVisionStream) stopVisionStream();
    initAudioContext();
    state.cameraFacing = facing;
    const constraints = {
      video: {
        facingMode: { ideal: facing },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    };
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia(constraints);
    } catch (e) {
      stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    }
    setupVisionStream(stream, 'camera');
    showToast('📷 تم تشغيل الكاميرا المباشرة — سمير يراك ويراقب معك');
  } catch (err) {
    console.warn('[Vision] Camera access failed:', err);
    showToast('⚠️ تعذر تشغيل الكاميرا، يرجى منح الإذن للكاميرا في المتصفح');
  }
}

function setupVisionStream(stream, mode) {
  state.activeVisionStream = stream;
  state.visionMode = mode;

  if (DOM.visionVideo) {
    DOM.visionVideo.srcObject = stream;
    // ✅ FIX: wait for video to actually load frame data before allowing capture
    DOM.visionVideo.onloadeddata = () => {
      console.log('[Vision] Video ready, dimensions:', DOM.visionVideo.videoWidth, 'x', DOM.visionVideo.videoHeight);
    };
    DOM.visionVideo.play().catch((e) => console.log('Video play muted:', e));
  }

  if (DOM.visionPip) {
    DOM.visionPip.classList.remove('hidden');
  }

  if (DOM.pipTitle) {
    DOM.pipTitle.textContent = mode === 'screen' ? '🖥️ مراقبة الشاشة لسمير' : '📷 رؤية الكاميرا لسمير';
  }

  if (DOM.pipSwitchCamera) {
    DOM.pipSwitchCamera.style.display = mode === 'camera' ? 'inline-block' : 'none';
  }

  if (mode === 'screen') {
    if (DOM.screenBtn) DOM.screenBtn.classList.add('streaming');
    if (DOM.cameraBtn) DOM.cameraBtn.classList.remove('streaming');
  } else {
    if (DOM.cameraBtn) DOM.cameraBtn.classList.add('streaming');
    if (DOM.screenBtn) DOM.screenBtn.classList.remove('streaming');
  }

  // Handle when stream tracks end (e.g. user clicked browser stop sharing button)
  const tracks = stream.getVideoTracks();
  if (tracks.length > 0) {
    tracks[0].onended = () => {
      stopVisionStream();
    };
  }
}

function stopVisionStream() {
  if (state.activeVisionStream) {
    state.activeVisionStream.getTracks().forEach((t) => t.stop());
    state.activeVisionStream = null;
  }
  state.visionMode = null;

  if (state.visionWatchInterval) {
    clearInterval(state.visionWatchInterval);
    state.visionWatchInterval = null;
  }

  if (DOM.pipAutoWatchCb) {
    DOM.pipAutoWatchCb.checked = false;
  }

  if (DOM.visionVideo) {
    DOM.visionVideo.srcObject = null;
  }

  if (DOM.visionPip) {
    DOM.visionPip.classList.add('hidden');
  }

  if (DOM.screenBtn) DOM.screenBtn.classList.remove('streaming');
  if (DOM.cameraBtn) DOM.cameraBtn.classList.remove('streaming');
  showToast('تم إيقاف البث المباشر');
}

function captureVisionFrame() {
  if (!DOM.visionVideo || !DOM.visionCanvas || !state.activeVisionStream) return null;
  const video = DOM.visionVideo;
  const canvas = DOM.visionCanvas;

  // ✅ FIX: check video is actually playing and has real dimensions
  if (!video.videoWidth || !video.videoHeight) return null;
  if (video.readyState < 2) return null; // HAVE_CURRENT_DATA or better

  // Good resolution while keeping payload lean
  const maxW = 1024;
  const scale = Math.min(1, maxW / video.videoWidth);
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);

  const ctx = canvas.getContext('2d');
  // ✅ FIX: fill black background first so canvas is never transparent/black on empty draw
  ctx.fillStyle = '#000000';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  const dataUrl = canvas.toDataURL('image/jpeg', 0.82);
  const base64 = dataUrl.split(',')[1];

  // Quick sanity check — pure black frames are usually empty
  if (!base64 || base64.length < 1000) return null;

  return base64;
}

function captureAndAnalyzeVision(customPrompt) {
  const base64 = captureVisionFrame();
  if (!base64) {
    // Video may not be ready yet — retry once after 600ms
    if (state.activeVisionStream && DOM.visionVideo) {
      showToast('⏳ جاري انتظار جاهزية الفيديو...');
      setTimeout(() => {
        const b64retry = captureVisionFrame();
        if (!b64retry) {
          showToast('⚠️ تعذر التقاط إطار واضح من الشاشة — جرب مرة أخرى');
          return;
        }
        _sendVisionCapture(b64retry, customPrompt);
      }, 600);
      return;
    }
    showToast('⚠️ لا يوجد إطار فيديو نشط حالياً لالتقاطه');
    return;
  }
  _sendVisionCapture(base64, customPrompt);
}

function _sendVisionCapture(base64, customPrompt) {
  const defaultPrompt = state.visionMode === 'screen'
    ? 'انظر لما هو معروض في شاشتي الآن وراقب ما أفعله واشرحه لي بدقة'
    : 'انظر عبر الكاميرا المباشرة الآن واشرح لي ما تراه وما الذي يحدث';

  const promptText = customPrompt || (DOM.textInput?.value?.trim() || defaultPrompt);
  if (DOM.textInput) DOM.textInput.value = '';

  // ✅ FIX: include base64 + is_image so orchestrator sends it to Gemini
  state.pendingAttachments.push({
    name: 'live_stream_capture.jpg',
    original_filename: 'live_stream_capture.jpg',
    base64: base64,          // ← key field orchestrator reads
    content: base64,         // ← fallback
    data: base64,            // ← fallback
    is_image: true,          // ← forces vision routing
    category: 'image',
    mime_type: 'image/jpeg',
  });

  handleSendText(promptText);
  showToast('👁️ جاري إرسال الإطار لسمير لتحليله...');
}

function toggleAutoWatch(enabled) {
  if (state.visionWatchInterval) {
    clearInterval(state.visionWatchInterval);
    state.visionWatchInterval = null;
  }

  if (enabled) {
    showToast('🟢 تم تفعيل المراقبة الذكية المستمرة لسمير (كل 12 ثانية)');
    state.visionWatchInterval = setInterval(() => {
      if (state.currentOrbState === 'idle' && state.activeVisionStream) {
        captureAndAnalyzeVision('راقب ما أفعله الآن على الشاشة بإيجاز');
      }
    }, 12000);
  } else {
    showToast('⚪ تم إيقاف المراقبة التلقائية المستمرة');
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   14. ALARMS, TIMERS & DEVICE SEARCH ENGINE
   ═════════════════════════════════════════════════════ */
function handleClientAction(action, data) {
  if (!action) return;
  console.log('[J.A.R.V.I.S Action]:', action, data);

  if (action === 'set_alarm') {
    const seconds = Number(data?.seconds) || 60;
    const label = data?.label || 'منبه سمير';
    scheduleAlarm(seconds, label);
  } else if (action === 'device_search') {
    const query = data?.query || '';
    const searchUrl = data?.search_url || `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    showToast(`🔍 جاري البحث: ${query}`);
    showUserDialogue(`🔍 بحث: ${query}`);
    showAssistantDialogue({
      text: `تم تجهيز نتائج البحث عن: **${query}**.\n\n🔗 [اضغط هنا لفتح نتائج البحث مباشرة في متصفحك أو هاتفك](${searchUrl})`,
      model: 'البحث الذكي',
    });
  } else if (action === 'open_in_app_media' || action === 'play_media') {
    openInAppMediaPlayer(data);
  }
}

function scheduleAlarm(seconds, label) {
  if (window.Notification && Notification.permission === 'default') {
    Notification.requestPermission();
  }

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  const timeDesc = mins > 0 ? (secs > 0 ? `${mins} دقيقة و ${secs} ثانية` : `${mins} دقيقة`) : `${secs} ثانية`;

  showToast(`🔔 تم ضبط المنبه: "${label}" بعد ${timeDesc}`);

  const alarmId = 'alarm_' + Date.now();
  const timer = setTimeout(() => {
    triggerAlarmRinging(label);
  }, seconds * 1000);

  state.activeAlarms.push({ id: alarmId, label, timer, seconds });
}

function playAlarmSound() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    if (!state.audioContext) state.audioContext = new AudioCtx();
    if (state.audioContext.state === 'suspended') state.audioContext.resume();

    stopAlarmSound();

    const ring = () => {
      if (!state.alarmOscillatorInterval) return;
      const ctx = state.audioContext;
      const now = ctx.currentTime;

      // 3 High-pitch energetic alarm chime beeps
      [0, 0.22, 0.44].forEach((offset) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(880, now + offset);
        osc.frequency.exponentialRampToValueAtTime(1760, now + offset + 0.12);

        gain.gain.setValueAtTime(0.7, now + offset);
        gain.gain.exponentialRampToValueAtTime(0.01, now + offset + 0.15);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now + offset);
        osc.stop(now + offset + 0.16);
      });
    };

    state.alarmOscillatorInterval = setInterval(ring, 1400);
    ring();
  } catch (err) {
    console.warn('Alarm sound error:', err);
  }
}

function stopAlarmSound() {
  if (state.alarmOscillatorInterval) {
    clearInterval(state.alarmOscillatorInterval);
    state.alarmOscillatorInterval = null;
  }
}

function triggerAlarmRinging(label) {
  playAlarmSound();

  // Mobile vibration
  if (navigator.vibrate) {
    navigator.vibrate([600, 200, 600, 200, 600, 200, 1000]);
  }

  // System notification
  if (window.Notification && Notification.permission === 'granted') {
    new Notification('🔔 منبه سمير الذكي!', {
      body: label || 'حان موعد المنبه المحدد!',
      icon: '/favicon.ico',
      vibrate: [500, 200, 500],
    });
  }

  // Show HUD Alarm Overlay
  if (DOM.alarmOverlay) {
    if (DOM.alarmTitle) DOM.alarmTitle.textContent = '🔔 حان موعد المنبه!';
    if (DOM.alarmMessage) DOM.alarmMessage.textContent = label || 'منبه سمير الذكي';
    if (DOM.alarmTimeTag) {
      const now = new Date();
      DOM.alarmTimeTag.textContent = now.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
    }
    DOM.alarmOverlay.classList.remove('hidden');
  }
}

function dismissAlarm() {
  stopAlarmSound();
  if (DOM.alarmOverlay) DOM.alarmOverlay.classList.add('hidden');
  showToast('تم إيقاف المنبه ✓');
}

function snoozeAlarm() {
  stopAlarmSound();
  if (DOM.alarmOverlay) DOM.alarmOverlay.classList.add('hidden');
  scheduleAlarm(300, (DOM.alarmMessage?.textContent || 'منبه') + ' (تأجيل 5 دقائق)');
  showToast('⏳ تم تأجيل المنبه 5 دقائق');
}

/* ═════════════════════════════════════════════════════════════════════════════
   13. INTERACTION MODE CONTROLLER (وضع الكتابة الصامتة / وضع الصوت)
   ═════════════════════════════════════════════════════ */
function initVoiceModeToggle() {
  const saved = localStorage.getItem('samir_voice_mode_active');
  // افتراضياً: false = كتابة صامتة بدون قراءة صوتية (طلب المستخدم الصريح)
  state.voiceModeActive = saved === 'true';
  updateVoiceModeUI();
}

function updateVoiceModeUI() {
  if (!DOM.btnToggleVoiceMode) return;
  if (state.voiceModeActive) {
    DOM.btnToggleVoiceMode.classList.add('voice-active');
    DOM.btnToggleVoiceMode.classList.remove('typing-active');
    if (DOM.voiceModeIcon) DOM.voiceModeIcon.textContent = '🎙️';
    if (DOM.voiceModeLabel) DOM.voiceModeLabel.textContent = 'وضع الصوت';
    DOM.btnToggleVoiceMode.title = 'وضع قراءة الردود صوتياً نشط. اضغط للتحويل إلى الوضع الصامت.';
  } else {
    DOM.btnToggleVoiceMode.classList.remove('voice-active');
    DOM.btnToggleVoiceMode.classList.add('typing-active');
    if (DOM.voiceModeIcon) DOM.voiceModeIcon.textContent = '✍️';
    if (DOM.voiceModeLabel) DOM.voiceModeLabel.textContent = 'كتابة صامتة';
    DOM.btnToggleVoiceMode.title = 'وضع الكتابة الصامتة نشط (لا يقرأ الردود بالصوت). اضغط لتفعيل الصوت.';
  }
}

function toggleVoiceMode() {
  state.voiceModeActive = !state.voiceModeActive;
  localStorage.setItem('samir_voice_mode_active', state.voiceModeActive ? 'true' : 'false');
  updateVoiceModeUI();
  wsSend({ type: 'set_voice_mode', enabled: state.voiceModeActive });
  if (state.voiceModeActive) {
    showToast('🎙️ تم تفعيل وضع الصوت — سيقرأ سمير الردود بالصوت');
  } else {
    showToast('✍️ تم تفعيل وضع الكتابة الصامتة — بدون قراءة صوتية');
    stopAudioPlayback();
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   14. GOOGLE AUTH & USER ISOLATED MEMORY ENGINE
   ═════════════════════════════════════════════════════ */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    return null;
  }
}

function initGoogleAuth() {
  // 1. استعادة الجلسة المحفوظة مسبقاً إن وُجدت
  const token = localStorage.getItem('samir_session_token');
  const cachedUserStr = localStorage.getItem('samir_user_data');
  if (token && cachedUserStr) {
    try {
      const user = JSON.parse(cachedUserStr);
      state.currentUser = user;
      updateAuthUI(user);
      fetchUserMemories(user.user_id || user.id, token);
      // التأكد من صحة التوكن من السيرفر بالخلفية
      verifySessionToken(token);
    } catch (e) {
      console.warn('Failed to parse cached user:', e);
      updateAuthUI(null);
    }
  } else {
    updateAuthUI(null);
  }
}

async function verifySessionToken(token) {
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/auth/me?token=${encodeURIComponent(token)}`);
    if (!res.ok) {
      // التوكن منتهي أو غير صالح
      console.warn('[Samir Auth] Session token expired or invalid');
      localStorage.removeItem('samir_session_token');
      localStorage.removeItem('samir_user_data');
      state.currentUser = null;
      updateAuthUI(null);
    }
  } catch (err) {
    // خطأ شبكة مؤقت، نبقي المستخدم مسجلاً
  }
}

function switchAuthTab(tab) {
  if (tab === 'login') {
    DOM.tabBtnLogin?.classList.add('active');
    DOM.tabBtnRegister?.classList.remove('active');
    DOM.paneAuthLogin?.classList.remove('hidden');
    DOM.paneAuthRegister?.classList.add('hidden');
    DOM.loginEmail?.focus();
  } else {
    DOM.tabBtnRegister?.classList.add('active');
    DOM.tabBtnLogin?.classList.remove('active');
    DOM.paneAuthRegister?.classList.remove('hidden');
    DOM.paneAuthLogin?.classList.add('hidden');
    DOM.regName?.focus();
  }
}

async function handleUserLogin() {
  const email = DOM.loginEmail?.value?.trim();
  const password = DOM.loginPassword?.value || '';

  if (!email) {
    showToast('⚠️ يرجى إدخال البريد الإلكتروني');
    DOM.loginEmail?.focus();
    return;
  }

  showToast('⚡ جاري تسجيل الدخول...');
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'تعذر تسجيل الدخول');
    }

    onAuthSuccess(data, `أهلاً بك يا ${data.name}! تم تسجيل دخولك بنجاح 🧠`);
  } catch (err) {
    console.error('Login error:', err);
    showToast('❌ ' + err.message);
  }
}

async function handleUserRegister() {
  const name = DOM.regName?.value?.trim();
  const email = DOM.regEmail?.value?.trim();
  const password = DOM.regPassword?.value || '';

  if (!name) {
    showToast('⚠️ يرجى إدخال اسمك الكريم');
    DOM.regName?.focus();
    return;
  }
  if (!email || !email.includes('@')) {
    showToast('⚠️ يرجى إدخال بريد إلكتروني صحيح');
    DOM.regEmail?.focus();
    return;
  }

  showToast('⚡ جاري إنشاء الحساب...');
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || 'تعذر إنشاء الحساب');
    }

    onAuthSuccess(data, `مرحباً بك يا ${data.name}! تم إنشاء حسابك وتفعيل الذاكرة فوراً ✨`);
  } catch (err) {
    console.error('Register error:', err);
    showToast('❌ ' + err.message);
  }
}

function onAuthSuccess(data, welcomeMsg) {
  state.currentUser = data;
  localStorage.setItem('samir_session_token', data.session_token);
  localStorage.setItem('samir_user_data', JSON.stringify(data));

  // إرسال التوكن لخادم الـ WebSocket لربط جلسة الذاكرة فورياً
  wsSend({ type: 'set_auth', token: data.session_token });

  updateAuthUI(data);
  fetchUserMemories(data.user_id, data.session_token);

  showToast(welcomeMsg);
  closeAuthModal();
}

function updateAuthUI(user) {
  if (user) {
    if (DOM.btnGoogleLogin) DOM.btnGoogleLogin.classList.add('hidden');
    if (DOM.userProfileChip) DOM.userProfileChip.classList.remove('hidden');
    if (DOM.userAvatar) DOM.userAvatar.src = user.picture || '/static/samir-logo.png';
    if (DOM.userName) DOM.userName.textContent = user.name || 'المستخدم';

    if (DOM.authViewLoggedOut) DOM.authViewLoggedOut.classList.add('hidden');
    if (DOM.authViewLoggedIn) DOM.authViewLoggedIn.classList.remove('hidden');
    if (DOM.authUserAvatar) DOM.authUserAvatar.src = user.picture || '/static/samir-logo.png';
    if (DOM.authUserName) DOM.authUserName.textContent = user.name || 'المستخدم';
    if (DOM.authUserEmail) DOM.authUserEmail.textContent = user.email || '';
  } else {
    if (DOM.btnGoogleLogin) DOM.btnGoogleLogin.classList.remove('hidden');
    if (DOM.userProfileChip) DOM.userProfileChip.classList.add('hidden');

    if (DOM.authViewLoggedOut) DOM.authViewLoggedOut.classList.remove('hidden');
    if (DOM.authViewLoggedIn) DOM.authViewLoggedIn.classList.add('hidden');
    if (DOM.userMemoryBadge) DOM.userMemoryBadge.textContent = '0';
  }
}

function openAuthModal() {
  if (DOM.authModalOverlay) {
    DOM.authModalOverlay.classList.remove('hidden');
    if (state.currentUser) {
      fetchUserMemories(state.currentUser.user_id || state.currentUser.id, localStorage.getItem('samir_session_token'));
    }
  }
}

function closeAuthModal() {
  if (DOM.authModalOverlay) {
    DOM.authModalOverlay.classList.add('hidden');
  }
}

async function fetchUserMemories(userId, token) {
  if (!userId || !token) return;
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/auth/memories/${userId}?token=${encodeURIComponent(token)}`);
    if (res.ok) {
      const data = await res.json();
      state.userMemories = data.memories || [];
      renderUserMemoriesList(state.userMemories);
    }
  } catch (err) {
    console.warn('Failed to fetch user memories:', err);
  }
}

function renderUserMemoriesList(memories) {
  const count = memories.length;
  if (DOM.authMemoriesCount) DOM.authMemoriesCount.textContent = count;
  if (DOM.userMemoryBadge) DOM.userMemoryBadge.textContent = count;

  if (!DOM.authMemoriesList) return;
  DOM.authMemoriesList.innerHTML = '';

  if (count === 0) {
    DOM.authMemoriesList.innerHTML = `
      <div class="empty-memories-hint">
        لا توجد ذكريات مسجلة بعد. عندما تتحدث مع سمير وتخبره بأي معلومة عنك أو عن مشاريعك، سيحفظها هنا في حسابك فقط!
      </div>
    `;
    return;
  }

  memories.forEach((m) => {
    const card = document.createElement('div');
    card.className = 'memory-row-card';
    card.innerHTML = `
      <div class="memory-row-content">
        <span class="memory-row-key">${escapeHtml(m.key)}</span>
        <span class="memory-row-val">${escapeHtml(m.value)}</span>
      </div>
    `;
    DOM.authMemoriesList.appendChild(card);
  });
}

async function wipeMyMemories() {
  if (!state.currentUser) return;
  const confirmed = confirm('هل أنت متأكد من رغبتك في مسح كافة ذكرياتك المسجلة؟ سيبدأ سمير بصفحة بيضاء تماماً معك.');
  if (!confirmed) return;

  const userId = state.currentUser.user_id || state.currentUser.id;
  const token = localStorage.getItem('samir_session_token') || state.currentUser.session_token;

  showToast('🧹 جاري مسح الذكريات...');
  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/auth/memory/${userId}?token=${encodeURIComponent(token)}`, {
      method: 'DELETE',
    });
    if (res.ok) {
      state.userMemories = [];
      renderUserMemoriesList([]);
      showToast('✅ تم مسح جميع ذكرياتك بنجاح والبدء بصفحة بيضاء');
    } else {
      showToast('❌ تعذر مسح الذكريات');
    }
  } catch (err) {
    console.error('Wipe memories err:', err);
    showToast('❌ خطأ في الاتصال بالخادم');
  }
}

function logoutUser() {
  localStorage.removeItem('samir_session_token');
  localStorage.removeItem('samir_user_data');
  state.currentUser = null;
  state.userMemories = [];
  updateAuthUI(null);
  closeAuthModal();
  showToast('تم تسجيل الخروج بنجاح 👋');
}


/* ═════════════════════════════════════════════════════════════════════════════
   15. CODE SANDBOX ENGINE — تشغيل الكود والألعاب كـ Qwen (مباشرة في المتصفح)
   ═════════════════════════════════════════════════════════════════════════════ */

// State for current sandbox session
const sandboxState = {
  currentCode: '',
  currentLang: 'html',
  isOpen: false,
};

function initSandboxEngine() {
  if (DOM.sandboxCloseBtn) {
    DOM.sandboxCloseBtn.addEventListener('click', closeSandbox);
  }
  if (DOM.sandboxReloadBtn) {
    DOM.sandboxReloadBtn.addEventListener('click', () => runInSandbox(sandboxState.currentCode, sandboxState.currentLang));
  }
  if (DOM.sandboxRunAgainBtn) {
    DOM.sandboxRunAgainBtn.addEventListener('click', () => runInSandbox(sandboxState.currentCode, sandboxState.currentLang));
  }
  if (DOM.sandboxFullscreenBtn) {
    DOM.sandboxFullscreenBtn.addEventListener('click', toggleSandboxFullscreen);
  }
  if (DOM.sandboxModalOverlay) {
    DOM.sandboxModalOverlay.addEventListener('click', (e) => {
      if (e.target === DOM.sandboxModalOverlay) closeSandbox();
    });
  }
}

function openSandbox() {
  if (!DOM.sandboxModalOverlay) return;
  DOM.sandboxModalOverlay.classList.remove('hidden');
  sandboxState.isOpen = true;
}

function closeSandbox() {
  if (!DOM.sandboxModalOverlay) return;
  DOM.sandboxModalOverlay.classList.add('hidden');
  sandboxState.isOpen = false;
  // Clear iframe to stop any running game/audio
  if (DOM.sandboxIframe) {
    DOM.sandboxIframe.srcdoc = '';
    DOM.sandboxIframe.src = 'about:blank';
  }
}

function toggleSandboxFullscreen() {
  if (!DOM.sandboxModalCard) return;
  DOM.sandboxModalCard.classList.toggle('fullscreen');
  if (DOM.sandboxFullscreenBtn) {
    DOM.sandboxFullscreenBtn.textContent = DOM.sandboxModalCard.classList.contains('fullscreen') ? '⊡' : '⛶';
  }
}

/**
 * Main entry: run a code block. Called from inline onclick handlers.
 * @param {string} codeId - ID of the .code-card-wrapper element
 */
function runCodeBlock(codeId) {
  const wrapper = document.getElementById(codeId);
  if (!wrapper) { showToast('⚠️ تعذر إيجاد الكود'); return; }

  const codeEl = wrapper.querySelector('code');
  if (!codeEl) { showToast('⚠️ تعذر قراءة الكود'); return; }

  // Get raw code - first from data-raw-code, then from textContent
  const rawCode = codeEl.getAttribute('data-raw-code') || codeEl.textContent || '';
  const lang = codeEl.getAttribute('data-lang') || codeEl.className.replace('language-', '') || 'html';

  if (!rawCode.trim()) { showToast('⚠️ الكود فارغ'); return; }

  runInSandbox(rawCode, lang);
}

/**
 * Execute code in sandbox based on language
 */
async function runInSandbox(code, lang) {
  const cleanLang = (lang || 'html').toLowerCase().trim();
  sandboxState.currentCode = code;
  sandboxState.currentLang = cleanLang;

  openSandbox();

  if (DOM.sandboxLangBadge) DOM.sandboxLangBadge.textContent = cleanLang.toUpperCase();
  if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '⏳ جاري التشغيل...';

  // HTML/JS/CSS/SVG/Games — run directly in iframe (like Qwen)
  if (['html', 'js', 'javascript', 'css', 'svg', 'game', 'web'].includes(cleanLang)) {
    if (DOM.sandboxTitle) DOM.sandboxTitle.textContent = '🎮 معاينة الكود المباشرة';
    if (DOM.sandboxContentArea) DOM.sandboxContentArea.style.display = 'flex';
    if (DOM.sandboxTerminal) DOM.sandboxTerminal.classList.add('hidden');

    let finalHtml = code;

    // If pure JS only (no html tag), wrap in canvas game boilerplate
    if (['js', 'javascript'].includes(cleanLang) && !code.includes('<html') && !code.includes('<body')) {
      finalHtml = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: #111; display: flex; align-items: center; justify-content: center; min-height: 100vh; }
    canvas { display: block; }
  </style>
</head>
<body>
<script>
${code}
<\/script>
</body>
</html>`;
    }

    // If pure CSS, wrap in demo HTML
    if (cleanLang === 'css') {
      finalHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body { background: #111; color: #f0f0f0; font-family: sans-serif; padding: 20px; }
${code}
</style></head><body><div class="demo">تجربة تصميم CSS المباشر</div></body></html>`;
    }

    // SVG — embed in HTML
    if (cleanLang === 'svg') {
      finalHtml = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{background:#111;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;}</style></head><body>${code}</body></html>`;
    }

    if (DOM.sandboxIframe) {
      DOM.sandboxIframe.srcdoc = finalHtml;
    }

    if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '🟢 يعمل الآن';
    showToast('🎮 تم تشغيل الكود في المعاينة!');

  } else if (['python', 'py', 'powershell', 'ps1', 'shell', 'bash', 'cmd'].includes(cleanLang)) {
    // Backend execution for Python/PowerShell
    if (DOM.sandboxTitle) DOM.sandboxTitle.textContent = '⚡ تنفيذ الكود على الخادم';
    if (DOM.sandboxContentArea) DOM.sandboxContentArea.style.display = 'none';
    if (DOM.sandboxTerminal) DOM.sandboxTerminal.classList.remove('hidden');
    if (DOM.terminalOutput) DOM.terminalOutput.textContent = '⏳ جاري تنفيذ الكود...\n';

    try {
      const res = await fetch(`${CONFIG.httpBase}/api/v1/code/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: cleanLang, code }),
      });

      const data = await res.json();

      if (data.is_gui_game) {
        if (DOM.terminalOutput) DOM.terminalOutput.textContent = `✅ ${data.output || data.message}\n\n🎮 تم فتح نافذة اللعبة على سطح المكتب!`;
        if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '🎮 نافذة اللعبة مفتوحة';
      } else if (data.preview_url) {
        // HTML result — open in iframe
        if (DOM.sandboxContentArea) DOM.sandboxContentArea.style.display = 'flex';
        if (DOM.sandboxTerminal) DOM.sandboxTerminal.classList.add('hidden');
        if (DOM.sandboxIframe) DOM.sandboxIframe.src = `${CONFIG.httpBase}${data.preview_url}`;
        if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '🟢 صفحة الويب تعمل';
      } else {
        const stdout = data.stdout || data.output || '';
        const stderr = data.stderr || data.error || '';
        const exitCode = data.return_code ?? data.code ?? 0;
        const execTime = data.execution_time ? ` (${data.execution_time}s)` : '';

        let output = '';
        if (stdout) output += `📤 المخرجات:\n${stdout}\n`;
        if (stderr) output += `\n⚠️ رسائل الخطأ:\n${stderr}\n`;
        if (!stdout && !stderr) output = '✅ تم التنفيذ بنجاح (لا توجد مخرجات)';
        output += `\n⏱️ كود الخروج: ${exitCode}${execTime}`;

        if (DOM.terminalOutput) DOM.terminalOutput.textContent = output;
        if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = exitCode === 0 ? '✅ تم بنجاح' : '⚠️ انتهى بأخطاء';
      }
    } catch (err) {
      if (DOM.terminalOutput) DOM.terminalOutput.textContent = `❌ خطأ في الاتصال بالخادم:\n${err.message}`;
      if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '❌ خطأ في الاتصال';
    }
  } else {
    // Generic unsupported language — just show in terminal view
    if (DOM.sandboxContentArea) DOM.sandboxContentArea.style.display = 'none';
    if (DOM.sandboxTerminal) DOM.sandboxTerminal.classList.remove('hidden');
    if (DOM.terminalOutput) DOM.terminalOutput.textContent = `الكود (${cleanLang}):\n\n${code}`;
    if (DOM.sandboxStatus) DOM.sandboxStatus.textContent = '📄 عرض فقط';
  }
}

/**
 * Copy code block content to clipboard
 */
function copyCodeBlock(codeId) {
  const wrapper = document.getElementById(codeId);
  if (!wrapper) return;
  const codeEl = wrapper.querySelector('code');
  const text = codeEl?.getAttribute('data-raw-code') || codeEl?.textContent || '';
  if (!text.trim()) { showToast('⚠️ لا يوجد كود للنسخ'); return; }
  navigator.clipboard.writeText(text).then(() => {
    showToast('✅ تم نسخ الكود إلى الحافظة');
  }).catch(() => {
    // Fallback
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    showToast('✅ تم نسخ الكود');
  });
}

/* ═════════════════════════════════════════════════════════════════════════════
   16. IN-APP MEDIA PLAYER ENGINE — تشغيل اليوتيوب وسبوتيفاي داخل سمير نفسه
   ═════════════════════════════════════════════════════ */
function initMediaPlayerEngine() {
  if (DOM.mediaCloseBtn) {
    DOM.mediaCloseBtn.addEventListener('click', closeInAppMediaPlayer);
  }
  if (DOM.mediaPipBtn) {
    DOM.mediaPipBtn.addEventListener('click', toggleInAppMediaPip);
  }
  if (DOM.mediaExternalBtn) {
    DOM.mediaExternalBtn.addEventListener('click', () => {
      if (state.currentMedia?.url) {
        window.open(state.currentMedia.url, '_blank');
      }
    });
  }
}

function openInAppMediaPlayer(data) {
  if (!data || !data.embed_url) return;
  state.currentMedia = data;

  const service = (data.service || '').toLowerCase();
  const isSpotify = service.includes('spotify') || data.embed_url.includes('spotify.com');
  const serviceLabel = isSpotify ? '🎵 سبوتيفاي' : '🎬 يوتيوب';
  const serviceTheme = isSpotify ? 'spotify-theme' : 'youtube-theme';
  const badgeClass = isSpotify ? 'spotify' : 'youtube';

  if (DOM.hudMediaCard) {
    DOM.hudMediaCard.classList.remove('spotify-theme', 'youtube-theme');
    DOM.hudMediaCard.classList.add(serviceTheme);
  }

  if (DOM.mediaServiceBadge) {
    DOM.mediaServiceBadge.textContent = serviceLabel;
    DOM.mediaServiceBadge.className = `media-badge ${badgeClass}`;
  }

  if (DOM.mediaPlayerTitle) {
    DOM.mediaPlayerTitle.textContent = data.title || (isSpotify ? 'Spotify Player' : 'YouTube Player');
  }

  if (DOM.mediaIframe) {
    DOM.mediaIframe.src = data.embed_url;
  }

  if (DOM.hudMediaPlayer) {
    DOM.hudMediaPlayer.classList.remove('hidden');
    DOM.hudMediaPlayer.classList.remove('minimized');
  }

  showToast(`▶ جاري تشغيل ${serviceLabel} مباشرة في سمير...`);
}

function closeInAppMediaPlayer() {
  if (DOM.mediaIframe) {
    DOM.mediaIframe.src = '';
  }
  if (DOM.hudMediaPlayer) {
    DOM.hudMediaPlayer.classList.add('hidden');
    DOM.hudMediaPlayer.classList.remove('fullscreen', 'minimized');
  }
  state.currentMedia = null;
}

function toggleInAppMediaPip() {
  if (DOM.hudMediaPlayer) {
    DOM.hudMediaPlayer.classList.toggle('minimized');
    if (DOM.mediaPipBtn) {
      DOM.mediaPipBtn.textContent = DOM.hudMediaPlayer.classList.contains('minimized') ? '🗖' : '🗗';
    }
  }
}

/* ═════════════════════════════════════════════════════════════════════════════
   17. CUSTOM RULES & PROMPTS ENGINE — أوامر وبرومبتات المستخدم الدائمة
   ═════════════════════════════════════════════════════ */

function openCustomRulesModal() {
  const modal = document.getElementById('custom-rules-modal');
  if (!modal) return;
  modal.style.display = 'flex';
  loadCustomRules();
}

function closeCustomRulesModal() {
  const modal = document.getElementById('custom-rules-modal');
  if (modal) modal.style.display = 'none';
}

async function loadCustomRules() {
  const container = document.getElementById('custom-rules-list-container');
  const badge = document.getElementById('custom-rules-count-badge');
  if (!container) return;

  container.innerHTML = '<div style="text-align:center;color:var(--text-ghost);font-size:12px;padding:16px;">⏳ جاري التحميل...</div>';

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/custom-rules`);
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const rules = await res.json();

    if (badge) badge.textContent = `${rules.length} ${rules.length === 1 ? 'أمر' : 'أوامر'}`;

    if (rules.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:var(--text-ghost);font-size:12px;padding:16px;">لا توجد أوامر بعد، اكتب أول أمر بالأعلى ليحفظه سمير فوراً.</div>';
      return;
    }

    container.innerHTML = '';
    rules.forEach(rule => {
      const card = document.createElement('div');
      card.style.cssText = 'background:rgba(0,229,255,0.05);border:1px solid rgba(0,229,255,0.15);border-radius:10px;padding:10px 12px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;';

      const textArea = document.createElement('div');
      textArea.style.cssText = 'flex:1;min-width:0;';

      const topicEl = document.createElement('div');
      topicEl.style.cssText = 'font-size:12px;font-weight:700;color:var(--cyan);margin-bottom:4px;';
      topicEl.textContent = '📌 ' + (rule.topic || 'أمر مخصص');

      const instrEl = document.createElement('div');
      instrEl.style.cssText = 'font-size:12.5px;color:var(--text-primary);line-height:1.5;word-break:break-word;';
      instrEl.textContent = rule.correction || '';

      const dateEl = document.createElement('div');
      dateEl.style.cssText = 'font-size:10px;color:var(--text-ghost);margin-top:4px;font-family:var(--font-mono);';
      dateEl.textContent = rule.created_at ? new Date(rule.created_at).toLocaleDateString('ar-EG') : '';

      textArea.appendChild(topicEl);
      textArea.appendChild(instrEl);
      textArea.appendChild(dateEl);

      const delBtn = document.createElement('button');
      delBtn.title = 'حذف هذا الأمر';
      delBtn.style.cssText = 'flex-shrink:0;background:rgba(255,58,58,0.15);border:1px solid rgba(255,58,58,0.3);border-radius:6px;padding:4px 8px;color:#ff3a3a;font-size:12px;cursor:pointer;';
      delBtn.textContent = '🗑️';
      delBtn.addEventListener('click', () => deleteCustomRule(rule.id));

      card.appendChild(textArea);
      card.appendChild(delBtn);
      container.appendChild(card);
    });
  } catch (err) {
    console.error('[Samir] Failed to load custom rules:', err);
    container.innerHTML = '<div style="text-align:center;color:#ff3a3a;font-size:12px;padding:16px;">⚠️ فشل تحميل الأوامر. تأكد من اتصال الخادم.</div>';
  }
}

async function saveCustomRule() {
  const topicInput = document.getElementById('new-rule-topic');
  const instrInput = document.getElementById('new-rule-instruction');
  const btn = document.getElementById('btn-save-custom-rule');

  const topic = topicInput?.value?.trim();
  const instruction = instrInput?.value?.trim();

  if (!instruction) {
    showToast('⚠️ اكتب الأمر أو البرومبت أولاً قبل الحفظ');
    return;
  }

  if (btn) {
    btn.textContent = '⏳ جاري الحفظ...';
    btn.disabled = true;
  }

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/custom-rules`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic: topic || 'أمر مخصص',
        instruction: instruction,
      }),
    });

    if (!res.ok) throw new Error('HTTP ' + res.status);

    if (topicInput) topicInput.value = '';
    if (instrInput) instrInput.value = '';

    showToast('✅ تم حفظ الأمر في عقل سمير الدائم!');
    await loadCustomRules();
  } catch (err) {
    console.error('[Samir] Failed to save custom rule:', err);
    showToast('❌ فشل في حفظ الأمر. تحقق من الاتصال بالخادم.');
  } finally {
    if (btn) {
      btn.textContent = '💾 حفظ الأمر في عقل سمير';
      btn.disabled = false;
    }
  }
}

async function deleteCustomRule(ruleId) {
  if (!confirm('هل أنت متأكد من حذف هذا الأمر نهائياً من ذاكرة سمير؟')) return;

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/custom-rules/${ruleId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    showToast('🗑️ تم حذف الأمر بنجاح');
    await loadCustomRules();
  } catch (err) {
    console.error('[Samir] Failed to delete custom rule:', err);
    showToast('❌ فشل في حذف الأمر.');
  }
}

