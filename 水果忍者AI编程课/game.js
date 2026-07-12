// ============================================================
//  水果忍者 · 教师演示版（适合小学高年级 AI 编程课）— 手势版
//  说明：代码用"大白话 + 中文注释"写成，方便学生读懂和改。
//  切割方式：① 摄像头识别手势（伸手用食指划过水果）② 鼠标/手指滑动（备用）
//  学生最常用的三个可调旋钮：GRAVITY（重力）、SPAWN_INTERVAL（出怪速度）、
//  BOMB_CHANCE（炸弹概率）。改一个数字，游戏手感就变了！
// ============================================================

// ---------- 1. 找到画布并准备好画笔 ----------
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const videoEl = document.getElementById("cam");   // 摄像头画面（画成游戏背景）
const modeTip = document.getElementById("modeTip"); // 顶部"手势模式"提示

// 让画布大小跟着窗口走（手机、电脑都铺满）
function resize() {
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
}
window.addEventListener("resize", resize);
resize();

// ---------- 2. 游戏里的"全局变量"（记着游戏现在的状态）----------
let fruits = [];    // 正在天上飞的水果
let particles = []; // 被切开后飞溅的果汁
let trail = [];     // "刀"的轨迹（一连串点）
let score = 0;      // 分数
let lives = 5;      // 剩余生命（调高，让游戏更耐玩）
let running = false;// 游戏是否在跑
let spawnTimer = 0; // 用于控制多久生成一个水果

// ---------- 摄像头相关状态 ----------
let cameraOn = false;   // 摄像头/手势是否已开启
let hands = null;       // MediaPipe 手势识别器
let tipPos = null;      // 当前食指指尖在屏幕上的位置（做过平滑，没有手时为 null）
let rawTip = null;      // 识别到的原始指尖（未平滑）
let lastTip = null;     // 上一帧指尖位置（用来连成"刀"的线段做切割，不依赖主循环）

// ---------- 3. 游戏"旋钮"：学生最爱改这里 ----------
const GRAVITY = 0.22;     // 重力：越大水果掉得越快（调小=掉得慢、更好切）
const SPAWN_INTERVAL = 55;// 每隔多少帧生成一个水果（越小越密）
const BOMB_CHANCE = 0.10; // 炸弹出现概率（0~1，0.10 = 10%）
const LAUNCH_SPEED = 18;  // 水果向上抛的初速度（越大飞得越高）
const HAND_SMOOTH = 0.5;  // 手势平滑强度（0~1，越大越稳但越"跟不上"）

// ---------- 4. 水果长什么样 ----------
const FRUIT_EMOJI = ["🍉", "🍎", "🍊", "🍋", "🍓", "🍇", "🥝"];
const BOMB = "💣";
const FRUIT_SIZE = 82;    // 水果画多大（字号，越大越好切）
const FRUIT_RADIUS = 52;  // 水果的"碰撞半径"（用来判断是否切到，配合大小一起调）

// ---------- 5. 生成一个水果（或炸弹）----------
function spawnFruit() {
  const isBomb = Math.random() < BOMB_CHANCE;
  const emoji = isBomb
    ? BOMB
    : FRUIT_EMOJI[Math.floor(Math.random() * FRUIT_EMOJI.length)];

  // 从屏幕底部往上抛
  const x = 80 + Math.random() * (canvas.width - 160);
  const y = canvas.height + 50;
  const vx = (Math.random() - 0.5) * 3.5;             // 左右飘一点
  const vy = -(LAUNCH_SPEED + Math.random() * 3);     // 向上速度（负号=往上，飞得更高）

  fruits.push({
    x, y, vx, vy,
    emoji, isBomb,
    rot: 0,                                  // 当前旋转角度
    vr: (Math.random() - 0.5) * 0.2,         // 旋转速度
    sliced: false,                           // 已经被切过了吗
  });
}

// ---------- 6. 切水果时飞溅的果汁粒子 ----------
const PARTICLE_COLORS = ["#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#ff8cc8"];
function spawnParticles(x, y) {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
  for (let i = 0; i < 14; i++) {
    particles.push({
      x, y,
      vx: (Math.random() - 0.5) * 9,
      vy: (Math.random() - 0.5) * 9,
      life: 1,        // 1=最亮，0=消失
      color,
    });
  }
}

// ---------- 7. 判断"刀"有没有切到水果 ----------
// 数学小知识：算"水果圆心"到"刀这一小段线"的距离，小于半径就算切到
function pointToSegmentDist(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  let t = len2 ? ((px - x1) * dx + (py - y1) * dy) / len2 : 0;
  t = Math.max(0, Math.min(1, t)); // 夹在 0~1 之间
  const cx = x1 + t * dx;
  const cy = y1 + t * dy;
  return Math.hypot(px - cx, py - cy);
}

// 用"一段线"(x1,y1)->(x2,y2) 去检测有没有切到水果。鼠标和手势都调用它。
function sliceSegment(x1, y1, x2, y2) {
  for (const f of fruits) {
    if (f.sliced) continue;
    const d = pointToSegmentDist(f.x, f.y, x1, y1, x2, y2);
    if (d < FRUIT_RADIUS) {
      f.sliced = true;
      if (f.isBomb) {
        gameOver();   // 切到炸弹 → 直接结束
        return;
      }
      score += 1;
      spawnParticles(f.x, f.y);
      updateHud();
    }
  }
}

// 鼠标模式：用"刀光轨迹"里最近的两个点连成的线来切
function checkSlice() {
  if (trail.length < 2) return;
  const p1 = trail[trail.length - 2];
  const p2 = trail[trail.length - 1];
  sliceSegment(p1.x, p1.y, p2.x, p2.y);
}

// ---------- 8. 主循环：每一帧都更新一次画面 ----------
function loop() {
  if (!running) return;

  // 清空上一帧
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 如果开了摄像头，就把摄像头画面当背景（左右镜像，像照镜子）
  if (cameraOn && videoEl.readyState >= 2) {
    const cw = canvas.width, ch = canvas.height;
    const vw = videoEl.videoWidth, vh = videoEl.videoHeight;
    const scale = Math.max(cw / vw, ch / vh); // 铺满不变形
    const dw = vw * scale, dh = vh * scale;
    ctx.save();
    ctx.translate(cw / 2, ch / 2);
    ctx.scale(-1, 1); // 镜像：你往右，画面里的手也往右
    ctx.drawImage(videoEl, -dw / 2, -dh / 2, dw, dh);
    ctx.restore();
  }

  // 定时生成水果
  spawnTimer++;
  if (spawnTimer >= SPAWN_INTERVAL) {
    spawnTimer = 0;
    spawnFruit();
    if (Math.random() < 0.35) spawnFruit(); // 偶尔一次来两个
  }

  // 更新 + 画水果
  for (let i = fruits.length - 1; i >= 0; i--) {
    const f = fruits[i];
    f.vy += GRAVITY;     // 重力让向上的速度慢慢变小、再往下掉
    f.x += f.vx;
    f.y += f.vy;
    f.rot += f.vr;

    // 画水果（带旋转）
    ctx.save();
    ctx.translate(f.x, f.y);
    ctx.rotate(f.rot);
    ctx.font = FRUIT_SIZE + "px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(f.emoji, 0, 0);
    ctx.restore();

    // 掉出屏幕底部了
    if (f.y > canvas.height + 60) {
      if (!f.isBomb && !f.sliced) {
        lives -= 1;       // 漏掉一个水果扣一条命
        updateHud();
        if (lives <= 0) { gameOver(); return; }
      }
      fruits.splice(i, 1);
    }
  }

  // 画 + 更新果汁粒子
  for (let i = particles.length - 1; i >= 0; i--) {
    const p = particles[i];
    p.x += p.vx;
    p.y += p.vy;
    p.vy += 0.2;
    p.life -= 0.03;
    if (p.life <= 0) { particles.splice(i, 1); continue; }
    ctx.globalAlpha = p.life;
    ctx.fillStyle = p.color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;
  }

  // 画刀光（把最近的点连成一条线）
  if (trail.length > 1) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (let i = 1; i < trail.length; i++) {
      ctx.strokeStyle = "rgba(255,255,255," + (i / trail.length) * 0.9 + ")";
      ctx.lineWidth = (i / trail.length) * 10;
      ctx.beginPath();
      ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
      ctx.lineTo(trail[i].x, trail[i].y);
      ctx.stroke();
    }
  }

  // 手势模式下，在食指指尖画一个发光的大圆点，让孩子清楚看到"刀尖"在哪
  if (cameraOn && tipPos) {
    // 外圈光晕
    ctx.beginPath();
    ctx.arc(tipPos.x, tipPos.y, 26, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,107,107,0.25)";
    ctx.fill();
    // 实心圆点
    ctx.beginPath();
    ctx.arc(tipPos.x, tipPos.y, 16, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.fill();
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#ff6b6b";
    ctx.stroke();
  }

  // 让旧刀光慢慢消失
  if (trail.length > 0) trail.shift();

  requestAnimationFrame(loop);
}

// ---------- 9. 输入：鼠标 / 手指 滑动（备用）----------
function addTrailPoint(x, y) {
  trail.push({ x, y });
  if (trail.length > 16) trail.shift();
  checkSlice();
}

canvas.addEventListener("pointerdown", (e) => {
  trail = [];
  addTrailPoint(e.clientX, e.clientY);
});
canvas.addEventListener("pointermove", (e) => {
  if (e.buttons || e.pointerType === "touch") addTrailPoint(e.clientX, e.clientY);
});
canvas.addEventListener("pointerup", () => { trail = []; });

// ---------- 10. 输入：摄像头手势识别 ----------
// 手势库（MediaPipe Hands）从网络加载，会定义全局的 Hands / Camera
async function enableCamera() {
  modeTip.textContent = "📷 正在打开摄像头并加载手势模型…（需联网，首次稍慢）";
  modeTip.classList.remove("hidden");
  try {
    // 1) 检查手势库有没有加载成功（断网会失败）
    if (typeof Hands === "undefined" || typeof Camera === "undefined") {
      throw new Error("手势识别库没加载（可能没联网）");
    }

    // 2) 准备手势识别器：只识别 1 只手，用更准的模型
    //    版本号锁死，避免 CDN "latest" 变动导致 Hands 加载失败、静默退回鼠标
    const MP_VERSION = "0.4.1675469240";
    hands = new Hands({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@${MP_VERSION}/${file}`,
    });
    hands.setOptions({
      maxNumHands: 1,
      modelComplexity: 1,       // 用更准的模型（识别更稳，稍慢一点点）
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    hands.onResults(onHandResults);

    // 3) 用 Camera 工具统一申请摄像头并不断喂帧给识别器（官方推荐写法，
    //    不自己再调 getUserMedia，避免重复占用摄像头导致"设备被占用"报错）
    const cam = new Camera(videoEl, {
      onFrame: async () => {
        try {
          await hands.send({ image: videoEl });
        } catch (e) {
          // 模型没下下来或被拦了，给个明确提示，而不是默默失败
          modeTip.textContent = "⚠️ 手势模型运行出错：" + e.message;
        }
      },
      width: 640,
      height: 480,
    });
    await cam.start(); // 这里会申请摄像头权限；被拒会抛错，进 catch

    // 4) 摄像头就绪，开始游戏
    cameraOn = true;
    startGame();
    modeTip.textContent = "📷 手势模式：伸手，用食指划过水果来切！";
  } catch (err) {
    // 任何一步失败（没权限 / 没联网 / 不是安全地址）→ 退回鼠标模式
    cameraOn = false;
    running = false;
    modeTip.classList.add("hidden");
    document.getElementById("overlay").classList.remove("hidden");
    alert("摄像头或手势模型打不开（" + err.message + "）。可先点'鼠标开始'玩～");
  }
}

// 每识别出一帧手，就在这里拿到关键点的位置
function onHandResults(results) {
  if (!running) return; // 游戏结束了就不用切了

  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
    // 画面里没有手：清空，避免"刀"卡在原地误切
    tipPos = null;
    rawTip = null;
    lastTip = null;
    trail = [];
    modeTip.textContent = "📷 没看到手，把手伸进画面里";
    return;
  }
  // 取"食指指尖"这个点（编号 8）。坐标是 0~1 的比例。
  const lm = results.multiHandLandmarks[0][8];
  // 转成画布上的像素坐标，并左右镜像（和背景画面一致）
  const x = (1 - lm.x) * canvas.width;
  const y = lm.y * canvas.height;

  // 平滑：把新位置和上一次位置做加权平均，减少手抖造成的乱跳
  if (!tipPos) {
    tipPos = { x, y };
  } else {
    tipPos = {
      x: tipPos.x * HAND_SMOOTH + x * (1 - HAND_SMOOTH),
      y: tipPos.y * HAND_SMOOTH + y * (1 - HAND_SMOOTH),
    };
  }
  rawTip = { x, y };

  // 把指尖送进"刀光"轨迹（只用于画出来好看）
  trail.push({ x: tipPos.x, y: tipPos.y });
  if (trail.length > 16) trail.shift();

  // 关键修复：直接用"上一帧指尖 → 这一帧指尖"这一段线去切水果，
  // 不再依赖主循环的 trail.shift()，这样无论摄像头快慢都能稳定切到。
  if (lastTip) sliceSegment(lastTip.x, lastTip.y, tipPos.x, tipPos.y);
  lastTip = { x: tipPos.x, y: tipPos.y };

  modeTip.textContent = "📷 看到手了！用食指划过水果来切～";
}

// ---------- 11. 分数 / 生命 显示 ----------
function updateHud() {
  document.getElementById("score").textContent = "分数：" + score;
  document.getElementById("lives").textContent = "❤️".repeat(Math.max(0, lives));
}

// ---------- 12. 开始 / 结束 ----------
function startGame() {
  fruits = [];
  particles = [];
  trail = [];
  score = 0;
  lives = 5;
  spawnTimer = 0;
  tipPos = null;   // 重开时清掉手势残留，避免用旧指尖位置误切
  lastTip = null;
  updateHud();
  document.getElementById("overlay").classList.add("hidden");
  document.getElementById("gameover").classList.add("hidden");
  if (!cameraOn) modeTip.classList.add("hidden");
  running = true;
  loop();
}

function gameOver() {
  running = false;
  document.getElementById("finalScore").textContent = "你切到了 " + score + " 个水果！";
  document.getElementById("gameover").classList.remove("hidden");
}

document.getElementById("startBtn").addEventListener("click", startGame);
document.getElementById("camBtn").addEventListener("click", enableCamera);
document.getElementById("restartBtn").addEventListener("click", startGame);

// 一开始就更新一次分数显示
updateHud();
