// إعدادات اللعبة
const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const GRAVITY = 0.6;
let keys = {};

// كائن اللاعب (سونك)
class Player {
  constructor(){
    this.width = 40;
    this.height = 60;
    this.x = 100;
    this.y = canvas.height - this.height - 10;
    this.vy = 0;
    this.speed = 4;
    this.color = '#ff0000'; // سونك أحمر
    this.onGround = true;
  }
  draw(){
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.width, this.height);
  }
  update(){
    // حركة أفقية ثابتة (جري)
    this.x += this.speed;
    // قفز
    if(keys['ArrowUp'] && this.onGround){
      this.vy = -12;
      this.onGround = false;
    }
    // تطبيق الجاذبية
    this.vy += GRAVITY;
    this.y += this.vy;
    // الأرض
    if(this.y + this.height >= canvas.height - 10){
      this.y = canvas.height - this.height - 10;
      this.vy = 0;
      this.onGround = true;
    }
    // منع الخروج من الشاشة
    if(this.x > canvas.width) this.x = -this.width;
  }
}

// عوائق بسيطة
class Obstacle {
  constructor(x){
    this.width = 30;
    this.height = 50;
    this.x = x;
    this.y = canvas.height - this.height - 10;
    this.color = '#654321';
    this.speed = 4;
  }
  draw(){
    ctx.fillStyle = this.color;
    ctx.fillRect(this.x, this.y, this.width, this.height);
  }
  update(){
    this.x -= this.speed;
    if(this.x + this.width < 0){
      this.x = canvas.width + Math.random()*200;
    }
  }
}

const player = new Player();
const obstacles = [new Obstacle(600), new Obstacle(900), new Obstacle(1300)];
let score = 0;
let gameOver = false;

function loop(){
  if(gameOver) return;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  // خلفية ثابتة
  ctx.fillStyle = '#5c94fc';
  ctx.fillRect(0, canvas.height-10, canvas.width, 10);

  player.update();
  player.draw();

  obstacles.forEach(ob=>{ob.update(); ob.draw();});

  // كشف التصادم
  obstacles.forEach(ob=>{
    if(player.x < ob.x + ob.width && player.x + player.width > ob.x &&
       player.y < ob.y + ob.height && player.y + player.height > ob.y){
      gameOver = true;
      alert('انتهت اللعبة! نتيجتك: '+score);
    }
  });

  score++;
  ctx.fillStyle = '#000';
  ctx.font = '20px Arial';
  ctx.fillText('النقاط: '+score, 10,30);

  requestAnimationFrame(loop);
}

// التحكم بالمفاتيح
window.addEventListener('keydown',e=>{keys[e.key]=true;});
window.addEventListener('keyup',e=>{keys[e.key]=false;});

loop();