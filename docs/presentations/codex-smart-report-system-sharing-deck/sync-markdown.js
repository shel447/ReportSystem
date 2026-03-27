"use strict";

const fs = require("fs");
const path = require("path");
const { meta, slides } = require("./slides-data");

function fileLink(target) {
  const normalized = target.replace(/\\/g, "/");
  const label = path.basename(normalized);
  return `[${label}](${normalized})`;
}

function renderList(items) {
  return items.map((item) => `- ${item}`).join("\n");
}

function renderSources(items) {
  if (!items || !items.length) {
    return "";
  }
  return `\n**参考材料**\n${items.map((item) => `- ${fileLink(item)}`).join("\n")}\n`;
}

function renderSlide(slide) {
  const visualLines = [...(slide.visualHints || [])];
  if (slide.placeholderItems?.length) {
    visualLines.push(
      ...slide.placeholderItems.map(
        (item) => `${item.title}：${item.desc} 参考 ${fileLink(item.source)}`,
      ),
    );
  }

  const noteLines = [...(slide.notes || [])];
  if (slide.callout) {
    noteLines.push(`${slide.callout.title}：${slide.callout.body}`);
  }

  return `## 第 ${slide.page} 页 ${slide.title}

**标题**

${slide.title}

**中心结论**

${slide.conclusion}

**要点**
${renderList(slide.points)}

**建议画面**
${renderList(visualLines)}

**讲者备注**
${renderList(noteLines)}
${renderSources(slide.sources)}`.trim();
}

const sections = slides.map(renderSlide).join("\n\n---\n\n");
const markdown = `# ${meta.title}

## 使用说明
- 受众：${meta.audience}
- 时长：${meta.duration}
- 形式：16 页讲稿式 Markdown，可直接转 PPT
- 视觉方向：${meta.style}
- 主线：背景边界 -> 工具理念 -> 外网到内网流程 -> SDD / skills -> 智能报告系统案例 -> 多 agent 协作 -> 调教经验 -> demo 转交付件

---

${sections}
`;

const outputPath = path.resolve(__dirname, meta.markdownOutput);
fs.writeFileSync(outputPath, markdown, "utf8");
console.log(`Markdown synced to ${outputPath}`);
