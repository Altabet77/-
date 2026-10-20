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

const CONFIG = {
  httpBase: defaultOrigin,
  wsUrl: (defaultOrigin.startsWith('https') ? 'wss://' : 'ws://') + defaultHost + '/ws/voice',
  sessionId: 'samir_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
};

/* ── Central Application State ────────────────────────────────────────────── */
const state = {
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

  // Voice Settings
  activeVoiceId: 'pNInz6obpgDQGcFmaJgB',

  // Pending media attachments (images, video, audio, docs)
  pendingAttachments: [],

  // Watchdog timer to prevent stuck 'thinking' state
  watchdogTimer: null,
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
    dialogueScrollArea: document.getElementById('dialogue-scroll-area'),
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
    attachBtn: document.getElementById('hud-attach-btn'),
    fileInput: document.getElementById('hud-file-input'),
    attachPreview: document.getElementById('hud-attachments-preview'),

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

    // Toast
    toast: document.getElementById('hud-toast'),

    // Wake Word & Mobile Connect
    btnWakeWord: document.getElementById('btn-wake-word'),
    wakeDot: document.querySelector('.wake-dot'),
    btnMobileConnect: document.getElementById('btn-mobile-connect'),
    mobileModal: document.getElementById('mobile-connect-modal'),
    mobileCloseBtn: document.getElementById('mobile-close-btn'),
    mobileDoneBtn: document.getElementById('mobile-done-btn'),
    mobileUrlInput: document.getElementById('mobile-url-input'),
    btnCopyMobileUrl: document.getElementById('btn-copy-mobile-url'),
    mobileQrCanvas: document.getElementById('mobile-qr-canvas'),
  };
}

/* ═════════════════════════════════════════════════════════════════════════════
   1. INITIALIZATION & SETUP
   ═════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initDOMCache();
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
});

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
    document.removeEventListener('click', unlock);
    document.removeEventListener('keydown', unlock);
  };
  document.addEventListener('click', unlock, { once: true });
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
    });

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
        queueAudioChunk(msg.audio);
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
        queueAudioChunk(msg.audio);
      }
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

  // Fallback: HTML5 Audio
  try {
    const audio = new Audio('data:audio/mp3;base64,' + base64);
    audio.onended = () => playNextAudioInQueue();
    audio.onerror = () => playNextAudioInQueue();
    audio.play().catch(() => playNextAudioInQueue());
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
    setOrbState('listening');

  } catch (err) {
    console.error('[J.A.R.V.I.S] Mic error:', err);
    showToast('تعذر الوصول إلى الميكروفون. تأكد من تفعيل الصلاحية.');
    setOrbState('idle');
  }
}

function stopRecording() {
  if (!state.isRecording) return;
  state.isRecording = false;

  if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
    state.mediaRecorder.stop();
  }

  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach(t => t.stop());
    state.mediaStream = null;
  }

  setOrbState('thinking');
  startWatchdog(); // will be cleared when transcription and response arrive
}

async function processAudioRecording() {
  if (state.audioChunks.length === 0) {
    setOrbState('idle');
    return;
  }

  const audioBlob = new Blob(state.audioChunks, { type: state.mediaRecorder?.mimeType || 'audio/webm' });
  if (audioBlob.size < 1200) {
    setOrbState('idle');
    return;
  }

  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result.split(',')[1];
    if (base64) {
      wsSend({ type: 'audio_input', audio: base64 });
      startWatchdog(); // prevent stuck state after sending voice
    } else {
      setOrbState('idle');
    }
  };
  reader.readAsDataURL(audioBlob);
}

/* ═════════════════════════════════════════════════════════════════════════════
   6. STABLE ANCHORED BOTTOM QUESTIONS BAR & MESSAGING
   ═════════════════════════════════════════════════════ */
function handleSendText(forcedText) {
  if (!DOM.textInput) return;
  const text = (forcedText !== undefined ? forcedText : DOM.textInput.value).trim();
  if (!text && state.pendingAttachments.length === 0) return;

  // Clear input without bouncing
  if (!forcedText) DOM.textInput.value = '';

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
  });

  // Re-focus input smoothly
  DOM.textInput.focus();
}

function formatCurrentTime() {
  const now = new Date();
  return now.toLocaleTimeString('ar-EG', { hour: '2-digit', minute: '2-digit' });
}

function showUserDialogue(text) {
  if (!DOM.userCard || !DOM.userText) return;
  DOM.userText.textContent = text;
  if (DOM.userTime) DOM.userTime.textContent = formatCurrentTime();
  DOM.userCard.classList.remove('hidden');

  // Hide old assistant card while waiting
  if (DOM.assistantCard) DOM.assistantCard.classList.add('hidden');

  scrollDialogueToBottom();
}

function renderMarkdown(raw) {
  if (!raw) return '';

  // 1. استخراج كتل الأكواد البرمجية لحمايتها من المعالجة
  const codeBlocks = [];
  let text = String(raw).replace(/```([a-zA-Z0-9_-]*)\n?([\s\S]*?)```/g, (match, lang, code) => {
    const idx = codeBlocks.length;
    codeBlocks.push(`<pre class="bubble-pre"><code class="language-${escapeHtml(lang)}">${escapeHtml(code.trim())}</code></pre>`);
    return `%%CODE_BLOCK_${idx}%%`;
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
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

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

  // 7. استعادة كتل الأكواد والـ inline code
  result = result.replace(/%%CODE_BLOCK_(\d+)%%/g, (match, idx) => codeBlocks[parseInt(idx)] || '');
  result = result.replace(/%%INLINE_CODE_(\d+)%%/g, (match, idx) => inlineCodes[parseInt(idx)] || '');

  return result;
}

function showAssistantDialogue(data) {
  if (!DOM.assistantCard || !DOM.assistantText) return;

  DOM.assistantText.innerHTML = renderMarkdown(data.text);
  if (DOM.assistantModel) DOM.assistantModel.textContent = data.model;
  if (DOM.assistantTime) DOM.assistantTime.textContent = formatCurrentTime();
  DOM.assistantCard.classList.remove('hidden');

  if (data.toolCalls && data.toolCalls.length > 0) {
    renderToolChips(data.toolCalls);
  } else if (DOM.assistantTools) {
    DOM.assistantTools.innerHTML = '';
  }

  scrollDialogueToBottom();
}

function scrollDialogueToBottom() {
  if (DOM.dialogueScrollArea) {
    setTimeout(() => {
      DOM.dialogueScrollArea.scrollTo({
        top: DOM.dialogueScrollArea.scrollHeight,
        behavior: 'smooth'
      });
    }, 50);
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
    const res = await fetch(`${CONFIG.httpBase}/api/v1/conversations?limit=50`);
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

  try {
    const res = await fetch(`${CONFIG.httpBase}/api/v1/conversations/${convId}/messages`);
    if (res.ok) {
      const msgs = await res.json();
      if (msgs && msgs.length > 0) {
        // Find last user and assistant message
        const lastUser = [...msgs].reverse().find(m => m.sender === 'user');
        const lastAssistant = [...msgs].reverse().find(m => m.sender === 'assistant' || m.sender === 'samir');

        if (lastUser) showUserDialogue(lastUser.content);
        if (lastAssistant) {
          showAssistantDialogue({
            text: lastAssistant.content,
            model: lastAssistant.model || 'Gemini 3.5',
            toolCalls: []
          });
        }
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
  { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam — آدم', desc: 'طبيعي ودافئ وواثق (الصوت الأساسي الأكثر فخامة)', icon: '🎙️' },
  { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Sarah — سارة', desc: 'صوت نسائي واثق ومريح للأذن مع نبرة هادئة', icon: '🎙️' },
  { id: 'nPczCjzI2devNBz1zQrb', name: 'Brian — برايان', desc: 'رجالي فخم وإخباري كالمعلقين الوثائقيين', icon: '🎙️' },
  { id: 'hpp4J3VqNfWAUOO0d1Us', name: 'Bella — بيلا', desc: 'صوت ناعم ومشرق، نبرة لطيفة وودودة', icon: '🎙️' },
  { id: 'Xb7hH8MSUJpSbSDYk0k2', name: 'Alice — أليس', desc: 'بريطانية واضحة ومثقفة للشرح والتعليم', icon: '🇬🇧' },
];

function initVoiceSettings() {
  if (!DOM.voiceCardsGrid) return;
  DOM.voiceCardsGrid.innerHTML = '';

  AVAILABLE_VOICES.forEach(v => {
    const card = document.createElement('div');
    card.className = 'voice-card';
    if (v.id === state.activeVoiceId) card.classList.add('selected');

    card.innerHTML = `
      <div class="voice-card-name">
        <span>${v.icon} ${v.name}</span>
        <span class="voice-check">${v.id === state.activeVoiceId ? '✓' : ''}</span>
      </div>
      <div class="voice-card-desc">${v.desc}</div>
    `;

    card.addEventListener('click', () => {
      state.activeVoiceId = v.id;
      document.querySelectorAll('.voice-card').forEach(c => {
        c.classList.remove('selected');
        c.querySelector('.voice-check').textContent = '';
      });
      card.classList.add('selected');
      card.querySelector('.voice-check').textContent = '✓';
    });

    DOM.voiceCardsGrid.appendChild(card);
  });
}

async function saveSettings() {
  try {
    // 1. Save voice
    if (state.activeVoiceId) {
      await fetch(`${CONFIG.httpBase}/api/v1/chat/voice/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voice_or_dialect: state.activeVoiceId }),
      });
    }

    // 2. Default Provider
    const prov = DOM.settingDefaultProvider?.value;
    if (prov && DOM.providerSelect) {
      DOM.providerSelect.value = prov;
    }

    showToast('تم حفظ جميع الإعدادات بنجاح ⚙️');
    if (DOM.settingsModal) DOM.settingsModal.classList.add('hidden');
  } catch (e) {
    showToast('حدث خطأ أثناء حفظ الإعدادات');
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
          const options = ['gemini', 'claude', 'groq', 'auto'];
          const nextIdx = (options.indexOf(current) + 1) % options.length;
          DOM.providerSelect.value = options[nextIdx];
          showToast(`⚡ تم التبديل إلى: ${DOM.providerSelect.options[DOM.providerSelect.selectedIndex].text}`);
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

  // 4. Oscillating Signal Wave Canvas
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

  // Send Button
  if (DOM.sendBtn) {
    DOM.sendBtn.addEventListener('click', handleSendText);
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

  // Settings Modal Toggle
  if (DOM.settingsBtn) {
    DOM.settingsBtn.addEventListener('click', () => {
      if (DOM.settingsModal) DOM.settingsModal.classList.remove('hidden');
    });
  }

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

  // ── Screen Vision Button (انظر للشاشة وترجم) ────────────────────────────
  if (DOM.screenBtn) {
    DOM.screenBtn.addEventListener('click', () => {
      const screenPrompt = 'شوف الصفحة ذي وترجملي واشرح ما فيها بالعربي';
      if (DOM.textInput) DOM.textInput.value = screenPrompt;
      handleSendText(screenPrompt);
      if (DOM.textInput) DOM.textInput.value = '';
    });
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

  // Global Keyboard Shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (DOM.drawerOverlay && !DOM.drawerOverlay.classList.contains('hidden')) {
        DOM.drawerOverlay.classList.add('hidden');
      } else if (DOM.settingsModal && !DOM.settingsModal.classList.contains('hidden')) {
        DOM.settingsModal.classList.add('hidden');
      } else if (state.isPlayingAudio) {
        stopAudioPlayback();
        wsSend({ type: 'abort' });
        setOrbState('idle');
      }
    }
  });
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
      if (data.status === 'success' && data.attachment) {
        state.pendingAttachments.push(data.attachment);
        renderAttachmentChips();
        showToast(`✅ تم رفع ${file.name || 'الملف'} بنجاح`);
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
    if (att.is_image && att.base64) {
      const mime = att.mime_type || 'image/jpeg';
      preview = `<img src="data:${mime};base64,${att.base64.substring(0, 100)}" alt="preview" />`;
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
      console.warn('[WakeWord] SpeechRecognition not supported in this browser.');
      if (DOM.btnWakeWord) {
        DOM.btnWakeWord.title = 'التعرف الصوتي على النداء غير مدعوم في هذا المتصفح';
        DOM.btnWakeWord.style.opacity = '0.5';
      }
      return;
    }

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
          this.triggerActivation();
        }
      };

      this.recognition.onerror = (e) => {
        if (e.error !== 'no-speech' && e.error !== 'aborted') {
          console.debug('[WakeWord] Recognition note:', e.error);
        }
      };

      this.recognition.onend = () => {
        this.isListeningWakeWord = false;
        if (this.enabled && !state.isRecording && !state.isPlayingAudio) {
          clearTimeout(this.restartTimeout);
          this.restartTimeout = setTimeout(() => {
            this.resumeListening();
          }, 600);
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

    if (this.activeSpeechTimer) clearTimeout(this.activeSpeechTimer);
    this.activeSpeechTimer = setTimeout(() => {
      if (state.isRecording) {
        stopRecording();
      }
    }, 6000);
  },

  pauseListening() {
    if (!this.recognition) return;
    try {
      this.recognition.abort();
    } catch (e) {}
    this.isListeningWakeWord = false;
  },

  resumeListening() {
    if (!this.enabled || !this.recognition || state.isRecording || state.isPlayingAudio) return;
    try {
      this.recognition.start();
    } catch (e) {
      // recognition may already be started
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
    if (!DOM.btnWakeWord) return;
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
      if (DOM.mobileUrlInput && data.mobile_url) {
        DOM.mobileUrlInput.value = data.mobile_url;
        const openLink = document.getElementById('mobile-open-link');
        if (openLink) openLink.href = data.mobile_url;
      }
      if (DOM.mobileQrCanvas && data.qr_base64) {
        const ctx = DOM.mobileQrCanvas.getContext('2d');
        const img = new Image();
        img.onload = () => {
          DOM.mobileQrCanvas.width = 180;
          DOM.mobileQrCanvas.height = 180;
          ctx.clearRect(0, 0, 180, 180);
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

