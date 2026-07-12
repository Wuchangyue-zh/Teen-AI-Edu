---
name: 微信动图表情
description: 为微信聊天制作可传播的 GIF 表情。用户提到微信表情包、动图表情、聊天反应图、斗图、打工人自嘲图或想把故事做成 GIF 时使用。技能按“迷你故事脚本 → 原始分镜素材 → GIF 成品”三步工作；除非用户明确要求一口气完成，否则每步结束都停下来请用户确认。所有项目过程文件和成品均使用中文目录与文件名。
compatibility: 需要内置文生图工具，以及安装 Pillow 的 Python 3。
---

# 微信动图表情

目标是做一张在聊天窗口里一眼看懂、愿意转发的表情。动作有铺垫和包袱，文字只做加分，不替代动作。

## 项目结构

每个项目在用户指定根目录下新建一个中文名称文件夹，不覆盖旧项目：

```text
<根目录>/<项目名称>/
  迷你故事脚本.md
  生成提示词.txt
  原始素材/连环分镜.png
  分帧图片/第01帧.png …
  最终成品/<项目名称>.gif
  最终成品/首帧预览.png
  质检报告/质量检查.json
  质检报告/动作预览图.png
```

## 三步确认工作流

默认采用“做完一步、让用户看一步”的协作方式。用户没有明确说“直接做完”“一口气完成”“不用确认”时，严格停在每一步末尾，展示结果路径和一句简短说明，并等待确认或修改意见。

若用户明确要求生成完整案例、直接完成或作为自动验收测试，可连续执行三步；在 `迷你故事脚本.md` 首行记录“本次按用户明确授权连续执行”。

### 第一步：迷你故事脚本

创建 `迷你故事脚本.md`，用 4 行写出四格动作：

1. **铺垫**：角色正处于哪种日常情境。
2. **触发**：发生什么让人有反应。
3. **包袱**：动作或表情如何反转，形成笑点。
4. **循环**：最后一格如何自然接回第一格。

再补充“聊天场景、角色、文字设计、画面重点”。角色使用原创形象，不使用真人、知名 IP、品牌或攻击特定人群。自嘲题材用荒诞和反差来表达无奈。

停下来请用户确认故事是否够好笑、文字是否合适。只有确认后才进入第二步。

### 第二步：生成原始素材

将确认过的完整提示词保存到 `生成提示词.txt`，再调用内置文生图工具生成正方形、规则 2×2 连环分镜，并保存为 `原始素材/连环分镜.png`。

使用纯白背景，避免绿幕抠图造成边缘残色；最终 GIF 也使用纯白背景。提示词结构如下：

```text
Use case: illustration-story
Asset type: WeChat custom animated sticker storyboard, to be cut into GIF frames
Primary request: original [角色] reacting “[聊天场景]” in four beats: [第1格]; [第2格]; [第3格]; [第4格].
Style/medium: original polished 2D Chinese chat-sticker illustration, bold clean outlines, high-contrast flat colours, highly expressive face.
Composition/framing: one perfectly regular 2 by 2 storyboard grid; four equal square panels; same character scale, viewpoint and placement; generous padding; thin pale-gray divider lines only.
Scene/backdrop: perfectly flat pure white #FFFFFF background in every panel; no gradients, floor, shadows, reflections, texture, watermark, decorative borders, or panel labels.
Text (verbatim): "[0–5个汉字，或 NONE]"
Text design: large, bold, high-contrast Chinese lettering in a clear empty area; text must be correct and legible at 240 by 240 pixels.
Constraints: each panel is a distinct sequential pose; preserve character identity; no logos; no other characters unless the story needs them.
```

文字可用于补充戏谑，例如“下班？”、“又来？”、“收到…”。只使用极短、常用的中文；如果文字渲染不可靠，去掉文字也要能看懂笑点。检查四格是否齐全、角色是否一致、文字是否正确、动作是否有递进。

停下来让用户查看分镜，接受“改文字、改动作、改角色、重新生成”等意见。确认后才进入第三步。

### 第三步：拼接成 GIF

运行技能内的中文脚本，切出每格并导出白底 GIF：

```bash
python3 <技能目录>/脚本/拼接动图.py \
  --source <项目目录>/原始素材/连环分镜.png \
  --project <项目目录> \
  --rows 2 --cols 2 --gutter 4 --durations 500,500,500,1000
```

`--durations` 是各帧停留时长（毫秒）。四格表情推荐从 `500,500,500,1000` 开始：前三个动作每格停半秒，读图更轻松，最后包袱帧停一秒；想加快或加强无奈感时再按故事节奏调整。脚本将统一每一帧的裁切区域，防止角色跳动；导出循环 GIF、最大边长 240 像素、文件不超过 500 KB、纯白无透明背景。它会写入中文命名的分帧、首帧预览、动作预览图和 `质量检查.json`。

交付前检查：

1. `质量检查.json` 的“是否通过”为真，且“背景检查”为“白色背景通过”。
2. GIF 是循环 GIF，大小不超过 240×240、文件不超过 500 KB。
3. 肉眼检查 `动作预览图.png`：人物稳定、文字可读、无绿色边缘、白底干净、循环自然。

最后报告成品路径、尺寸、帧数、时长、文件大小。用户可将 GIF 发到微信后长按选择“添加到表情”。
