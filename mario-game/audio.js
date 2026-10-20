// 8-Bit Chiptune Web Audio Synthesizer for Super Zack Bros
class RetroAudio {
  constructor() {
    this.ctx = null;
    this.enabled = true;
    this.bgmPlaying = false;
    this.isStarMode = false;
    this.musicTimer = null;
    this.noteStep = 0;
  }

  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        this.ctx = new AudioContext();
      }
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  toggleSound() {
    this.enabled = !this.enabled;
    if (!this.enabled) {
      this.stopBGM();
    } else {
      this.startBGM();
    }
    return this.enabled;
  }

  // Play a simple custom square/triangle wave tone
  playTone(freq, type, duration, startVol = 0.2, endVol = 0.01) {
    if (!this.enabled || !this.ctx) return;
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
      gain.gain.setValueAtTime(startVol, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(Math.max(endVol, 0.0001), this.ctx.currentTime + duration);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start();
      osc.stop(this.ctx.currentTime + duration);
    } catch (e) {}
  }

  // Sound FX: Jump
  playJump(isSuper = false) {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'square';
    const startFreq = isSuper ? 180 : 140;
    const endFreq = isSuper ? 580 : 440;
    osc.frequency.setValueAtTime(startFreq, now);
    osc.frequency.exponentialRampToValueAtTime(endFreq, now + 0.18);
    gain.gain.setValueAtTime(0.15, now);
    gain.gain.linearRampToValueAtTime(0.01, now + 0.18);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.18);
  }

  // Sound FX: Coin Collect
  playCoin() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(987.77, now); // B5
    osc.frequency.setValueAtTime(1318.51, now + 0.08); // E6
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.35);
  }

  // Sound FX: Stomp Enemy
  playStomp() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(280, now);
    osc.frequency.exponentialRampToValueAtTime(60, now + 0.15);
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.15);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.15);
  }

  // Sound FX: Block Hit
  playBlockHit() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(160, now);
    osc.frequency.linearRampToValueAtTime(80, now + 0.1);
    gain.gain.setValueAtTime(0.3, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.1);
  }

  // Sound FX: Brick Break (Noise-like)
  playBrickBreak() {
    if (!this.enabled || !this.ctx) return;
    this.playTone(180, 'sawtooth', 0.12, 0.25, 0.01);
    setTimeout(() => this.playTone(120, 'square', 0.1, 0.2, 0.01), 40);
  }

  // Sound FX: Powerup Spawns
  playPowerupSpawns() {
    if (!this.enabled || !this.ctx) return;
    const notes = [330, 392, 659, 523, 587, 784];
    notes.forEach((freq, idx) => {
      setTimeout(() => {
        this.playTone(freq, 'square', 0.07, 0.12, 0.02);
      }, idx * 60);
    });
  }

  // Sound FX: Powerup Collect
  playPowerupCollect() {
    if (!this.enabled || !this.ctx) return;
    const notes = [330, 392, 659, 523, 587, 784, 880, 1046];
    notes.forEach((freq, idx) => {
      setTimeout(() => {
        this.playTone(freq, 'triangle', 0.09, 0.2, 0.01);
      }, idx * 45);
    });
  }

  // Sound FX: Fireball Shoot
  playFireball() {
    if (!this.enabled || !this.ctx) return;
    const now = this.ctx.currentTime;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = 'triangle';
    osc.frequency.setValueAtTime(750, now);
    osc.frequency.exponentialRampToValueAtTime(250, now + 0.1);
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(now + 0.1);
  }

  // Sound FX: Pipe Warp
  playPipeWarp() {
    if (!this.enabled || !this.ctx) return;
    const freqs = [300, 260, 220, 180, 150];
    freqs.forEach((f, i) => {
      setTimeout(() => this.playTone(f, 'sawtooth', 0.08, 0.2, 0.02), i * 60);
    });
  }

  // Sound FX: Player Die
  playDie() {
    this.stopBGM();
    if (!this.enabled || !this.ctx) return;
    const notes = [500, 420, 350, 300, 260, 220, 180, 130];
    notes.forEach((f, i) => {
      setTimeout(() => this.playTone(f, 'square', 0.1, 0.25, 0.02), i * 80);
    });
  }

  // Sound FX: Stage Clear Fanfare
  playStageClear() {
    this.stopBGM();
    if (!this.enabled || !this.ctx) return;
    const melody = [
      { f: 523.25, d: 120 }, { f: 659.25, d: 120 }, { f: 783.99, d: 120 },
      { f: 1046.50, d: 240 }, { f: 880.00, d: 120 }, { f: 1046.50, d: 400 }
    ];
    let time = 0;
    melody.forEach(item => {
      setTimeout(() => {
        this.playTone(item.f, 'triangle', item.d / 1000, 0.25, 0.01);
      }, time);
      time += item.d + 30;
    });
  }

  // Chiptune Music Sequencer (Retro Mario Theme Loop)
  startBGM(isStar = false) {
    if (!this.enabled || !this.ctx) return;
    this.stopBGM();
    this.bgmPlaying = true;
    this.isStarMode = isStar;
    this.noteStep = 0;

    const normalMelody = [
      659, 659, 0, 659, 0, 523, 659, 0, 784, 0, 0, 0, 392, 0, 0, 0,
      523, 0, 0, 392, 0, 0, 330, 0, 0, 440, 0, 493, 0, 466, 440, 0,
      392, 659, 784, 880, 0, 698, 784, 0, 659, 0, 523, 587, 493, 0
    ];

    const starMelody = [
      784, 784, 784, 659, 784, 784, 784, 659,
      880, 880, 880, 698, 880, 880, 880, 698,
      987, 987, 987, 784, 987, 987, 987, 784,
      1046, 1046, 1046, 880, 1046, 1046, 1046, 880
    ];

    const melody = isStar ? starMelody : normalMelody;
    const tempo = isStar ? 90 : 135; // ms per step

    this.musicTimer = setInterval(() => {
      if (!this.bgmPlaying || !this.enabled) return;
      const freq = melody[this.noteStep % melody.length];
      if (freq > 0) {
        // Lead melody channel
        this.playTone(freq, isStar ? 'sawtooth' : 'square', 0.08, isStar ? 0.12 : 0.08, 0.01);
        // Bass accompaniment
        if (this.noteStep % 4 === 0) {
          this.playTone(freq / 2, 'triangle', 0.12, 0.1, 0.01);
        }
      }
      this.noteStep++;
    }, tempo);
  }

  stopBGM() {
    this.bgmPlaying = false;
    if (this.musicTimer) {
      clearInterval(this.musicTimer);
      this.musicTimer = null;
    }
  }
}

window.retroAudio = new RetroAudio();
