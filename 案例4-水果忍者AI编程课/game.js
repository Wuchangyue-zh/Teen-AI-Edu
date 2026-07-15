// ============================================================
//  水果忍者 · 教师演示版（适合小学高年级 AI 编程课）— 手势版
//  说明：代码用"大白话 + 中文注释"写成，方便学生读懂和改。
//  切割方式：① 摄像头识别手势（伸手用食指划过水果）② 鼠标/手指滑动（备用）
//  学生最常用的可调旋钮：GRAVITY、SPAWN_INTERVAL、BOMB_CHANCE、COMBO_WINDOW
// ============================================================

// ---------- 1. 找到画布并准备好画笔 ----------
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
const videoEl = document.getElementById("cam");
const modeTip = document.getElementById("modeTip");

function resize() {
  canvas.width = canvas.clientWidth;
  canvas.height = canvas.clientHeight;
}
window.addEventListener("resize", resize);
resize();

// 把鼠标/触摸的屏幕坐标，转成画布里的坐标（重要！否则切不准）
function toCanvasPos(clientX, clientY) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (clientX - rect.left) * (canvas.width / rect.width),
    y: (clientY - rect.top) * (canvas.height / rect.height),
  };
}

// ---------- 2. 游戏里的"全局变量" ----------
const STARTING_LIVES = 5;      // 开局生命数（基础挑战可改）
let fruits = [];
let particles = [];
let halves = [];       // 被切开后飞出去的两半水果
let trail = [];
let score = 0;
let lives = STARTING_LIVES;
let running = false;
let paused = false;
let spawnTimer = 0;
let level = 1;
let combo = 0;
let bestCombo = 0;
let lastSliceTime = 0;
let flashAlpha = 0;    // 切中时屏幕闪一下
let shakeTime = 0;     // 切炸弹时屏幕抖一下
let popups = [];       // 飘字（+1、Combo x3 等）

// ---------- 摄像头相关状态 ----------
let cameraOn = false;
let hands = null;
let tipPos = null;       // 屏幕上显示的指尖（每帧平滑更新，更跟手）
let tipTarget = null;    // AI 识别到的目标位置（大约每秒 15~30 次）
let handBusy = false;    // 上一帧识别还没算完，就跳过，避免越积越慢

// ---------- 3. 游戏"旋钮"：学生最爱改这里 ----------
const GRAVITY = 0.22;
const SPAWN_INTERVAL = 55;
const BOMB_CHANCE = 0.10;
const LAUNCH_SPEED = 18;
const HAND_SMOOTH = 0.25;      // AI 结果平滑：越小越跟手，越大越稳但显慢
const HAND_LERP = 0.6;         // 每帧朝目标靠近多少：让圆点在两次识别之间也动起来
const HAND_MODEL = 0;          // 0=轻量快速（推荐） 1=更准但更吃电脑
const CAMERA_WIDTH = 480;      // 摄像头宽：越小识别越快（320~640）
const CAMERA_HEIGHT = 360;     // 摄像头高
const COMBO_WINDOW = 900;
const COMBO_BONUS = 1;         // 每多连一刀额外加几分
const LEVEL_UP_EVERY = 8;      // 每切几个水果升一级
const MAX_LEVEL = 10;

// 实际运行时用的值（会随等级慢慢变难）
let spawnInterval = SPAWN_INTERVAL;
let bombChance = BOMB_CHANCE;

// ---------- 4. 水果长什么样 ----------
const FRUIT_EMOJI = ["🍉", "🍎", "🍊", "🍋", "🍓", "🍇", "🥝"];
const BOMB = "💣";
const FRUIT_SIZE = 82;
const FRUIT_RADIUS = 52;

// ---------- 5. 音效（用浏览器自带声音，不用下载 mp3）----------
let audioCtx = null;
function ensureAudio() {
  if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (audioCtx.state === "suspended") audioCtx.resume();
}

function playTone(freq, duration, type = "sine", volume = 0.08) {
  try {
    ensureAudio();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = volume;
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) { /* 静音环境忽略 */ }
}

function playSliceSound(comboCount) {
  const base = 520 + Math.min(comboCount, 8) * 40;
  playTone(base, 0.08, "triangle", 0.07);
  playTone(base * 1.5, 0.05, "sine", 0.04);
}

function playMissSound() {
  playTone(180, 0.15, "sawtooth", 0.05);
}

function playBombSound() {
  playTone(90, 0.35, "square", 0.1);
  playTone(60, 0.4, "sawtooth", 0.08);
}

function playLevelUpSound() {
  playTone(440, 0.1, "sine", 0.06);
  playTone(660, 0.12, "sine", 0.06);
  playTone(880, 0.15, "sine", 0.06);
}

// ---------- 6. 本地最高分 ----------
function getHighScore() {
  return Number(localStorage.getItem("fruitNinjaHighScore") || 0);
}
function saveHighScore() {
  const old = getHighScore();
  if (score > old) localStorage.setItem("fruitNinjaHighScore", String(score));
}

// ---------- 7. 生成水果 ----------
function spawnFruit() {
  const isBomb = Math.random() < bombChance;
  const emoji = isBomb ? BOMB : FRUIT_EMOJI[Math.floor(Math.random() * FRUIT_EMOJI.length)];

  const x = 80 + Math.random() * (canvas.width - 160);
  const y = canvas.height + 50;
  const speedBoost = Math.min(level - 1, 5) * 0.6;
  const vx = (Math.random() - 0.5) * (3.5 + level * 0.15);
  const vy = -(LAUNCH_SPEED + Math.random() * 3 + speedBoost);

  fruits.push({
    x, y, vx, vy,
    emoji, isBomb,
    rot: 0,
    vr: (Math.random() - 0.5) * 0.2,
    sliced: false,
  });
}

// ---------- 8. 切水果特效 ----------
const PARTICLE_COLORS = ["#ff6b6b", "#ffa94d", "#ffd43b", "#69db7c", "#ff8cc8"];

function spawnParticles(x, y) {
  const color = PARTICLE_COLORS[Math.floor(Math.random() * PARTICLE_COLORS.length)];
  for (let i = 0; i < 14; i++) {
    particles.push({
      x, y,
      vx: (Math.random() - 0.5) * 9,
      vy: (Math.random() - 0.5) * 9,
      life: 1,
      color,
    });
  }
}

function spawnHalves(x, y, emoji, rot) {
  const halfEmoji = emoji + "✂️";
  for (let side = -1; side <= 1; side += 2) {
    halves.push({
      x, y,
      vx: side * (2 + Math.random() * 3),
      vy: -2 - Math.random() * 2,
      rot,
      vr: side * 0.15,
      emoji: halfEmoji,
      life: 1,
    });
  }
}

function addPopup(x, y, text, color = "#fff") {
  popups.push({ x, y, text, color, life: 1, vy: -1.2 });
}

// ---------- 9. 碰撞检测 ----------
function pointToSegmentDist(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len2 = dx * dx + dy * dy;
  let t = len2 ? ((px - x1) * dx + (py - y1) * dy) / len2 : 0;
  t = Math.max(0, Math.min(1, t));
  const cx = x1 + t * dx;
  const cy = y1 + t * dy;
  return Math.hypot(px - cx, py - cy);
}

function registerCombo() {
  const now = Date.now();
  if (now - lastSliceTime < COMBO_WINDOW) {
    combo += 1;
  } else {
    combo = 1;
  }
  lastSliceTime = now;
  if (combo > bestCombo) bestCombo = combo;
}

function updateDifficulty() {
  const newLevel = Math.min(MAX_LEVEL, 1 + Math.floor(score / LEVEL_UP_EVERY));
  if (newLevel > level) {
    level = newLevel;
    spawnInterval = Math.max(28, SPAWN_INTERVAL - (level - 1) * 3);
    bombChance = Math.min(0.22, BOMB_CHANCE + (level - 1) * 0.012);
    playLevelUpSound();
    addPopup(canvas.width / 2, canvas.height * 0.35, "⬆️ 等级 " + level + "！", "#ffd43b");
    showLevelBanner();
  }
}

let levelBannerTimer = 0;
function showLevelBanner() {
  levelBannerTimer = 90;
}

function sliceSegment(x1, y1, x2, y2) {
  for (const f of fruits) {
    if (f.sliced) continue;
    const d = pointToSegmentDist(f.x, f.y, x1, y1, x2, y2);
    if (d < FRUIT_RADIUS) {
      f.sliced = true;
      if (f.isBomb) {
        shakeTime = 18;
        playBombSound();
        gameOver();
        return;
      }

      registerCombo();
      const bonus = combo > 1 ? (combo - 1) * COMBO_BONUS : 0;
      const gained = 1 + bonus;
      score += gained;
      flashAlpha = 0.35;
      spawnParticles(f.x, f.y);
      spawnHalves(f.x, f.y, f.emoji, f.rot);
      playSliceSound(combo);

      if (combo > 1) {
        addPopup(f.x, f.y - 30, "Combo x" + combo + " +" + gained, "#ffd43b");
      } else {
        addPopup(f.x, f.y - 20, "+1", "#fff");
      }

      updateHud();
      updateDifficulty();
    }
  }
}

function checkSlice() {
  if (trail.length < 2) return;
  const p1 = trail[trail.length - 2];
  const p2 = trail[trail.length - 1];
  sliceSegment(p1.x, p1.y, p2.x, p2.y);
}

// ---------- 10. 主循环 ----------
function loop() {
  if (!running) return;
  if (paused) {
    requestAnimationFrame(loop);
    return;
  }

  ctx.save();
  if (shakeTime > 0) {
    const s = shakeTime / 18;
    ctx.translate((Math.random() - 0.5) * 12 * s, (Math.random() - 0.5) * 12 * s);
    shakeTime--;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 摄像头背景
  if (cameraOn && videoEl.readyState >= 2) {
    const cw = canvas.width, ch = canvas.height;
    const vw = videoEl.videoWidth, vh = videoEl.videoHeight;
    const scale = Math.max(cw / vw, ch / vh);
    const dw = vw * scale, dh = vh * scale;
    ctx.save();
    ctx.translate(cw / 2, ch / 2);
    ctx.scale(-1, 1);
    ctx.drawImage(videoEl, -dw / 2, -dh / 2, dw, dh);
    ctx.restore();
    // 半透明遮罩，让水果更醒目
    ctx.fillStyle = "rgba(20, 12, 40, 0.25)";
    ctx.fillRect(0, 0, cw, ch);
  } else {
    // 无摄像头时的渐变背景
    const g = ctx.createLinearGradient(0, 0, 0, canvas.height);
    g.addColorStop(0, "#2b1d52");
    g.addColorStop(1, "#16213e");
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }

  spawnTimer++;
  if (spawnTimer >= spawnInterval) {
    spawnTimer = 0;
    spawnFruit();
    if (Math.random() < 0.25 + level * 0.02) spawnFruit();
  }

  // 水果
  for (let i = fruits.length - 1; i >= 0; i--) {
    const f = fruits[i];
    f.vy += GRAVITY;
    f.x += f.vx;
    f.y += f.vy;
    f.rot += f.vr;

    ctx.save();
    ctx.translate(f.x, f.y);
    ctx.rotate(f.rot);
    ctx.font = FRUIT_SIZE + "px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(f.emoji, 0, 0);
    ctx.restore();

    if (f.y > canvas.height + 60) {
      if (!f.isBomb && !f.sliced) {
        lives -= 1;
        combo = 0;
        playMissSound();
        addPopup(f.x, canvas.height - 40, "漏掉了！", "#ff6b6b");
        updateHud();
        if (lives <= 0) { ctx.restore(); gameOver(); return; }
      }
      fruits.splice(i, 1);
    }
  }

  // 切开的两半
  for (let i = halves.length - 1; i >= 0; i--) {
    const h = halves[i];
    h.vy += GRAVITY * 0.6;
    h.x += h.vx;
    h.y += h.vy;
    h.rot += h.vr;
    h.life -= 0.02;
    if (h.life <= 0) { halves.splice(i, 1); continue; }
    ctx.save();
    ctx.globalAlpha = h.life;
    ctx.translate(h.x, h.y);
    ctx.rotate(h.rot);
    ctx.font = (FRUIT_SIZE * 0.7) + "px serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(h.emoji, 0, 0);
    ctx.restore();
  }

  // 果汁粒子
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

  // 刀光
  if (trail.length > 1) {
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (let i = 1; i < trail.length; i++) {
      const t = i / trail.length;
      ctx.strokeStyle = "rgba(255,255,255," + (t * 0.9) + ")";
      ctx.lineWidth = t * 12;
      ctx.beginPath();
      ctx.moveTo(trail[i - 1].x, trail[i - 1].y);
      ctx.lineTo(trail[i].x, trail[i].y);
      ctx.stroke();
    }
  }

  // 指尖指示器
  if (cameraOn && tipPos) {
    ctx.beginPath();
    ctx.arc(tipPos.x, tipPos.y, 26, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,107,107,0.25)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(tipPos.x, tipPos.y, 16, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(255,255,255,0.95)";
    ctx.fill();
    ctx.lineWidth = 5;
    ctx.strokeStyle = "#ff6b6b";
    ctx.stroke();
  }

  // 飘字
  for (let i = popups.length - 1; i >= 0; i--) {
    const p = popups[i];
    p.y += p.vy;
    p.life -= 0.02;
    if (p.life <= 0) { popups.splice(i, 1); continue; }
    ctx.globalAlpha = p.life;
    ctx.font = "bold 22px 'Microsoft YaHei', sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = p.color;
    ctx.fillText(p.text, p.x, p.y);
    ctx.globalAlpha = 1;
  }

  // 切中闪光
  if (flashAlpha > 0) {
    ctx.fillStyle = "rgba(255,255,255," + flashAlpha + ")";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    flashAlpha -= 0.04;
  }

  // 升级横幅
  if (levelBannerTimer > 0) {
    levelBannerTimer--;
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.fillRect(0, canvas.height * 0.28, canvas.width, 56);
    ctx.font = "bold 28px 'Microsoft YaHei', sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = "#ffd43b";
    ctx.fillText("⬆️ 升级到 等级 " + level + "！水果来得更快了～", canvas.width / 2, canvas.height * 0.28 + 36);
  }

  if (trail.length > 0) trail.shift();

  // 手势模式：游戏 60 帧/秒更新指尖，AI 只有 15~30 次/秒 → 中间用插值补上，更跟手
  if (cameraOn) updateHandPointer();

  ctx.restore();

  requestAnimationFrame(loop);
}

// ---------- 11. 输入：鼠标 / 触屏 ----------
function addTrailPoint(x, y) {
  trail.push({ x, y });
  if (trail.length > 18) trail.shift();
  checkSlice();
}

canvas.addEventListener("pointerdown", (e) => {
  if (!running || paused) return;
  trail = [];
  const p = toCanvasPos(e.clientX, e.clientY);
  addTrailPoint(p.x, p.y);
});
canvas.addEventListener("pointermove", (e) => {
  if (!running || paused) return;
  if (e.buttons || e.pointerType === "touch") {
    const p = toCanvasPos(e.clientX, e.clientY);
    addTrailPoint(p.x, p.y);
  }
});
canvas.addEventListener("pointerup", () => { trail = []; });

// ---------- 12. 摄像头手势识别 ----------
async function enableCamera() {
  modeTip.textContent = "📷 正在打开摄像头并加载手势模型…（需联网，首次稍慢）";
  modeTip.classList.remove("hidden");
  try {
    if (typeof Hands === "undefined" || typeof Camera === "undefined") {
      throw new Error("手势识别库没加载（可能没联网）");
    }

    const MP_VERSION = "0.4.1675469240";
    hands = new Hands({
      locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands@${MP_VERSION}/${file}`,
    });
    hands.setOptions({
      maxNumHands: 1,
      modelComplexity: HAND_MODEL,  // 0 轻量快，1 精准慢
      minDetectionConfidence: 0.5,
      minTrackingConfidence: 0.5,
    });
    hands.onResults(onHandResults);

    const cam = new Camera(videoEl, {
      onFrame: async () => {
        if (handBusy) return; // 算不过来就丢帧，比排队卡顿好
        handBusy = true;
        try {
          await hands.send({ image: videoEl });
        } catch (e) {
          modeTip.textContent = "⚠️ 手势模型运行出错：" + e.message;
        } finally {
          handBusy = false;
        }
      },
      width: CAMERA_WIDTH,
      height: CAMERA_HEIGHT,
    });
    await cam.start();

    cameraOn = true;
    startGame();
    modeTip.textContent = "📷 手势模式：伸手，用食指划过水果来切！";
  } catch (err) {
    cameraOn = false;
    running = false;
    modeTip.classList.add("hidden");
    document.getElementById("overlay").classList.remove("hidden");
    alert("摄像头或手势模型打不开（" + err.message + "）。可先点'鼠标开始'玩～");
  }
}

function onHandResults(results) {
  if (!running || paused) return;

  if (!results.multiHandLandmarks || results.multiHandLandmarks.length === 0) {
    tipTarget = null;
    tipPos = null;
    trail = [];
    modeTip.textContent = "📷 没看到手，把手伸进画面里";
    return;
  }

  const lm = results.multiHandLandmarks[0][8];
  const x = (1 - lm.x) * canvas.width;
  const y = lm.y * canvas.height;

  if (!tipTarget) {
    tipTarget = { x, y };
    tipPos = { x, y };
  } else {
    tipTarget = {
      x: tipTarget.x * HAND_SMOOTH + x * (1 - HAND_SMOOTH),
      y: tipTarget.y * HAND_SMOOTH + y * (1 - HAND_SMOOTH),
    };
  }

  modeTip.textContent = "📷 看到手了！用食指划过水果来切～";
}

// 每帧把指尖圆点往 AI 目标位置靠近，并在这之间做切割检测
function updateHandPointer() {
  if (!tipTarget) return;

  const prev = { x: tipPos.x, y: tipPos.y };
  tipPos.x += (tipTarget.x - tipPos.x) * HAND_LERP;
  tipPos.y += (tipTarget.y - tipPos.y) * HAND_LERP;

  sliceSegment(prev.x, prev.y, tipPos.x, tipPos.y);

  trail.push({ x: tipPos.x, y: tipPos.y });
  if (trail.length > 18) trail.shift();
}

// ---------- 13. HUD 更新 ----------
function updateHud() {
  document.getElementById("score").textContent = "分数：" + score;
  document.getElementById("lives").textContent = "❤️".repeat(Math.max(0, lives));
  document.getElementById("level").textContent = "等级 " + level;
  const comboEl = document.getElementById("combo");
  if (combo > 1) {
    comboEl.textContent = "🔥 Combo x" + combo;
    comboEl.classList.add("active");
  } else {
    comboEl.textContent = "";
    comboEl.classList.remove("active");
  }
  document.getElementById("highScore").textContent = "最高：" + getHighScore();
}

// ---------- 14. 暂停 ----------
function togglePause() {
  if (!running) return;
  paused = !paused;
  document.getElementById("pauseOverlay").classList.toggle("hidden", !paused);
}

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" || e.key === "p" || e.key === "P") togglePause();
});

document.getElementById("resumeBtn").addEventListener("click", togglePause);

// ---------- 15. 开始 / 结束 ----------
function startGame() {
  fruits = [];
  particles = [];
  halves = [];
  popups = [];
  trail = [];
  score = 0;
  lives = STARTING_LIVES;
  level = 1;
  combo = 0;
  bestCombo = 0;
  spawnTimer = 0;
  spawnInterval = SPAWN_INTERVAL;
  bombChance = BOMB_CHANCE;
  tipPos = null;
  tipTarget = null;
  handBusy = false;
  paused = false;
  flashAlpha = 0;
  shakeTime = 0;
  levelBannerTimer = 0;
  updateHud();
  document.getElementById("overlay").classList.add("hidden");
  document.getElementById("gameover").classList.add("hidden");
  document.getElementById("pauseOverlay").classList.add("hidden");
  if (!cameraOn) modeTip.classList.add("hidden");
  document.getElementById("pauseBtn").classList.remove("hidden");
  running = true;
  ensureAudio();
  loop();
}

function gameOver() {
  running = false;
  document.getElementById("pauseBtn").classList.add("hidden");
  const oldHigh = getHighScore();
  const isNewRecord = score > oldHigh;
  saveHighScore();
  document.getElementById("finalScore").textContent =
    "你切到了 " + score + " 个水果！最高连击 Combo x" + bestCombo;
  document.getElementById("finalRecord").textContent =
    isNewRecord ? "🎉 新纪录！已保存到本机" : "本机最高分：" + getHighScore();
  document.getElementById("gameover").classList.remove("hidden");
}

document.getElementById("startBtn").addEventListener("click", () => {
  cameraOn = false;
  startGame();
});
document.getElementById("camBtn").addEventListener("click", enableCamera);
document.getElementById("restartBtn").addEventListener("click", startGame);
document.getElementById("pauseBtn").addEventListener("click", togglePause);

updateHud();
