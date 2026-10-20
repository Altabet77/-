
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const scoreEl = document.getElementById('score');

    let player = { x: 280, y: 340, width: 40, height: 24, speed: 6, color: '#00ffcc' };
    let bullets = [];
    let enemies = [];
    let stars = [];
    let score = 0;
    let keys = {};
    let gameOver = false;

    for (let i = 0; i < 80; i++) {
        stars.push({ x: Math.random() * 600, y: Math.random() * 400, size: Math.random() * 2, speed: Math.random() * 1.5 + 0.5 });
    }

    function spawnEnemy() {
        if (gameOver) return;
        enemies.push({
            x: Math.random() * 550,
            y: -30,
            width: 32,
            height: 24,
            speed: Math.random() * 2 + 1.5,
            color: '#ff0055'
        });
        setTimeout(spawnEnemy, Math.random() * 1000 + 800);
    }
    spawnEnemy();

    window.addEventListener('keydown', e => {
        keys[e.code] = true;
        if (e.code === 'Space' && !gameOver) {
            bullets.push({ x: player.x + player.width / 2 - 2, y: player.y, width: 4, height: 10, speed: 8 });
            e.preventDefault();
        }
    });
    window.addEventListener('keyup', e => { keys[e.code] = false; });

    function update() {
        if (gameOver) return;
        if (keys['ArrowLeft'] && player.x > 0) player.x -= player.speed;
        if (keys['ArrowRight'] && player.x + player.width < 600) player.x += player.speed;

        stars.forEach(s => {
            s.y += s.speed;
            if (s.y > 400) s.y = 0;
        });

        bullets.forEach((b, i) => {
            b.y -= b.speed;
            if (b.y < -10) bullets.splice(i, 1);
        });

        enemies.forEach((e, ei) => {
            e.y += e.speed;
            if (e.y > 400) enemies.splice(ei, 1);

            bullets.forEach((b, bi) => {
                if (b.x < e.x + e.width && b.x + b.width > e.x && b.y < e.y + e.height && b.y + b.height > e.y) {
                    enemies.splice(ei, 1);
                    bullets.splice(bi, 1);
                    score += 10;
                    scoreEl.textContent = score;
                }
            });

            if (player.x < e.x + e.width && player.x + player.width > e.x && player.y < e.y + e.height && player.y + player.height > e.y) {
                gameOver = true;
            }
        });
    }

    function draw() {
        ctx.fillStyle = '#02050c';
        ctx.fillRect(0, 0, 600, 400);

        ctx.fillStyle = '#ffffff';
        stars.forEach(s => { ctx.fillRect(s.x, s.y, s.size, s.size); });

        ctx.fillStyle = player.color;
        ctx.beginPath();
        ctx.moveTo(player.x + player.width / 2, player.y);
        ctx.lineTo(player.x, player.y + player.height);
        ctx.lineTo(player.x + player.width, player.y + player.height);
        ctx.fill();

        ctx.fillStyle = '#39ff14';
        bullets.forEach(b => { ctx.fillRect(b.x, b.y, b.width, b.height); });

        enemies.forEach(e => {
            ctx.fillStyle = e.color;
            ctx.fillRect(e.x, e.y, e.width, e.height);
        });

        if (gameOver) {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
            ctx.fillRect(0, 0, 600, 400);
            ctx.fillStyle = '#ff0055';
            ctx.font = 'bold 28px Tajawal, sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('انتهت اللعبة! نقاطك: ' + score, 300, 190);
            ctx.fillStyle = '#00ffcc';
            ctx.font = '16px Tajawal, sans-serif';
            ctx.fillText('اضغط F5 لإعادة اللعب', 300, 230);
        }
    }

    function loop() {
        update();
        draw();
        requestAnimationFrame(loop);
    }
    loop();
    