const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.author = "Teen-AI-Edu";
pres.title = "如何使用正确的提示词生图 · 社区体验课";

const IMG = "E:/EduProject/Teen-AI-Edu/如何使用正确的提示词生图/物料包/预生成图库";
const OUT = "E:/EduProject/Teen-AI-Edu/如何使用正确的提示词生图/物料包/如何使用正确的提示词生图_社区体验课.pptx";

// palette
const C_DARK = "2A3B47", C_BG = "FBF6EE", C_PRIMARY = "E8654A", C_ACCENT = "2A6F87",
      C_GOLD = "F2B441", C_TEXT = "2C2C2A", C_MUTED = "7A7770", C_WHITE = "FFFFFF", C_LINE = "E8E2D6";
const F = "Microsoft YaHei";

function titleBar(s, text, sub) {
  s.background = { color: C_BG };
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.46, w: 0.26, h: 0.52, fill: { color: C_PRIMARY }, line: { type: "none" } });
  s.addText(text, { x: 0.92, y: 0.36, w: 8.6, h: 0.72, fontSize: 28, fontFace: F, bold: true, color: C_TEXT, margin: 0, valign: "middle" });
  if (sub) s.addText(sub, { x: 0.92, y: 1.02, w: 8.6, h: 0.4, fontSize: 14, fontFace: F, color: C_MUTED, margin: 0 });
}
function card(s, x, y, w, h, accent) {
  s.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: C_WHITE }, line: { color: C_LINE, width: 0.5 } });
  s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.09, h, fill: { color: accent || C_PRIMARY }, line: { type: "none" } });
}
function notes(s, t) { s.addNotes(t); }

// ===== P1 封面 =====
{
  const s = pres.addSlide();
  s.background = { color: C_DARK };
  s.addImage({ path: IMG + "/保底图库/一座漂浮在云上的城堡_绘本插画风格_2026-07-12T14-38-28.png", x: 5.9, y: 0.5, w: 3.8, h: 4.7, sizing: { type: "cover", w: 3.8, h: 4.7 } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 6.2, h: 5.625, fill: { color: C_DARK }, line: { type: "none" } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.5, w: 0.5, h: 0.12, fill: { color: C_GOLD }, line: { type: "none" } });
  s.addText("如何使用正确的\n提示词生图", { x: 0.6, y: 1.7, w: 6, h: 1.8, fontSize: 40, fontFace: F, bold: true, color: C_WHITE, margin: 0, lineSpacingMultiple: 1.1 });
  s.addText("珠海 XX 社区 · AI 小创客", { x: 0.6, y: 3.6, w: 6, h: 0.5, fontSize: 16, fontFace: F, color: "C9D3D8" });
  s.addText("你是导演，AI 是画笔", { x: 0.6, y: 4.1, w: 6, h: 0.5, fontSize: 14, fontFace: F, italic: true, color: C_GOLD });
  notes(s, "开场：今天不听课，直接教 AI 给你画图——但前提是，你得把话说对。公益体验，后续有正式课可了解，不强求。");
}

// ===== P2 开场互动 =====
{
  const s = pres.addSlide();
  titleBar(s, "谁用过 AI 画图？", "先举手，按经验分层");
  card(s, 0.6, 1.7, 4.2, 2.6, C_PRIMARY);
  s.addText("用过的", { x: 0.9, y: 1.9, w: 3.6, h: 0.5, fontSize: 18, fontFace: F, bold: true, color: C_PRIMARY, margin: 0 });
  s.addText("别得意，等下看“清楚提示词”和你平时说的差在哪。", { x: 0.9, y: 2.5, w: 3.6, h: 1.6, fontSize: 15, fontFace: F, color: C_TEXT, margin: 0, paraSpaceAfter: 6 });
  card(s, 5.2, 1.7, 4.2, 2.6, C_ACCENT);
  s.addText("没用过的", { x: 5.5, y: 1.9, w: 3.6, h: 0.5, fontSize: 18, fontFace: F, bold: true, color: C_ACCENT, margin: 0 });
  s.addText("没关系，今天教你让 AI 给你画。", { x: 5.5, y: 2.5, w: 3.6, h: 1.6, fontSize: 15, fontFace: F, color: C_TEXT, margin: 0 });
  notes(s, "分层切入话术：用过的别得意；没用过的别担心。不假设零基础。");
}

// ===== P3 今天你是导演 =====
{
  const s = pres.addSlide();
  titleBar(s, "今天你是导演");
  s.addText("你说什么，AI 画什么。", { x: 0.6, y: 2.2, w: 8.8, h: 1, fontSize: 30, fontFace: F, bold: true, color: C_TEXT, align: "center", margin: 0 });
  s.addText("AI 不会替你想 —— 画什么，你说了算。", { x: 0.6, y: 3.2, w: 8.8, h: 0.8, fontSize: 18, fontFace: F, color: C_MUTED, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 4.5, y: 4.3, w: 1, h: 0.08, fill: { color: C_GOLD }, line: { type: "none" } });
  notes(s, "立人设：你是导演，AI 是画笔。主体性先行。");
}

// ===== P4 AI 为什么能画 =====
{
  const s = pres.addSlide();
  titleBar(s, "AI 为什么能画？");
  s.addText("AI 像一个看过亿万张图、按你文字“猜”画面的朋友。", { x: 0.8, y: 1.9, w: 8.4, h: 1.4, fontSize: 22, fontFace: F, color: C_TEXT, margin: 0, lineSpacingMultiple: 1.2 });
  s.addText("所以 —— 要说清，它才猜得准；它也会猜错。", { x: 0.8, y: 3.1, w: 8.4, h: 0.9, fontSize: 20, fontFace: F, bold: true, color: C_PRIMARY, margin: 0 });
  s.addShape(pres.shapes.OVAL, { x: 8.6, y: 1.5, w: 0.9, h: 0.9, fill: { color: C_GOLD }, line: { type: "none" } });
  s.addText("猜", { x: 8.6, y: 1.5, w: 0.9, h: 0.9, fontSize: 24, fontFace: F, bold: true, color: C_WHITE, align: "center", valign: "middle", margin: 0 });
  notes(s, "原理一句话：AI 从海量图学规律、按文字猜画面，所以会说清、会猜错。");
}

// ===== P5 三档对比 =====
{
  const s = pres.addSlide();
  titleBar(s, "同一只猫，三句话，差在哪？", "差距不在 AI，在“说没说清”");
  const ys = 1.7, h = 2.7, w = 2.7;
  const xs = [0.45, 3.65, 6.85];
  const imgs = [IMG + "/三档对比/画只猫_2026-07-12T14-37-36.png", IMG + "/三档对比/一只猫_2026-07-12T14-37-36.png", IMG + "/三档对比/一只戴红围巾的小猫_坐在屋顶看星星_水彩风格_暖黄灯光_安静_2026-07-12T14-37-36.png"];
  const caps = ["① 画只猫", "② 一只猫", "③ 戴红围巾小猫坐屋顶看星星…"];
  const tags = ["模糊", "仍空", "清楚"];
  const colors = [C_MUTED, C_GOLD, C_ACCENT];
  for (let i = 0; i < 3; i++) {
    s.addImage({ path: imgs[i], x: xs[i], y: ys, w, h, sizing: { type: "cover", w, h } });
    s.addShape(pres.shapes.RECTANGLE, { x: xs[i], y: ys + h - 0.5, w, h: 0.5, fill: { color: C_DARK }, line: { type: "none" } });
    s.addText(tags[i], { x: xs[i], y: ys + h - 0.5, w, h: 0.5, fontSize: 14, fontFace: F, bold: true, color: colors[i], align: "center", valign: "middle", margin: 0 });
    s.addText(caps[i], { x: xs[i], y: ys + h + 0.05, w, h: 0.7, fontSize: 12, fontFace: F, color: C_TEXT, align: "center", margin: 0 });
  }
  notes(s, "三档对比话术：不是 AI 笨，是话没说清。【注意】此页三张图为内置模型生成，正式课前请用豆包重跑这三张替换，保证与课堂工具一致。");
}

// ===== P6 五要素 =====
{
  const s = pres.addSlide();
  titleBar(s, "把画面拆成五块", "五要素 = 一句清楚的话");
  const items = [["主体", "画的是什么", C_PRIMARY], ["场景", "在做什么/在哪", C_ACCENT], ["风格", "水彩/卡通/绘本", C_GOLD], ["光线", "暖黄/星空/夕阳", C_ACCENT], ["情绪", "开心/勇敢/温柔", C_PRIMARY]];
  const w = 1.74, gap = 0.1, x0 = 0.5, y = 2.0, h = 2.4;
  for (let i = 0; i < 5; i++) {
    const x = x0 + i * (w + gap);
    card(s, x, y, w, h, items[i][2]);
    s.addText(items[i][0], { x: x + 0.2, y: y + 0.25, w: w - 0.3, h: 0.6, fontSize: 20, fontFace: F, bold: true, color: items[i][2], margin: 0 });
    s.addText(items[i][1], { x: x + 0.2, y: y + 1.0, w: w - 0.3, h: 1.2, fontSize: 13, fontFace: F, color: C_TEXT, margin: 0 });
  }
  notes(s, "五要素：主体+场景+风格+光线+情绪。没有标准答案，只有更清楚。");
}

// ===== P7 五要素示范 =====
{
  const s = pres.addSlide();
  titleBar(s, "看一张图，倒推五要素", "示范：图 → 词");
  s.addImage({ path: IMG + "/保底图库/一只戴围巾的小猫在屋顶看星星_绘本插画风格_2026-07-12T14-38-28.png", x: 0.6, y: 1.5, w: 2.8, h: 3.6, sizing: { type: "cover", w: 2.8, h: 3.6 } });
  const rows = [["主体", "戴围巾的小猫"], ["场景", "坐在屋顶"], ["风格", "绘本插画"], ["光线", "星空"], ["情绪", "安静温柔"]];
  for (let i = 0; i < 5; i++) {
    const y = 1.6 + i * 0.62;
    card(s, 3.8, y, 5.6, 0.5, C_PRIMARY);
    s.addText(rows[i][0], { x: 4.0, y, w: 1.2, h: 0.5, fontSize: 14, fontFace: F, bold: true, color: C_PRIMARY, valign: "middle", margin: 0 });
    s.addText(rows[i][1], { x: 5.2, y, w: 4.0, h: 0.5, fontSize: 14, fontFace: F, color: C_TEXT, valign: "middle", margin: 0 });
  }
  notes(s, "示范：用一张参考图带孩子集体填五要素，练图→词逆向能力。");
}

// ===== P8 清楚 vs 模糊 =====
{
  const s = pres.addSlide();
  titleBar(s, "清楚 vs 模糊", "“好看”AI 听不懂，要换成具体词");
  const data = [["画只猫", "一只趴在窗台的橘猫，午后阳光"], ["画个好看的场景", "秋天的树林小路，落叶满地，金色光线"], ["一个勇敢的骑士", "一个勇敢的骑士，绘本插画风格，冷色调"]];
  for (let i = 0; i < 3; i++) {
    const y = 1.7 + i * 1.05;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y, w: 4.0, h: 0.85, fill: { color: "FBEAEA" }, line: { color: C_LINE, width: 0.5 } });
    s.addText(data[i][0], { x: 0.75, y, w: 3.8, h: 0.85, fontSize: 14, fontFace: F, color: C_MUTED, valign: "middle", margin: 0 });
    s.addText("→", { x: 4.6, y, w: 0.5, h: 0.85, fontSize: 20, fontFace: F, bold: true, color: C_PRIMARY, align: "center", valign: "middle", margin: 0 });
    s.addShape(pres.shapes.RECTANGLE, { x: 5.1, y, w: 4.3, h: 0.85, fill: { color: "EAF3F5" }, line: { color: C_LINE, width: 0.5 } });
    s.addText(data[i][1], { x: 5.25, y, w: 4.1, h: 0.85, fontSize: 14, fontFace: F, color: C_TEXT, valign: "middle", margin: 0 });
  }
  notes(s, "对照：把模糊换成能看见的具体词，AI 就会画了。");
}

// ===== P9 找错并改清游戏 =====
{
  const s = pres.addSlide();
  titleBar(s, "游戏 · 把“坏话”改清楚", "谁能把这句改清楚？");
  card(s, 0.6, 2.0, 4.0, 2.2, C_MUTED);
  s.addText("坏话", { x: 0.9, y: 2.2, w: 3.5, h: 0.5, fontSize: 16, fontFace: F, bold: true, color: C_MUTED, margin: 0 });
  s.addText("“画个好看的场景”", { x: 0.9, y: 2.8, w: 3.5, h: 1.2, fontSize: 18, fontFace: F, color: C_TEXT, margin: 0 });
  s.addText("→ 改一改 →", { x: 4.7, y: 2.7, w: 1.2, h: 0.6, fontSize: 14, fontFace: F, bold: true, color: C_PRIMARY, align: "center", margin: 0 });
  card(s, 5.9, 2.0, 3.6, 2.2, C_ACCENT);
  s.addText("清楚", { x: 6.2, y: 2.2, w: 3.2, h: 0.5, fontSize: 16, fontFace: F, bold: true, color: C_ACCENT, margin: 0 });
  s.addText("“秋天的树林小路，落叶满地，金色光线”", { x: 6.2, y: 2.8, w: 3.2, h: 1.2, fontSize: 15, fontFace: F, color: C_TEXT, margin: 0 });
  notes(s, "找错并改清游戏：让孩子改模糊句，体会具体词的作用。");
}

// ===== P10 看图挑错 =====
{
  const s = pres.addSlide();
  titleBar(s, "AI 也会错 · 看图挑错", "AI 在“猜”，会猜错 —— 画完自己看一遍");
  const imgs = [IMG + "/翻车示例/照片级写实_一个小女孩在弹钢琴的特写_清晰看到双手和手指_2026-07-12T14-37-36.png", IMG + "/翻车示例/一张海报_上面用大字写着夏天快乐四个汉字_2026-07-12T14-37-36.png"];
  const caps = ["多指 / 多肢（数手指）", "文字乱码（AI 不会写字）"];
  const xs = [0.7, 5.5];
  for (let i = 0; i < 2; i++) {
    s.addImage({ path: imgs[i], x: xs[i], y: 1.6, w: 3.8, h: 2.6, sizing: { type: "cover", w: 3.8, h: 2.6 } });
    s.addText(caps[i], { x: xs[i], y: 4.25, w: 3.8, h: 0.5, fontSize: 14, fontFace: F, bold: true, color: C_PRIMARY, align: "center", margin: 0 });
  }
  s.addText("还有：违反物理（水往上流）· 角色漂移（前后不一样）", { x: 0.6, y: 4.85, w: 8.8, h: 0.4, fontSize: 12, fontFace: F, color: C_MUTED, align: "center", margin: 0 });
  notes(s, "看图挑错话术：AI 在猜会猜错。【注意】这两张是翻车尝试图，模型已较稳，不一定真翻车；课堂真实翻车即时截图更有效。多指/乱码是AI错非提示词错，重生成不计入学生迭代。");
}

// ===== P11 AI 小规矩 =====
{
  const s = pres.addSlide();
  titleBar(s, "AI 小规矩", "记住了，才能放心用 AI");
  const rules = [["不画别人脸、不造假图", C_PRIMARY], ["AI 会出错，别全信它", C_ACCENT], ["分享前先问家长", C_GOLD]];
  for (let i = 0; i < 3; i++) {
    const x = 0.6 + i * 3.05;
    card(s, x, 2.0, 2.85, 2.6, rules[i][1]);
    s.addShape(pres.shapes.OVAL, { x: x + 1.05, y: 2.3, w: 0.7, h: 0.7, fill: { color: rules[i][1] }, line: { type: "none" } });
    s.addText(String(i + 1), { x: x + 1.05, y: 2.3, w: 0.7, h: 0.7, fontSize: 26, fontFace: F, bold: true, color: C_WHITE, align: "center", valign: "middle", margin: 0 });
    s.addText(rules[i][0], { x: x + 0.2, y: 3.2, w: 2.45, h: 1.2, fontSize: 15, fontFace: F, bold: true, color: C_TEXT, align: "center", margin: 0 });
  }
  notes(s, "AI 小规矩三条：不画别人脸不造假、AI会出错别全信、分享前问家长。城市家长对隐私敏感，是加分项。");
}

// ===== P12 实践 1 =====
{
  const s = pres.addSlide();
  titleBar(s, "实践 1 · 第一次生图", "现在轮到你当导演");
  const items = [["有想法", "直接画自己的", C_PRIMARY], ["卡住了", "挑灵感图卡，描述+变体", C_ACCENT], ["等生图时", "做手里的任务卡", C_GOLD]];
  for (let i = 0; i < 3; i++) {
    const y = 1.8 + i * 1.05;
    card(s, 0.6, y, 8.8, 0.85, items[i][2]);
    s.addText(items[i][0], { x: 0.85, y, w: 1.8, h: 0.85, fontSize: 16, fontFace: F, bold: true, color: items[i][2], valign: "middle", margin: 0 });
    s.addText(items[i][1], { x: 2.7, y, w: 6.5, h: 0.85, fontSize: 15, fontFace: F, color: C_TEXT, valign: "middle", margin: 0 });
  }
  notes(s, "实践1：分组轮换生图，等待时做任务卡，别空等。引导自检：说清了吗？画对了吗？");
}

// ===== P13 实践 2 =====
{
  const s = pres.addSlide();
  titleBar(s, "实践 2 · 改清 + 迭代", "第一张不理想？正常，改一个词试试");
  s.addShape(pres.shapes.RECTANGLE, { x: 1.0, y: 2.4, w: 3.2, h: 1.6, fill: { color: "FBEAEA" }, line: { color: C_LINE, width: 0.5 } });
  s.addText("v1\n“画只猫”", { x: 1.0, y: 2.4, w: 3.2, h: 1.6, fontSize: 18, fontFace: F, color: C_MUTED, align: "center", valign: "middle", margin: 0, lineSpacingMultiple: 1.2 });
  s.addText("加/换一个词 →", { x: 4.3, y: 2.9, w: 1.6, h: 0.6, fontSize: 14, fontFace: F, bold: true, color: C_PRIMARY, align: "center", valign: "middle", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.0, y: 2.4, w: 3.2, h: 1.6, fill: { color: "EAF3F5" }, line: { color: C_LINE, width: 0.5 } });
  s.addText("v2\n“戴围巾小猫坐屋顶看星星…”", { x: 6.0, y: 2.4, w: 3.2, h: 1.6, fontSize: 15, fontFace: F, color: C_TEXT, align: "center", valign: "middle", margin: 0, lineSpacingMultiple: 1.2 });
  notes(s, "实践2：哪句没说清？加/换一个词再生成。多指/乱码是AI错，重画一次不计迭代。迭代≤2次。");
}

// ===== P14 图文小卡 =====
{
  const s = pres.addSlide();
  titleBar(s, "把作品包成图文小卡", "图 + 提示词 + 一句感悟");
  // card mockup
  s.addShape(pres.shapes.RECTANGLE, { x: 2.6, y: 1.4, w: 4.8, h: 3.9, fill: { color: C_WHITE }, line: { color: C_LINE, width: 0.75 } });
  s.addImage({ path: IMG + "/保底图库/一只会飞的小狗在夜空_绘本插画风格_2026-07-12T14-38-28.png", x: 2.8, y: 1.6, w: 4.4, h: 2.4, sizing: { type: "cover", w: 4.4, h: 2.4 } });
  s.addText("珠海XX社区 · AI 小创客 · 小石头 作品", { x: 2.8, y: 4.05, w: 4.4, h: 0.35, fontSize: 11, fontFace: F, color: C_MUTED, align: "center", margin: 0 });
  s.addText("我的提示词：一只会飞的小狗…绘本风，星空，勇敢", { x: 2.8, y: 4.4, w: 4.4, h: 0.4, fontSize: 11, fontFace: F, color: C_TEXT, margin: 0 });
  s.addText("感悟：把“好看”换成“星空光线”，AI 就画对了。", { x: 2.8, y: 4.8, w: 4.4, h: 0.4, fontSize: 11, fontFace: F, italic: true, color: C_PRIMARY, margin: 0 });
  notes(s, "图文小卡：Agent输出素材，拼卡由人完成。这是带走的作品，也是护城河。");
}

// ===== P15 首映 =====
{
  const s = pres.addSlide();
  titleBar(s, "首映 · 放给爸妈看", "你最满意的那张，给爸妈看");
  s.addText("把作品放给家长看 —— 老师不抢话。", { x: 0.6, y: 2.3, w: 8.8, h: 1, fontSize: 26, fontFace: F, bold: true, color: C_TEXT, align: "center", margin: 0 });
  s.addShape(pres.shapes.RECTANGLE, { x: 4.5, y: 3.5, w: 1, h: 0.08, fill: { color: C_GOLD }, line: { type: "none" } });
  notes(s, "首映：孩子展示，老师不抢话。家长“眼睛亮”的瞬间交给家长。");
}

// ===== P16 结尾 =====
{
  const s = pres.addSlide();
  s.background = { color: C_DARK };
  s.addText("一句话原则", { x: 0.6, y: 1.0, w: 8.8, h: 0.7, fontSize: 18, fontFace: F, color: C_GOLD, margin: 0 });
  s.addText("说清楚了，画才对；\n画完自己看；\n你是导演，AI 是画笔。", { x: 0.6, y: 1.7, w: 8.8, h: 2.4, fontSize: 30, fontFace: F, bold: true, color: C_WHITE, margin: 0, lineSpacingMultiple: 1.3 });
  s.addText("今天公益体验，后续有正式课可了解，不强求。", { x: 0.6, y: 4.5, w: 8.8, h: 0.5, fontSize: 13, fontFace: F, italic: true, color: "C9D3D8" });
  notes(s, "结尾：点题。轻量去推销化口径。");
}

pres.writeFile({ fileName: OUT }).then(f => console.log("WROTE " + f));
