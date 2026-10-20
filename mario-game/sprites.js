// Procedural Pixel-Art Sprite Renderer for Super Zack Bros
const Sprites = {
  // Draw Zack (Player)
  drawPlayer(ctx, x, y, width, height, state) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    // Flip horizontally if facing left
    if (state.facingLeft) {
      ctx.translate(width, 0);
      ctx.scale(-1, 1);
    }

    const isStar = state.isInvincible;
    const isSuper = state.isSuper || state.isFire;
    const isFire = state.isFire;
    const frame = state.animFrame || 0;

    // Star color cycle
    let mainColor = '#ff3344'; // default red
    let overallColor = '#2255cc'; // default blue overalls
    let capColor = '#ff3344';
    let skinColor = '#ffcca3';

    if (isFire) {
      mainColor = '#ffffff';
      overallColor = '#ff3344';
      capColor = '#ffffff';
    }

    if (isStar) {
      const starColors = ['#ff0055', '#ffaa00', '#00ff88', '#00d2ff', '#ff00ff', '#ffffff'];
      const c = starColors[Math.floor(Date.now() / 60) % starColors.length];
      mainColor = c;
      overallColor = '#ffffff';
      capColor = c;
    }

    const scale = isSuper ? 1.5 : 1.0;
    const drawHeight = 32 * scale;
    const drawWidth = 20 * scale;
    const yOffset = height - drawHeight;

    // Cap / Hair
    ctx.fillStyle = capColor;
    ctx.fillRect(4 * scale, yOffset + 0, 12 * scale, 6 * scale);
    ctx.fillRect(10 * scale, yOffset + 4 * scale, 8 * scale, 3 * scale); // cap visor

    // Face / Skin
    ctx.fillStyle = skinColor;
    ctx.fillRect(4 * scale, yOffset + 6 * scale, 10 * scale, 7 * scale);
    // Eye & Eyebrow
    ctx.fillStyle = '#111';
    ctx.fillRect(10 * scale, yOffset + 7 * scale, 2 * scale, 3 * scale);
    // Beard / Sideburn (Zack style!)
    ctx.fillStyle = '#5c3a21';
    ctx.fillRect(3 * scale, yOffset + 8 * scale, 3 * scale, 4 * scale);
    // Nose
    ctx.fillStyle = '#e0aa80';
    ctx.fillRect(12 * scale, yOffset + 8 * scale, 3 * scale, 3 * scale);

    // Shirt / Torso
    ctx.fillStyle = mainColor;
    ctx.fillRect(4 * scale, yOffset + 13 * scale, 12 * scale, 9 * scale);

    // Overalls
    ctx.fillStyle = overallColor;
    ctx.fillRect(5 * scale, yOffset + 16 * scale, 10 * scale, 8 * scale);
    // Yellow overall buttons
    ctx.fillStyle = '#ffd700';
    ctx.fillRect(6 * scale, yOffset + 17 * scale, 2 * scale, 2 * scale);
    ctx.fillRect(12 * scale, yOffset + 17 * scale, 2 * scale, 2 * scale);

    // Arms & Hands
    ctx.fillStyle = mainColor;
    if (state.isJumping) {
      ctx.fillRect(1 * scale, yOffset + 10 * scale, 4 * scale, 5 * scale); // arm up
    } else {
      ctx.fillRect(1 * scale, yOffset + 14 * scale, 4 * scale, 6 * scale);
    }
    // Hand
    ctx.fillStyle = '#ffffff'; // white gloves
    ctx.fillRect(0, yOffset + (state.isJumping ? 8 : 17) * scale, 4 * scale, 4 * scale);

    // Legs / Boots with running cycle
    ctx.fillStyle = '#5c3a21'; // brown boots
    if (state.isJumping) {
      // Jump pose
      ctx.fillStyle = overallColor;
      ctx.fillRect(3 * scale, yOffset + 24 * scale, 6 * scale, 4 * scale);
      ctx.fillRect(11 * scale, yOffset + 22 * scale, 6 * scale, 4 * scale);
      ctx.fillStyle = '#5c3a21';
      ctx.fillRect(2 * scale, yOffset + 28 * scale, 6 * scale, 4 * scale);
      ctx.fillRect(12 * scale, yOffset + 26 * scale, 6 * scale, 4 * scale);
    } else if (state.isMoving) {
      const legOffset = (Math.sin(frame * 0.4) * 4) * scale;
      ctx.fillStyle = overallColor;
      ctx.fillRect((4 + legOffset) * scale, yOffset + 24 * scale, 5 * scale, 4 * scale);
      ctx.fillRect((11 - legOffset) * scale, yOffset + 24 * scale, 5 * scale, 4 * scale);
      ctx.fillStyle = '#5c3a21';
      ctx.fillRect((3 + legOffset) * scale, yOffset + 28 * scale, 6 * scale, 4 * scale);
      ctx.fillRect((10 - legOffset) * scale, yOffset + 28 * scale, 6 * scale, 4 * scale);
    } else {
      // Standing pose
      ctx.fillStyle = overallColor;
      ctx.fillRect(4 * scale, yOffset + 24 * scale, 5 * scale, 4 * scale);
      ctx.fillRect(11 * scale, yOffset + 24 * scale, 5 * scale, 4 * scale);
      ctx.fillStyle = '#5c3a21';
      ctx.fillRect(3 * scale, yOffset + 28 * scale, 6 * scale, 4 * scale);
      ctx.fillRect(11 * scale, yOffset + 28 * scale, 6 * scale, 4 * scale);
    }

    ctx.restore();
  },

  // Draw Goomba Enemy
  drawGoomba(ctx, x, y, width, height, state) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    if (state.isSquished) {
      // Squished flat goomba
      ctx.fillStyle = '#8b4513';
      ctx.fillRect(2, height - 10, width - 4, 10);
      ctx.fillStyle = '#fff';
      ctx.fillRect(6, height - 8, 4, 4);
      ctx.fillRect(width - 10, height - 8, 4, 4);
      ctx.fillStyle = '#000';
      ctx.fillRect(8, height - 6, 2, 2);
      ctx.fillRect(width - 8, height - 6, 2, 2);
      ctx.restore();
      return;
    }

    const frame = state.animFrame || 0;
    const footWobble = Math.sin(frame * 0.3) > 0 ? 1 : -1;

    // Mushroom Head (Brown)
    ctx.fillStyle = '#a6522c';
    ctx.beginPath();
    ctx.arc(width / 2, height / 2 - 2, width / 2 - 2, Math.PI, 0, false);
    ctx.lineTo(width - 2, height - 10);
    ctx.lineTo(2, height - 10);
    ctx.closePath();
    ctx.fill();

    // Darker outline details
    ctx.fillStyle = '#6b3218';
    ctx.fillRect(4, height - 12, width - 8, 3);

    // Stem / Body
    ctx.fillStyle = '#fce4c8';
    ctx.fillRect(width / 2 - 6, height - 12, 12, 6);

    // Angry Eyes
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(5, height / 2 - 4, 5, 8);
    ctx.fillRect(width - 10, height / 2 - 4, 5, 8);
    // Pupils
    ctx.fillStyle = '#000000';
    ctx.fillRect(7, height / 2 - 1, 3, 5);
    ctx.fillRect(width - 10, height / 2 - 1, 3, 5);
    // Eyebrows (Angry)
    ctx.fillStyle = '#000';
    ctx.fillRect(4, height / 2 - 6, 6, 2);
    ctx.fillRect(width - 10, height / 2 - 6, 6, 2);

    // Feet
    ctx.fillStyle = '#3d2314';
    if (footWobble > 0) {
      ctx.fillRect(1, height - 6, 8, 6);
      ctx.fillRect(width - 8, height - 4, 7, 4);
    } else {
      ctx.fillRect(1, height - 4, 7, 4);
      ctx.fillRect(width - 9, height - 6, 8, 6);
    }

    ctx.restore();
  },

  // Draw Koopa Turtle
  drawKoopa(ctx, x, y, width, height, state) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    if (state.facingLeft) {
      ctx.translate(width, 0);
      ctx.scale(-1, 1);
    }

    if (state.isShell) {
      // Shell mode
      ctx.fillStyle = '#00bb44';
      ctx.beginPath();
      ctx.arc(width / 2, height / 2 + 4, width / 2 - 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(width / 2 - 6, height / 2 + 2, 12, 4);
      ctx.fillRect(width / 2 - 2, height / 2 - 2, 4, 12);
      ctx.restore();
      return;
    }

    const frame = state.animFrame || 0;
    // Green Shell
    ctx.fillStyle = '#00bb44';
    ctx.fillRect(4, 14, 16, 18);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(2, 28, 20, 4); // Shell white rim

    // Head
    ctx.fillStyle = '#ffcc00';
    ctx.fillRect(14, 2, 12, 12);
    ctx.fillRect(18, 10, 8, 4); // Beak
    // Eye
    ctx.fillStyle = '#000';
    ctx.fillRect(18, 5, 3, 4);

    // Feet waddle
    ctx.fillStyle = '#ffcc00';
    const leg = Math.sin(frame * 0.3) * 3;
    ctx.fillRect(4 + leg, 32, 6, 6);
    ctx.fillRect(14 - leg, 32, 6, 6);

    ctx.restore();
  },

  // Draw Question Block
  drawQuestionBlock(ctx, x, y, size, isHit, animFrame = 0) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    if (isHit) {
      // Empty brown block
      ctx.fillStyle = '#8b5a2b';
      ctx.fillRect(0, 0, size, size);
      ctx.fillStyle = '#5c3a1e';
      ctx.fillRect(2, 2, size - 4, size - 4);
      // Screws
      ctx.fillStyle = '#3a2010';
      ctx.fillRect(3, 3, 3, 3);
      ctx.fillRect(size - 6, 3, 3, 3);
      ctx.fillRect(3, size - 6, 3, 3);
      ctx.fillRect(size - 6, size - 6, 3, 3);
    } else {
      // Golden animated block
      const pulse = (Math.sin(animFrame * 0.1) + 1) * 0.5;
      ctx.fillStyle = '#e69500';
      ctx.fillRect(0, 0, size, size);

      ctx.fillStyle = pulse > 0.5 ? '#ffcc00' : '#ffb700';
      ctx.fillRect(2, 2, size - 4, size - 4);

      // Question Mark "?"
      ctx.fillStyle = '#5c3a1e';
      const cx = size / 2;
      const cy = size / 2;
      ctx.fillRect(cx - 5, cy - 8, 10, 3);
      ctx.fillRect(cx + 2, cy - 5, 3, 4);
      ctx.fillRect(cx - 2, cy - 2, 5, 3);
      ctx.fillRect(cx - 2, cy + 1, 4, 3);
      // Dot
      ctx.fillRect(cx - 2, cy + 6, 4, 3);

      // Corner rivets
      ctx.fillStyle = '#996600';
      ctx.fillRect(2, 2, 2, 2);
      ctx.fillRect(size - 4, 2, 2, 2);
      ctx.fillRect(2, size - 4, 2, 2);
      ctx.fillRect(size - 4, size - 4, 2, 2);
    }

    ctx.restore();
  },

  // Draw Brick Block
  drawBrickBlock(ctx, x, y, size) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    ctx.fillStyle = '#b84418';
    ctx.fillRect(0, 0, size, size);

    ctx.fillStyle = '#000000';
    // Horizontal mortar lines
    ctx.fillRect(0, size / 3, size, 2);
    ctx.fillRect(0, (size / 3) * 2, size, 2);
    // Vertical mortar lines
    ctx.fillRect(size / 2, 0, 2, size / 3);
    ctx.fillRect(size / 4, size / 3, 2, size / 3);
    ctx.fillRect((size / 4) * 3, size / 3, 2, size / 3);
    ctx.fillRect(size / 2, (size / 3) * 2, 2, size / 3);

    // Highlight
    ctx.fillStyle = '#ff7744';
    ctx.fillRect(1, 1, size / 2 - 2, 2);
    ctx.fillRect(size / 2 + 2, 1, size / 2 - 3, 2);

    ctx.restore();
  },

  // Draw Coin
  drawCoin(ctx, x, y, width, height, animFrame = 0) {
    ctx.save();
    ctx.translate(Math.floor(x + width / 2), Math.floor(y + height / 2));

    const scaleX = Math.abs(Math.sin(animFrame * 0.15));
    ctx.scale(Math.max(scaleX, 0.15), 1);

    ctx.fillStyle = '#ffd700';
    ctx.beginPath();
    ctx.arc(0, 0, width / 2, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ff9900';
    ctx.fillRect(-2, -height / 3, 4, (height / 3) * 2);

    ctx.restore();
  },

  // Draw Super Mushroom
  drawMushroom(ctx, x, y, size) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    // Cap (Red)
    ctx.fillStyle = '#ff2222';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 2, size / 2, Math.PI, 0, false);
    ctx.fill();

    // White Spots
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(size / 2 - 3, 3, 6, 6);
    ctx.fillRect(2, size / 2 - 6, 4, 6);
    ctx.fillRect(size - 6, size / 2 - 6, 4, 6);

    // Stem (Skin)
    ctx.fillStyle = '#ffe0cc';
    ctx.fillRect(size / 2 - 6, size / 2 - 2, 12, size / 2 + 2);

    // Eyes
    ctx.fillStyle = '#000000';
    ctx.fillRect(size / 2 - 4, size / 2 + 2, 2, 5);
    ctx.fillRect(size / 2 + 2, size / 2 + 2, 2, 5);

    ctx.restore();
  },

  // Draw Fire Flower
  drawFireFlower(ctx, x, y, size, animFrame = 0) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    const colors = ['#ff2222', '#ffaa00', '#ffffff'];
    const cIdx = Math.floor(animFrame * 0.2) % colors.length;

    // Petals
    ctx.fillStyle = colors[cIdx];
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 4, size / 2 - 2, 0, Math.PI * 2);
    ctx.fill();

    // Center
    ctx.fillStyle = '#ffd700';
    ctx.beginPath();
    ctx.arc(size / 2, size / 2 - 4, size / 4, 0, Math.PI * 2);
    ctx.fill();

    // Stem
    ctx.fillStyle = '#00cc44';
    ctx.fillRect(size / 2 - 2, size / 2 + 2, 4, size / 2 - 2);
    // Leaves
    ctx.fillRect(size / 2 - 8, size / 2 + 6, 6, 3);
    ctx.fillRect(size / 2 + 2, size / 2 + 6, 6, 3);

    ctx.restore();
  },

  // Draw Super Star
  drawStar(ctx, x, y, size, animFrame = 0) {
    ctx.save();
    ctx.translate(Math.floor(x + size / 2), Math.floor(y + size / 2));

    const colors = ['#ffd700', '#ffffff', '#ff9900'];
    ctx.fillStyle = colors[Math.floor(animFrame * 0.2) % colors.length];

    // Star shape
    ctx.beginPath();
    const spikes = 5;
    const outerRadius = size / 2;
    const innerRadius = size / 4;
    let rot = (Math.PI / 2) * 3;
    let step = Math.PI / spikes;

    ctx.moveTo(0, -outerRadius);
    for (let i = 0; i < spikes; i++) {
      ctx.lineTo(Math.cos(rot) * outerRadius, Math.sin(rot) * outerRadius);
      rot += step;
      ctx.lineTo(Math.cos(rot) * innerRadius, Math.sin(rot) * innerRadius);
      rot += step;
    }
    ctx.lineTo(0, -outerRadius);
    ctx.closePath();
    ctx.fill();

    // Eyes
    ctx.fillStyle = '#000';
    ctx.fillRect(-3, -2, 2, 4);
    ctx.fillRect(2, -2, 2, 4);

    ctx.restore();
  },

  // Draw Fireball
  drawFireball(ctx, x, y, size, animFrame = 0) {
    ctx.save();
    ctx.translate(Math.floor(x + size / 2), Math.floor(y + size / 2));
    ctx.rotate(animFrame * 0.4);

    ctx.fillStyle = '#ff2200';
    ctx.beginPath();
    ctx.arc(0, 0, size / 2, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = '#ffdd00';
    ctx.beginPath();
    ctx.arc(1, -1, size / 3, 0, Math.PI * 2);
    ctx.fill();

    ctx.restore();
  },

  // Draw Green Warp Pipe
  drawPipe(ctx, x, y, width, height) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    // Pipe Top Rim
    ctx.fillStyle = '#00a82d';
    ctx.fillRect(-2, 0, width + 4, 20);
    ctx.fillStyle = '#00dd44'; // Top highlight
    ctx.fillRect(2, 2, 6, 16);
    ctx.fillStyle = '#005511'; // Shadow
    ctx.fillRect(width - 6, 2, 6, 16);

    // Pipe Body
    ctx.fillStyle = '#00a82d';
    ctx.fillRect(2, 20, width - 4, height - 20);
    ctx.fillStyle = '#00dd44';
    ctx.fillRect(6, 20, 6, height - 20);
    ctx.fillStyle = '#005511';
    ctx.fillRect(width - 10, 20, 6, height - 20);

    ctx.restore();
  },

  // Draw Flagpole & Castle
  drawFlagpole(ctx, x, y, height, flagProgress = 0) {
    ctx.save();
    ctx.translate(Math.floor(x), Math.floor(y));

    // Golden ball top
    ctx.fillStyle = '#ffd700';
    ctx.beginPath();
    ctx.arc(4, 0, 8, 0, Math.PI * 2);
    ctx.fill();

    // Steel pole
    ctx.fillStyle = '#aaaaaa';
    ctx.fillRect(2, 8, 4, height - 8);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(3, 8, 2, height - 8);

    // Green base
    ctx.fillStyle = '#008800';
    ctx.fillRect(-6, height - 16, 20, 16);

    // Flag
    const flagY = 10 + (height - 40) * flagProgress;
    ctx.fillStyle = '#00cc44';
    ctx.beginPath();
    ctx.moveTo(6, flagY);
    ctx.lineTo(34, flagY + 12);
    ctx.lineTo(6, flagY + 24);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }
};
