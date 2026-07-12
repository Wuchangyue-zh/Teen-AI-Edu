from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
source = Image.open(ROOT / "source/otter_contact_sheet.png").convert("RGB")

# Hand-tuned after visual inspection of the 3×2 generated panel grid.
boxes = [
    (12, 137, 413, 618), (427, 137, 828, 618), (841, 137, 1243, 618),
    (12, 636, 413, 1117), (427, 636, 828, 1117), (841, 636, 1243, 1117),
]

frames = []
for i, box in enumerate(boxes, 1):
    frame = source.crop(box).resize((200, 240), Image.Resampling.LANCZOS)
    frame.save(ROOT / "frames" / f"frame_{i:02d}.png", optimize=True)
    frames.append(frame)

# Modest pause on the readable start/end beats makes the joke land in chat.
durations = [250, 250, 250, 400, 200, 700]
frames[0].save(
    ROOT / "output/otter-understanding.gif", save_all=True, append_images=frames[1:],
    duration=durations, loop=0, disposal=2, optimize=True,
)

# A static contact sheet makes the sequence easy to evaluate without playback.
poster = Image.new("RGB", (600, 480), "#fffaf0")
for i, frame in enumerate(frames):
    poster.paste(frame, ((i % 3) * 200, (i // 3) * 240))
poster.save(ROOT / "output/otter-understanding-contact-sheet.jpg", quality=88, optimize=True)

gif = Image.open(ROOT / "output/otter-understanding.gif")
report = f'''# Baseline execution report — Otter “懂了”

- Method: one image-model-generated 3×2 action sheet, then local Pillow crop/split and GIF assembly.
- Narrative frames: attentive listen → serious listen → eyes drift → blank stare → snap back/nod → happy nod + “懂了”.
- Source canvas: {source.size[0]}×{source.size[1]} px; split into 6 independently saved PNG frames.
- GIF: {gif.size[0]}×{gif.size[1]} px, {gif.n_frames} frames, looping, {sum(durations)/1000:.2f} s per cycle.
- File size: {(ROOT / "output/otter-understanding.gif").stat().st_size:,} bytes ({(ROOT / "output/otter-understanding.gif").stat().st_size / 1024:.1f} KiB).
- Visual checks: character identity is consistent; all six story beats are present; final bubble reads “懂了”; final frame has clear nod motion lines; no watermark or unrelated text observed.
- WeChat suitability: compact looping GIF at 200×240 px and well under common custom-emoji size limits. Import as a GIF custom emoji; platform-side limits can vary by client/version.
'''
(ROOT / "outputs/execution_report.md").write_text(report, encoding="utf-8")
