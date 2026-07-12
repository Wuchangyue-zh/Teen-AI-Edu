# Teen-AI-Edu (AI 青少年培训项目)

这是一个针对 4–6 年级小学生的 AI 创新与实践培训项目课程库。旨在引导孩子们把“刷手机、玩屏幕的时间”，转变为“亲手做出一件拿得手、可展示的 AI 创意作品”的成就感。

## 📂 项目结构

* **`儿童AI故事视频/`**：MVP（最简可行产品）核心案例。
  * **`视频创作skills/`**：封装的 AI Skill 包，包含自动生成 3:4 故事视频的脚本和公共素材。
    * `脚本/`：视频生成、生图、配音克隆和视频合成的主程序。
    * `参考/`：故事创作规则与样例数据（如 `story.example.json`）。
    * `资源/背景音乐/`：故事视频中使用的内置免版权背景音乐资产。
* **`官方文章和政策/`**：培训课程相关的其它写作与课程案例物料。
* **`AI青少年培训_试点执行清单.md`**：社区体验课试点的 SOP、运营排期和转化脚本。

---

## 🛠️ 环境准备与快速上手 (儿童 AI 故事视频案例)

### 1. 依赖安装

在使用视频生成脚本前，请确保您的电脑上已安装：
* **Python 3.10+**
* **FFmpeg** 及其命令行工具（确保能在终端中通过 `ffmpeg` 和 `ffprobe` 运行）

### 2. 密钥配置

在项目运行前，需要进行 API Key 的配置：
1. 在 `儿童AI故事视频/视频创作skills/` 下，复制 `.env.example` 并命名为 `.env`。
2. 在该 `.env` 文件中填写您的 API Key：
   ```env
   VOLCENGINE_API_KEY=您的火山引擎API_KEY
   MIMO_API_KEY=您的小米MiMo_API_KEY
   ```
   *(注：该文件已被 `.gitignore` 自动忽略，绝不会被推送到远端仓库。)*

### 3. 环境预检

在终端运行以下预检命令：
```bash
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py preflight
```
若检查结果显示 `可以开始制作`，则表示环境配置完成。

### 4. 单元测试运行

在根目录下运行以下命令可以对系统逻辑进行测试：
```bash
# 运行本地故事基础校验测试
PYTHONPATH=儿童AI故事视频/视频创作skills python3 儿童AI故事视频/视频创作skills/脚本/测试/test_local.py

# 运行背景音乐匹配逻辑测试
PYTHONPATH=儿童AI故事视频/视频创作skills python3 儿童AI故事视频/视频创作skills/脚本/测试/test_bgm.py
```

---

## 🚀 视频生成命令指引

通常，在支持 Agent Skills 的编辑器（如 WorkBuddy、TRAE）中，您可以直接使用自然语言给 AI 派发任务，系统将自动识别 Skill 并调用脚本。如果您需要手动执行脚本，请遵循以下三阶段命令（中途有停顿核对点）：

### 阶段 1：生成文稿并导出 DOCX
```bash
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py init \
  --project "儿童AI故事视频/小小创作者001" \
  --drawing "您的原画图片路径.jpg" \
  --story "儿童AI故事视频/视频创作skills/参考/story.example.json" \
  --voice "参考录音路径.wav"
```
*请核对项目目录下的 `故事.docx` 文档并保存修改后再继续。*

### 阶段 2：生成故事配图与声音旁白
```bash
# 生成配图并自动插入 Word
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py images --project "儿童AI故事视频/小小创作者001"

# 生成各幕旁白音频
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py voice --project "儿童AI故事视频/小小创作者001"
```
*请重新打开 `故事.docx` 检查画面和排版，并在 `声音/` 目录下试听旁白后再继续。*

### 阶段 3：合成最终故事视频
```bash
# 合成 3:4 故事视频并完成校验
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py render --project "儿童AI故事视频/小小创作者001"
PYTHONPATH=儿童AI故事视频/视频创作skills/脚本 python3 儿童AI故事视频/视频创作skills/脚本/run.py verify --project "儿童AI故事视频/小小创作者001"
```

更多指令与参数细节请阅读 [儿童AI故事视频/README.md](file:///Users/dielangli/Desktop/AI%E9%9D%92%E5%B0%91%E5%B9%B4%E5%9F%B9%E8%AE%AD/%E5%84%BF%E7%AB%A5AI%E6%95%85%E4%BA%8B%E8%A7%86%E9%A2%91/README.md)。
