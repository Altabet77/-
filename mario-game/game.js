// Super Zack Bros - Complete 2D Platformer Engine
(function () {
  'use strict';

  // --- Game Canvas & Context ---
  const canvas = document.getElementById('gameCanvas');
  const ctx = canvas.getContext('2d');

  // Virtual Game Resolution
  const V_WIDTH = 800;
  const V_HEIGHT = 450;
  const GRAVITY = 0.65;

  // --- DOM HUD & Overlays ---
  const hudScore = document.getElementById('hud-score');
  const hudCoins = document.getElementById('hud-coins');
  const hudTime = document.getElementById('hud-time');
  const hudLives = document.getElementById('hud-lives');
  const hudWorld = document.getElementById('hud-world');

  const menuScreen = document.getElementById('menu-screen');
  const gameoverScreen = document.getElementById('gameover-screen');
  const winScreen = document.getElementById('win-screen');
  const pauseScreen = document.getElementById('pause-screen');

  const btnStart = document.getElementById('btn-start');
  const btnRestart = document.getElementById('btn-restart');
  const btnNextLevel = document.getElementById('btn-next-level');
  const btnResume = document.getElementById('btn-resume');
  const btnSound = document.getElementById('btn-sound');
  const btnCrt = document.getElementById('btn-crt');
  const btnFullscreen = document.getElementById('btn-fullscreen');
  const screenContainer = document.getElementById('screen-container');

  // --- Input State ---
  const keys = {
    left: false,
    right: false,
    up: false,
    down: false,
    jump: false,
    run: false,
    fire: false
  };

  // --- Game State Variables ---
  let gameState = 'MENU'; // 'MENU' | 'PLAYING' | 'PAUSED' | 'GAMEOVER' | 'WIN'
  let score = 0;
  let coins = 0;
  let lives = 3;
  let timeLeft = 400;
  let timeTimer = 0;
  let currentLevel = 1;
  let cameraX = 0;
  let levelLength = 3600;
  let animTick = 0;

  // Entities Containers
  let player = null;
  let blocks = [];
  let enemies = [];
  let items = [];
  let fireballs = [];
  let particles = [];
  let floatingTexts = [];
  let flagpole = null;
  let fireworks = [];

  // --- Sound Helper ---
  function getAudio() {
    return window.retroAudio;
  }

  // --- Particle Effects ---
  class Particle {
    constructor(x, y, vx, vy, color, size, life = 30, isGravity = true) {
      this.x = x;
      this.y = y;
      this.vx = vx;
      this.vy = vy;
      this.color = color;
      this.size = size;
      this.maxLife = life;
      this.life = life;
      this.isGravity = isGravity;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      if (this.isGravity) this.vy += 0.3;
      this.life--;
    }
    draw(c, camX) {
      const alpha = Math.max(this.life / this.maxLife, 0);
      c.save();
      c.globalAlpha = alpha;
      c.fillStyle = this.color;
      c.fillRect(Math.floor(this.x - camX), Math.floor(this.y), this.size, this.size);
      c.restore();
    }
  }

  // Floating Score Text (+100, +200, 1UP)
  class FloatingText {
    constructor(x, y, text, color = '#ffffff') {
      this.x = x;
      this.y = y;
      this.text = text;
      this.color = color;
      this.life = 40;
    }
    update() {
      this.y -= 1.2;
      this.life--;
    }
    draw(c, camX) {
      c.save();
      c.font = "12px 'Press Start 2P', monospace";
      c.fillStyle = this.color;
      c.shadowColor = '#000';
      c.shadowOffsetX = 2;
      c.shadowOffsetY = 2;
      c.fillText(this.text, Math.floor(this.x - camX), Math.floor(this.y));
      c.restore();
    }
  }

  function addScore(amount, x, y) {
    score += amount;
    hudScore.textContent = String(score).padStart(6, '0');
    if (x !== undefined && y !== undefined) {
      floatingTexts.push(new FloatingText(x, y, `+${amount}`));
    }
  }

  function addCoin(x, y) {
    coins++;
    if (coins >= 100) {
      coins = 0;
      lives++;
      hudLives.textContent = `❤️ x${lives}`;
      floatingTexts.push(new FloatingText(player.x, player.y - 20, '1-UP!', '#00ff88'));
      getAudio().playPowerupCollect();
    }
    hudCoins.textContent = String(coins).padStart(2, '0');
    addScore(200, x, y);
    getAudio().playCoin();

    // Sparkle particles
    if (x !== undefined) {
      for (let i = 0; i < 6; i++) {
        particles.push(new Particle(x + 10, y + 10, (Math.random() - 0.5) * 4, (Math.random() - 0.5) * 4, '#ffd700', 3, 20, false));
      }
    }
  }

  // --- Player Class ---
  class Player {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.width = 24;
      this.height = 36;
      this.vx = 0;
      this.vy = 0;
      this.speed = 4.2;
      this.runSpeed = 6.8;
      this.jumpPower = -12.8;

      this.isGrounded = false;
      this.isJumping = false;
      this.facingLeft = false;

      // Power states
      this.isSuper = false;
      this.isFire = false;
      this.isInvincible = false;
      this.invincibleTimer = 0;
      this.starTimer = 0;

      this.isDead = false;
      this.deathTimer = 0;
      this.flagSliding = false;
      this.fireCooldown = 0;
    }

    growSuper() {
      if (!this.isSuper) {
        this.isSuper = true;
        this.y -= 12;
        this.height = 48;
        this.width = 26;
        getAudio().playPowerupCollect();
        floatingTexts.push(new FloatingText(this.x, this.y, 'SUPER ZACK!', '#ffd700'));
      }
    }

    growFire() {
      this.growSuper();
      this.isFire = true;
      getAudio().playPowerupCollect();
      floatingTexts.push(new FloatingText(this.x, this.y, 'FIRE ZACK!', '#ff4400'));
    }

    giveStar() {
      this.isInvincible = true;
      this.starTimer = 600; // ~10 seconds
      getAudio().playPowerupCollect();
      getAudio().startBGM(true);
      floatingTexts.push(new FloatingText(this.x, this.y, 'STAR POWER!', '#00ffff'));
    }

    hit() {
      if (this.isInvincible || this.isDead || this.invincibleTimer > 0) return;

      if (this.isFire) {
        this.isFire = false;
        this.invincibleTimer = 90;
        getAudio().playBlockHit();
      } else if (this.isSuper) {
        this.isSuper = false;
        this.height = 36;
        this.width = 24;
        this.invincibleTimer = 90;
        getAudio().playBlockHit();
      } else {
        this.die();
      }
    }

    die() {
      if (this.isDead) return;
      this.isDead = true;
      this.deathTimer = 0;
      this.vy = -12;
      this.vx = 0;
      getAudio().playDie();
    }

    shootFireball() {
      if (!this.isFire || this.fireCooldown > 0 || this.isDead) return;
      this.fireCooldown = 15;
      const dir = this.facingLeft ? -1 : 1;
      const fbX = this.facingLeft ? this.x - 8 : this.x + this.width + 4;
      fireballs.push(new Fireball(fbX, this.y + 12, dir * 8, 2));
      getAudio().playFireball();
    }

    update() {
      if (this.isDead) {
        this.deathTimer++;
        this.vy += GRAVITY;
        this.y += this.vy;
        if (this.deathTimer > 120) {
          loseLife();
        }
        return;
      }

      if (this.flagSliding) {
        this.y += 2.5;
        return;
      }

      // Invincibility timers
      if (this.starTimer > 0) {
        this.starTimer--;
        if (this.starTimer === 0) {
          this.isInvincible = false;
          getAudio().startBGM(false);
        }
      }
      if (this.invincibleTimer > 0) {
        this.invincibleTimer--;
      }
      if (this.fireCooldown > 0) {
        this.fireCooldown--;
      }

      // Horizontal movement
      const maxSpd = (keys.run || keys.fire) ? this.runSpeed : this.speed;
      const accel = this.isGrounded ? 0.45 : 0.25;
      const friction = this.isGrounded ? 0.82 : 0.94;

      if (keys.left) {
        this.vx -= accel;
        this.facingLeft = true;
      } else if (keys.right) {
        this.vx += accel;
        this.facingLeft = false;
      } else {
        this.vx *= friction;
        if (Math.abs(this.vx) < 0.05) this.vx = 0;
      }

      // Clamp speed
      this.vx = Math.max(-maxSpd, Math.min(maxSpd, this.vx));

      // Dust when skidding
      if (this.isGrounded && Math.abs(this.vx) > 3 && ((keys.left && this.vx > 0) || (keys.right && this.vx < 0))) {
        particles.push(new Particle(this.x + this.width / 2, this.y + this.height - 2, (Math.random() - 0.5) * 2, -1, '#c2b280', 4, 12));
      }

      // Jumping (Variable jump height)
      if (keys.jump && this.isGrounded && !this.isJumping) {
        this.vy = this.jumpPower;
        this.isGrounded = false;
        this.isJumping = true;
        getAudio().playJump(this.isSuper);

        // Jump dust
        for (let i = 0; i < 4; i++) {
          particles.push(new Particle(this.x + this.width / 2, this.y + this.height, (Math.random() - 0.5) * 3, -1, '#ddd', 3, 14));
        }
      }

      // Cut jump short if releasing jump button
      if (!keys.jump && this.vy < -4) {
        this.vy *= 0.65;
      }

      // Fireball trigger
      if (keys.fire && this.isFire) {
        this.shootFireball();
      }

      // Apply Gravity
      this.vy += GRAVITY;
      if (this.vy > 14) this.vy = 14;

      // Move & Collide Horizontally
      this.x += this.vx;
      this.collideHorizontal();

      // Move & Collide Vertically
      this.y += this.vy;
      this.collideVertical();

      // Screen boundaries
      if (this.x < 0) {
        this.x = 0;
        this.vx = 0;
      }

      // Bottomless Pit Death
      if (this.y > V_HEIGHT + 60) {
        this.die();
      }

      // Flagpole check
      if (flagpole && this.x + this.width >= flagpole.x && this.x <= flagpole.x + 20 && !this.flagSliding) {
        triggerVictory();
      }
    }

    collideHorizontal() {
      for (const block of blocks) {
        if (!block.solid) continue;
        if (this.intersects(block)) {
          if (this.vx > 0) {
            this.x = block.x - this.width;
          } else if (this.vx < 0) {
            this.x = block.x + block.width;
          }
          this.vx = 0;
        }
      }
    }

    collideVertical() {
      this.isGrounded = false;
      for (const block of blocks) {
        if (!block.solid) continue;
        if (this.intersects(block)) {
          if (this.vy > 0) {
            // Landing on top of block
            this.y = block.y - this.height;
            this.vy = 0;
            this.isGrounded = true;
            this.isJumping = false;
          } else if (this.vy < 0) {
            // Hitting block from below
            this.y = block.y + block.height;
            this.vy = 0;
            block.hit(this);
          }
        }
      }
    }

    intersects(rect) {
      return (
        this.x < rect.x + rect.width &&
        this.x + this.width > rect.x &&
        this.y < rect.y + rect.height &&
        this.y + this.height > rect.y
      );
    }

    draw(c, camX) {
      if (this.isDead) {
        Sprites.drawPlayer(c, this.x - camX, this.y, this.width, this.height, {
          facingLeft: this.facingLeft,
          isJumping: true,
          isDead: true,
          isSuper: false
        });
        return;
      }

      // Blinking during damage immunity
      if (this.invincibleTimer > 0 && Math.floor(this.invincibleTimer / 4) % 2 === 0) {
        return;
      }

      Sprites.drawPlayer(c, this.x - camX, this.y, this.width, this.height, {
        facingLeft: this.facingLeft,
        isJumping: !this.isGrounded,
        isMoving: Math.abs(this.vx) > 0.4,
        animFrame: animTick,
        isSuper: this.isSuper,
        isFire: this.isFire,
        isInvincible: this.isInvincible
      });
    }
  }

  // --- Block Class (? blocks, Bricks, Pipes, Ground) ---
  class Block {
    constructor(x, y, type = 'ground', size = 32, itemInside = null) {
      this.x = x;
      this.y = y;
      this.initialY = y;
      this.width = size;
      this.height = size;
      this.type = type; // 'ground' | 'brick' | 'question' | 'pipe' | 'pipe-body' | 'hard'
      this.itemInside = itemInside; // null | 'coin' | 'mushroom' | 'flower' | 'star'
      this.isHit = false;
      this.bounceTimer = 0;
      this.solid = true;
      this.destroyed = false;
    }

    hit(p) {
      if (this.isHit || this.destroyed) {
        getAudio().playBlockHit();
        return;
      }

      if (this.type === 'question') {
        this.isHit = true;
        this.bounceTimer = 8;
        getAudio().playBlockHit();

        // Spawn content
        if (this.itemInside === 'coin' || !this.itemInside) {
          addCoin(this.x, this.y - 32);
          items.push(new BouncingCoin(this.x + 6, this.y - 20));
        } else if (this.itemInside === 'mushroom') {
          getAudio().playPowerupSpawns();
          items.push(new PowerupItem(this.x, this.y - 32, 'mushroom'));
        } else if (this.itemInside === 'flower') {
          getAudio().playPowerupSpawns();
          items.push(new PowerupItem(this.x, this.y - 32, 'flower'));
        } else if (this.itemInside === 'star') {
          getAudio().playPowerupSpawns();
          items.push(new PowerupItem(this.x, this.y - 32, 'star'));
        }
      } else if (this.type === 'brick') {
        if (p.isSuper || p.isFire) {
          // Break brick!
          this.destroyed = true;
          this.solid = false;
          getAudio().playBrickBreak();
          addScore(50, this.x, this.y);

          // Brick debris particles
          const debrisColors = ['#b84418', '#ff7744', '#8a2b0a'];
          for (let i = 0; i < 4; i++) {
            const vx = (i % 2 === 0 ? -1 : 1) * (2 + Math.random() * 2);
            const vy = -6 - Math.random() * 4;
            particles.push(new Particle(this.x + 12, this.y + 12, vx, vy, debrisColors[i % 3], 8, 45));
          }
        } else {
          // Small Zack bounce brick
          this.bounceTimer = 6;
          getAudio().playBlockHit();
        }
      }
    }

    update() {
      if (this.bounceTimer > 0) {
        this.bounceTimer--;
        this.y = this.initialY - Math.sin((8 - this.bounceTimer) / 8 * Math.PI) * 6;
      } else {
        this.y = this.initialY;
      }
    }

    draw(c, camX) {
      if (this.destroyed) return;
      const drawX = Math.floor(this.x - camX);
      const drawY = Math.floor(this.y);

      if (this.type === 'ground') {
        c.fillStyle = '#b84418';
        c.fillRect(drawX, drawY, this.width, this.height);
        c.fillStyle = '#00bb44'; // Grass top
        c.fillRect(drawX, drawY, this.width, 6);
      } else if (this.type === 'brick') {
        Sprites.drawBrickBlock(c, drawX, drawY, this.width);
      } else if (this.type === 'question') {
        Sprites.drawQuestionBlock(c, drawX, drawY, this.width, this.isHit, animTick);
      } else if (this.type === 'hard') {
        c.fillStyle = '#6b7280';
        c.fillRect(drawX, drawY, this.width, this.height);
        c.fillStyle = '#374151';
        c.fillRect(drawX + 2, drawY + 2, this.width - 4, this.height - 4);
      } else if (this.type === 'pipe') {
        Sprites.drawPipe(c, drawX, drawY, this.width, this.height);
      }
    }
  }

  // --- Collectible Items (Mushroom, Flower, Star, Coins) ---
  class PowerupItem {
    constructor(x, y, type) {
      this.x = x;
      this.y = y;
      this.type = type; // 'mushroom' | 'flower' | 'star'
      this.width = 24;
      this.height = 24;
      this.vx = type === 'flower' ? 0 : 2;
      this.vy = -3;
      this.isGrounded = false;
      this.destroyed = false;
    }

    update() {
      if (this.destroyed) return;

      if (this.type === 'flower') {
        // Stationary powerup
        if (this.intersects(player)) {
          player.growFire();
          this.destroyed = true;
          addScore(1000, this.x, this.y);
        }
        return;
      }

      // Mushroom / Star Physics
      this.vy += GRAVITY * 0.8;
      if (this.vy > 8) this.vy = 8;

      this.x += this.vx;
      // Collide Horizontal with solid blocks
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vx > 0) {
            this.x = block.x - this.width;
            this.vx = -this.vx;
          } else if (this.vx < 0) {
            this.x = block.x + block.width;
            this.vx = -this.vx;
          }
        }
      }

      this.y += this.vy;
      // Collide Vertical
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vy > 0) {
            this.y = block.y - this.height;
            this.vy = this.type === 'star' ? -7.5 : 0; // Star bounces!
            this.isGrounded = true;
          }
        }
      }

      // Collect by player
      if (this.intersects(player)) {
        if (this.type === 'mushroom') {
          player.growSuper();
          addScore(1000, this.x, this.y);
        } else if (this.type === 'star') {
          player.giveStar();
          addScore(1000, this.x, this.y);
        }
        this.destroyed = true;
      }
    }

    intersects(r) {
      return (
        this.x < r.x + r.width &&
        this.x + this.width > r.x &&
        this.y < r.y + r.height &&
        this.y + this.height > r.y
      );
    }

    draw(c, camX) {
      if (this.destroyed) return;
      const dx = Math.floor(this.x - camX);
      const dy = Math.floor(this.y);

      if (this.type === 'mushroom') {
        Sprites.drawMushroom(c, dx, dy, this.width);
      } else if (this.type === 'flower') {
        Sprites.drawFireFlower(c, dx, dy, this.width, animTick);
      } else if (this.type === 'star') {
        Sprites.drawStar(c, dx, dy, this.width, animTick);
      }
    }
  }

  // Bouncing Coin from ? Block
  class BouncingCoin {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.vy = -7.5;
      this.life = 25;
    }
    update() {
      this.y += this.vy;
      this.vy += 0.5;
      this.life--;
    }
    draw(c, camX) {
      if (this.life <= 0) return;
      Sprites.drawCoin(c, this.x - camX, this.y, 20, 20, animTick);
    }
  }

  // Floating Coin in level
  class FloatingCoin {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.width = 20;
      this.height = 20;
      this.destroyed = false;
    }
    update() {
      if (this.destroyed) return;
      if (
        player.x < this.x + this.width &&
        player.x + player.width > this.x &&
        player.y < this.y + this.height &&
        player.y + player.height > this.y
      ) {
        this.destroyed = true;
        addCoin(this.x, this.y);
      }
    }
    draw(c, camX) {
      if (this.destroyed) return;
      Sprites.drawCoin(c, this.x - camX, this.y, this.width, this.height, animTick);
    }
  }

  // --- Fireball Projectile ---
  class Fireball {
    constructor(x, y, vx, vy) {
      this.x = x;
      this.y = y;
      this.vx = vx;
      this.vy = vy;
      this.size = 12;
      this.destroyed = false;
      this.life = 120;
    }

    update() {
      if (this.destroyed) return;
      this.life--;
      if (this.life <= 0) {
        this.destroyed = true;
        return;
      }

      this.vy += GRAVITY * 0.7;
      this.x += this.vx;

      // Block collision
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (
          this.x < block.x + block.width &&
          this.x + this.size > block.x &&
          this.y < block.y + block.height &&
          this.y + this.size > block.y
        ) {
          // Explode on wall
          this.destroyed = true;
          this.explode();
          return;
        }
      }

      this.y += this.vy;
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (
          this.x < block.x + block.width &&
          this.x + this.size > block.x &&
          this.y < block.y + block.height &&
          this.y + this.size > block.y
        ) {
          // Bounce off floor
          this.y = block.y - this.size;
          this.vy = -6;
        }
      }

      // Check hit enemies
      for (const enemy of enemies) {
        if (enemy.isDead) continue;
        if (
          this.x < enemy.x + enemy.width &&
          this.x + this.size > enemy.x &&
          this.y < enemy.y + enemy.height &&
          this.y + this.size > enemy.y
        ) {
          this.destroyed = true;
          this.explode();
          enemy.dieFromProjectile();
          addScore(200, enemy.x, enemy.y);
          break;
        }
      }
    }

    explode() {
      for (let i = 0; i < 6; i++) {
        particles.push(new Particle(this.x, this.y, (Math.random() - 0.5) * 4, (Math.random() - 0.5) * 4, '#ffaa00', 4, 15, false));
      }
    }

    draw(c, camX) {
      if (this.destroyed) return;
      Sprites.drawFireball(c, this.x - camX, this.y, this.size, animTick);
    }
  }

  // --- Enemy Classes (Goomba, Koopa) ---
  class Goomba {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.width = 28;
      this.height = 28;
      this.vx = -1.2;
      this.vy = 0;
      this.isDead = false;
      this.isSquished = false;
      this.squishTimer = 0;
      this.destroyed = false;
    }

    update() {
      if (this.destroyed) return;
      if (this.isSquished) {
        this.squishTimer++;
        if (this.squishTimer > 25) this.destroyed = true;
        return;
      }
      if (this.isDead) {
        this.vy += GRAVITY;
        this.y += this.vy;
        if (this.y > V_HEIGHT + 50) this.destroyed = true;
        return;
      }

      // Gravity & Move
      this.vy += GRAVITY;
      if (this.vy > 10) this.vy = 10;

      this.x += this.vx;
      // Wall collision
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vx > 0) {
            this.x = block.x - this.width;
            this.vx = -this.vx;
          } else if (this.vx < 0) {
            this.x = block.x + block.width;
            this.vx = -this.vx;
          }
        }
      }

      this.y += this.vy;
      // Floor collision
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vy > 0) {
            this.y = block.y - this.height;
            this.vy = 0;
          }
        }
      }

      // Check player interaction
      if (!player.isDead && this.intersects(player)) {
        if (player.isInvincible) {
          this.dieFromProjectile();
          addScore(200, this.x, this.y);
        } else if (player.vy > 0 && player.y + player.height - player.vy <= this.y + 12) {
          // Player stomped on Goomba!
          this.squish();
          player.vy = keys.jump ? -12 : -7.5; // Big jump bounce if holding jump
          getAudio().playStomp();
          addScore(200, this.x, this.y);
        } else {
          player.hit();
        }
      }
    }

    squish() {
      this.isSquished = true;
      this.isDead = true;
    }

    dieFromProjectile() {
      this.isDead = true;
      this.vy = -8;
      getAudio().playStomp();
    }

    intersects(r) {
      return (
        this.x < r.x + r.width &&
        this.x + this.width > r.x &&
        this.y < r.y + r.height &&
        this.y + this.height > r.y
      );
    }

    draw(c, camX) {
      if (this.destroyed) return;
      Sprites.drawGoomba(c, this.x - camX, this.y, this.width, this.height, {
        isSquished: this.isSquished,
        animFrame: animTick
      });
    }
  }

  // Koopa Turtle
  class Koopa {
    constructor(x, y) {
      this.x = x;
      this.y = y;
      this.width = 28;
      this.height = 38;
      this.vx = -1.2;
      this.vy = 0;
      this.isShell = false;
      this.isSliding = false;
      this.isDead = false;
      this.destroyed = false;
    }

    update() {
      if (this.destroyed) return;
      if (this.isDead) {
        this.vy += GRAVITY;
        this.y += this.vy;
        if (this.y > V_HEIGHT + 50) this.destroyed = true;
        return;
      }

      this.vy += GRAVITY;
      if (this.vy > 10) this.vy = 10;

      this.x += this.vx;
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vx > 0) {
            this.x = block.x - this.width;
            this.vx = -this.vx;
            if (this.isSliding) getAudio().playBlockHit();
          } else if (this.vx < 0) {
            this.x = block.x + block.width;
            this.vx = -this.vx;
            if (this.isSliding) getAudio().playBlockHit();
          }
        }
      }

      this.y += this.vy;
      for (const block of blocks) {
        if (!block.solid || block.destroyed) continue;
        if (this.intersects(block)) {
          if (this.vy > 0) {
            this.y = block.y - this.height;
            this.vy = 0;
          }
        }
      }

      // Sliding shell kills other enemies
      if (this.isSliding) {
        for (const other of enemies) {
          if (other !== this && !other.isDead && this.intersects(other)) {
            other.dieFromProjectile();
            addScore(400, other.x, other.y);
          }
        }
      }

      // Interaction with Player
      if (!player.isDead && this.intersects(player)) {
        if (player.isInvincible) {
          this.dieFromProjectile();
          addScore(400, this.x, this.y);
        } else if (player.vy > 0 && player.y + player.height - player.vy <= this.y + 14) {
          // Stomp on Koopa
          getAudio().playStomp();
          player.vy = keys.jump ? -12 : -7.5;
          if (!this.isShell) {
            this.isShell = true;
            this.vx = 0;
            this.height = 28;
            addScore(200, this.x, this.y);
          } else if (!this.isSliding) {
            // Kick stationary shell
            this.isSliding = true;
            this.vx = player.x < this.x ? 8 : -8;
            addScore(400, this.x, this.y);
          } else {
            // Stop sliding shell
            this.isSliding = false;
            this.vx = 0;
          }
        } else {
          if (this.isShell && !this.isSliding) {
            // Kick shell from side
            this.isSliding = true;
            this.vx = player.x < this.x ? 8 : -8;
            getAudio().playStomp();
            addScore(400, this.x, this.y);
          } else {
            player.hit();
          }
        }
      }
    }

    dieFromProjectile() {
      this.isDead = true;
      this.vy = -8;
      getAudio().playStomp();
    }

    intersects(r) {
      return (
        this.x < r.x + r.width &&
        this.x + this.width > r.x &&
        this.y < r.y + r.height &&
        this.y + this.height > r.y
      );
    }

    draw(c, camX) {
      if (this.destroyed) return;
      Sprites.drawKoopa(c, this.x - camX, this.y, this.width, this.height, {
        isShell: this.isShell,
        facingLeft: this.vx < 0,
        animFrame: animTick
      });
    }
  }

  // --- Level Generator ---
  function buildLevel(lvlNum) {
    blocks = [];
    enemies = [];
    items = [];
    fireballs = [];
    particles = [];
    floatingTexts = [];
    fireworks = [];

    levelLength = 3800;
    const groundY = V_HEIGHT - 64;

    // Continuous Ground with Pits
    let curX = 0;
    const pits = [
      { start: 900, end: 1020 },
      { start: 1800, end: 1940 },
      { start: 2700, end: 2840 }
    ];

    while (curX < levelLength) {
      const inPit = pits.some(p => curX >= p.start && curX < p.end);
      if (!inPit) {
        blocks.push(new Block(curX, groundY, 'ground', 32));
        blocks.push(new Block(curX, groundY + 32, 'ground', 32));
      }
      curX += 32;
    }

    // Question Blocks & Bricks Configuration
    // Zone 1
    blocks.push(new Block(280, groundY - 100, 'question', 32, 'coin'));
    blocks.push(new Block(380, groundY - 100, 'brick', 32));
    blocks.push(new Block(412, groundY - 100, 'question', 32, 'mushroom'));
    blocks.push(new Block(444, groundY - 100, 'brick', 32));
    blocks.push(new Block(476, groundY - 100, 'question', 32, 'coin'));
    blocks.push(new Block(508, groundY - 100, 'brick', 32));
    blocks.push(new Block(444, groundY - 190, 'question', 32, 'star'));

    // Pipes
    blocks.push(new Block(620, groundY - 50, 'pipe', 50));
    blocks.push(new Block(780, groundY - 70, 'pipe', 50));

    // Enemies Zone 1
    enemies.push(new Goomba(340, groundY - 40));
    enemies.push(new Goomba(530, groundY - 40));
    enemies.push(new Koopa(700, groundY - 40));

    // Zone 2 (After Pit 1)
    blocks.push(new Block(1120, groundY - 100, 'brick', 32));
    blocks.push(new Block(1152, groundY - 100, 'question', 32, 'flower'));
    blocks.push(new Block(1184, groundY - 100, 'brick', 32));

    // Pyramid Stairs
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col <= row; col++) {
        blocks.push(new Block(1340 + row * 32, groundY - 32 - col * 32, 'hard', 32));
      }
    }
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col <= (3 - row); col++) {
        blocks.push(new Block(1500 + row * 32, groundY - 32 - col * 32, 'hard', 32));
      }
    }

    enemies.push(new Goomba(1220, groundY - 40));
    enemies.push(new Goomba(1270, groundY - 40));
    enemies.push(new Koopa(1440, groundY - 180));

    // High Platform with Coins
    for (let b = 0; b < 6; b++) {
      blocks.push(new Block(2050 + b * 32, groundY - 120, 'brick', 32));
      items.push(new FloatingCoin(2056 + b * 32, groundY - 160));
    }
    blocks.push(new Block(2146, groundY - 120, 'question', 32, 'star'));

    // Pipe in Zone 3
    blocks.push(new Block(2350, groundY - 80, 'pipe', 50));
    enemies.push(new Goomba(2100, groundY - 40));
    enemies.push(new Goomba(2160, groundY - 40));
    enemies.push(new Koopa(2450, groundY - 40));

    // Zone 4 - Final Castle Stairs & Flagpole
    for (let step = 0; step < 8; step++) {
      for (let h = 0; h <= step; h++) {
        blocks.push(new Block(3000 + step * 32, groundY - 32 - h * 32, 'hard', 32));
      }
    }

    // Flagpole
    flagpole = {
      x: 3380,
      y: groundY - 260,
      height: 260,
      flagProgress: 0
    };

    // Castle at level end
    const castleX = 3480;
    for (let row = 0; row < 4; row++) {
      for (let col = 0; col < 4; col++) {
        blocks.push(new Block(castleX + row * 32, groundY - 32 - col * 32, 'brick', 32));
      }
    }
  }

  // --- Background Scenery Drawing (Parallax) ---
  function drawBackground(c, camX) {
    // Sky gradient
    const skyGrad = c.createLinearGradient(0, 0, 0, V_HEIGHT);
    skyGrad.addColorStop(0, '#5c94fc');
    skyGrad.addColorStop(0.7, '#8fb5fe');
    skyGrad.addColorStop(1, '#c5dafe');
    c.fillStyle = skyGrad;
    c.fillRect(0, 0, V_WIDTH, V_HEIGHT);

    // Parallax Clouds (Slow)
    c.fillStyle = 'rgba(255, 255, 255, 0.85)';
    for (let i = 0; i < 15; i++) {
      const cloudX = (i * 320 - camX * 0.2) % (V_WIDTH + 400) - 100;
      const cloudY = 40 + (i % 3) * 35;
      drawCloud(c, cloudX, cloudY);
    }

    // Parallax Mountains (Medium)
    for (let i = 0; i < 8; i++) {
      const mX = (i * 540 - camX * 0.4) % (V_WIDTH + 600) - 200;
      const mY = V_HEIGHT - 64;
      drawMountain(c, mX, mY, 180, 120);
    }

    // Green Hills & Bushes (Faster)
    for (let i = 0; i < 12; i++) {
      const hX = (i * 360 - camX * 0.7) % (V_WIDTH + 500) - 150;
      const hY = V_HEIGHT - 64;
      drawBush(c, hX, hY, 80);
    }
  }

  function drawCloud(c, x, y) {
    c.beginPath();
    c.arc(x, y, 20, 0, Math.PI * 2);
    c.arc(x + 20, y - 8, 25, 0, Math.PI * 2);
    c.arc(x + 45, y, 20, 0, Math.PI * 2);
    c.fill();
  }

  function drawMountain(c, x, y, w, h) {
    c.fillStyle = '#00a859';
    c.beginPath();
    c.moveTo(x, y);
    c.lineTo(x + w / 2, y - h);
    c.lineTo(x + w, y);
    c.closePath();
    c.fill();
    // Mountain cap
    c.fillStyle = '#77d9a8';
    c.beginPath();
    c.moveTo(x + w / 2, y - h);
    c.lineTo(x + w / 2 - 20, y - h + 30);
    c.lineTo(x + w / 2 + 20, y - h + 30);
    c.closePath();
    c.fill();
  }

  function drawBush(c, x, y, size) {
    c.fillStyle = '#00bb44';
    c.beginPath();
    c.arc(x, y, size / 3, 0, Math.PI * 2);
    c.arc(x + size / 2, y - 4, size / 2.5, 0, Math.PI * 2);
    c.arc(x + size, y, size / 3, 0, Math.PI * 2);
    c.fill();
  }

  // --- Victory & Stage Clear Sequence ---
  function triggerVictory() {
    if (gameState === 'WIN') return;
    gameState = 'WIN';
    player.flagSliding = true;
    player.vx = 0;
    getAudio().playStageClear();

    // Time bonus score
    const timeBonus = timeLeft * 50;
    addScore(timeBonus + 5000);

    // Flag sliding down
    let fProgress = 0;
    const fInterval = setInterval(() => {
      fProgress += 0.04;
      if (flagpole) flagpole.flagProgress = Math.min(fProgress, 1);
      if (fProgress >= 1) {
        clearInterval(fInterval);
        // Show victory screen
        setTimeout(() => {
          document.getElementById('win-score').textContent = score;
          document.getElementById('win-time-bonus').textContent = `${timeLeft}s x 50 = +${timeBonus}`;
          winScreen.classList.remove('hidden');
        }, 1200);
      }
    }, 40);

    // Fireworks
    for (let f = 0; f < 8; f++) {
      setTimeout(() => {
        const fx = flagpole.x + (Math.random() - 0.5) * 300;
        const fy = 80 + Math.random() * 120;
        const colors = ['#ff0055', '#ffd700', '#00ff88', '#00d2ff', '#ffffff'];
        const col = colors[Math.floor(Math.random() * colors.length)];
        for (let p = 0; p < 24; p++) {
          const ang = (p / 24) * Math.PI * 2;
          const spd = 2 + Math.random() * 4;
          particles.push(new Particle(fx, fy, Math.cos(ang) * spd, Math.sin(ang) * spd, col, 4, 35, false));
        }
        getAudio().playPowerupCollect();
      }, f * 350);
    }
  }

  function loseLife() {
    lives--;
    hudLives.textContent = `❤️ x${lives}`;
    if (lives <= 0) {
      gameState = 'GAMEOVER';
      document.getElementById('go-score').textContent = score;
      document.getElementById('go-coins').textContent = coins;
      gameoverScreen.classList.remove('hidden');
    } else {
      // Restart current level
      startLevel(currentLevel);
    }
  }

  // --- Start / Reset Game ---
  function startLevel(lvl = 1) {
    currentLevel = lvl;
    timeLeft = 400;
    timeTimer = 0;
    cameraX = 0;

    hudWorld.textContent = `1-${lvl}`;
    hudScore.textContent = String(score).padStart(6, '0');
    hudCoins.textContent = String(coins).padStart(2, '0');
    hudLives.textContent = `❤️ x${lives}`;

    buildLevel(lvl);
    player = new Player(80, V_HEIGHT - 160);

    menuScreen.classList.add('hidden');
    gameoverScreen.classList.add('hidden');
    winScreen.classList.add('hidden');
    pauseScreen.classList.add('hidden');

    gameState = 'PLAYING';
    getAudio().startBGM(false);
  }

  function resetFullGame() {
    score = 0;
    coins = 0;
    lives = 3;
    startLevel(1);
  }

  // --- Main Game Loop ---
  function gameLoop() {
    animTick++;

    if (gameState === 'PLAYING' || gameState === 'WIN') {
      // Countdown Timer
      if (gameState === 'PLAYING') {
        timeTimer++;
        if (timeTimer >= 60) {
          timeTimer = 0;
          timeLeft--;
          hudTime.textContent = String(timeLeft).padStart(3, '0');
          if (timeLeft <= 0) {
            player.die();
          }
        }
      }

      // Update Player
      player.update();

      // Smooth Camera Tracking
      const targetCamX = player.x - V_WIDTH * 0.35;
      cameraX += (targetCamX - cameraX) * 0.1;
      cameraX = Math.max(0, Math.min(levelLength - V_WIDTH, cameraX));

      // Update Entities
      blocks.forEach(b => b.update());
      enemies.forEach(e => e.update());
      items.forEach(i => i.update());
      fireballs.forEach(f => f.update());
      particles.forEach(p => p.update());
      floatingTexts.forEach(t => t.update());

      // Filter out destroyed
      enemies = enemies.filter(e => !e.destroyed);
      items = items.filter(i => !i.destroyed);
      fireballs = fireballs.filter(f => !f.destroyed);
      particles = particles.filter(p => p.life > 0);
      floatingTexts = floatingTexts.filter(t => t.life > 0);
    }

    // --- Render Frame ---
    ctx.clearRect(0, 0, V_WIDTH, V_HEIGHT);

    // Draw Parallax Scenery
    drawBackground(ctx, cameraX);

    // Draw Flagpole
    if (flagpole) {
      Sprites.drawFlagpole(ctx, flagpole.x - cameraX, flagpole.y, flagpole.height, flagpole.flagProgress);
    }

    // Draw Blocks
    blocks.forEach(b => b.draw(ctx, cameraX));

    // Draw Items & Coins
    items.forEach(i => i.draw(ctx, cameraX));

    // Draw Enemies
    enemies.forEach(e => e.draw(ctx, cameraX));

    // Draw Fireballs
    fireballs.forEach(f => f.draw(ctx, cameraX));

    // Draw Player
    if (player) player.draw(ctx, cameraX);

    // Draw Particles
    particles.forEach(p => p.draw(ctx, cameraX));

    // Draw Floating Text
    floatingTexts.forEach(t => t.draw(ctx, cameraX));

    requestAnimationFrame(gameLoop);
  }

  // --- Keyboard & Touch Event Listeners ---
  function handleKeyDown(e) {
    getAudio().init();

    if (e.code === 'ArrowLeft' || e.code === 'KeyA') {
      keys.left = true;
    } else if (e.code === 'ArrowRight' || e.code === 'KeyD') {
      keys.right = true;
    } else if (e.code === 'ArrowUp' || e.code === 'KeyW' || e.code === 'Space') {
      keys.jump = true;
      e.preventDefault();
    } else if (e.code === 'ArrowDown' || e.code === 'KeyS') {
      keys.down = true;
    } else if (e.code === 'ShiftLeft' || e.code === 'ShiftRight' || e.code === 'KeyX' || e.code === 'KeyF') {
      keys.fire = true;
      keys.run = true;
    } else if (e.code === 'KeyP') {
      togglePause();
    } else if (e.code === 'KeyM') {
      toggleSoundBtn();
    }

    // Start game from menu with Space / Enter
    if (gameState === 'MENU' && (e.code === 'Space' || e.code === 'Enter')) {
      resetFullGame();
    }
  }

  function handleKeyUp(e) {
    if (e.code === 'ArrowLeft' || e.code === 'KeyA') keys.left = false;
    if (e.code === 'ArrowRight' || e.code === 'KeyD') keys.right = false;
    if (e.code === 'ArrowUp' || e.code === 'KeyW' || e.code === 'Space') keys.jump = false;
    if (e.code === 'ArrowDown' || e.code === 'KeyS') keys.down = false;
    if (e.code === 'ShiftLeft' || e.code === 'ShiftRight' || e.code === 'KeyX' || e.code === 'KeyF') {
      keys.fire = false;
      keys.run = false;
    }
  }

  function togglePause() {
    if (gameState === 'PLAYING') {
      gameState = 'PAUSED';
      getAudio().stopBGM();
      pauseScreen.classList.remove('hidden');
    } else if (gameState === 'PAUSED') {
      gameState = 'PLAYING';
      getAudio().startBGM(player.isInvincible);
      pauseScreen.classList.add('hidden');
    }
  }

  function toggleSoundBtn() {
    const on = getAudio().toggleSound();
    btnSound.textContent = on ? '🔊 صوت: تشغيل' : '🔇 صوت: كتم';
    btnSound.classList.toggle('active', on);
  }

  // Bind Buttons
  btnStart.addEventListener('click', () => {
    getAudio().init();
    resetFullGame();
  });

  btnRestart.addEventListener('click', () => {
    getAudio().init();
    resetFullGame();
  });

  btnNextLevel.addEventListener('click', () => {
    getAudio().init();
    startLevel(currentLevel + 1);
  });

  btnResume.addEventListener('click', togglePause);
  btnSound.addEventListener('click', () => {
    getAudio().init();
    toggleSoundBtn();
  });

  btnCrt.addEventListener('click', () => {
    screenContainer.classList.toggle('crt-active');
    btnCrt.classList.toggle('active');
  });

  btnFullscreen.addEventListener('click', () => {
    if (!document.fullscreenElement) {
      screenContainer.requestFullscreen().catch(() => {});
    } else {
      document.exitFullscreen().catch(() => {});
    }
  });

  // Touch / Mobile Controls Setup
  const touchBtns = document.querySelectorAll('.t-btn');
  touchBtns.forEach(btn => {
    const key = btn.dataset.key;
    const press = (e) => {
      e.preventDefault();
      getAudio().init();
      if (key === 'ArrowLeft') keys.left = true;
      if (key === 'ArrowRight') keys.right = true;
      if (key === 'ArrowDown') keys.down = true;
      if (key === 'Space') keys.jump = true;
      if (key === 'KeyX') { keys.fire = true; keys.run = true; }
    };
    const release = (e) => {
      e.preventDefault();
      if (key === 'ArrowLeft') keys.left = false;
      if (key === 'ArrowRight') keys.right = false;
      if (key === 'ArrowDown') keys.down = false;
      if (key === 'Space') keys.jump = false;
      if (key === 'KeyX') { keys.fire = false; keys.run = false; }
    };

    btn.addEventListener('touchstart', press, { passive: false });
    btn.addEventListener('touchend', release, { passive: false });
    btn.addEventListener('mousedown', press);
    btn.addEventListener('mouseup', release);
    btn.addEventListener('mouseleave', release);
  });

  window.addEventListener('keydown', handleKeyDown);
  window.addEventListener('keyup', handleKeyUp);

  // Initialize Canvas
  canvas.width = V_WIDTH;
  canvas.height = V_HEIGHT;

  // Start animation loop
  requestAnimationFrame(gameLoop);
})();
