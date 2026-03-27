"use strict";

const path = require("path");
const PptxGenJS = require("pptxgenjs");
const { warnIfSlideHasOverlaps, warnIfSlideElementsOutOfBounds } = require("./pptxgenjs_helpers/layout");
const { imageSizingCrop, imageSizingContain } = require("./pptxgenjs_helpers/image");
const { safeOuterShadow } = require("./pptxgenjs_helpers/util");
const { svgToDataUri } = require("./pptxgenjs_helpers/svg");
const { meta, slides } = require("./slides-data");

const pptx = new PptxGenJS();
const W = 13.333;
const H = 7.5;

const COLORS = {
  bg: "F5F7FB",
  panel: "FFFFFF",
  ink: "122033",
  text: "243447",
  muted: "5B6B7F",
  border: "D7E0EA",
  accent: "2F6FED",
  accentSoft: "EAF2FF",
  accentDeep: "1E4CB2",
  teal: "0F9FA8",
  tealSoft: "E8FAFB",
  amber: "C48B18",
  amberSoft: "FFF6DD",
  danger: "D9485F",
  dangerSoft: "FFEDEF",
  slate: "7C8DA1",
  line: "C4D1E0",
};

const FONTS = {
  head: "Microsoft YaHei UI",
  body: "Microsoft YaHei UI",
  mono: "Consolas",
};

pptx.layout = "LAYOUT_WIDE";
pptx.author = "OpenAI Codex";
pptx.company = "OpenAI";
pptx.subject = meta.title;
pptx.title = meta.title;
pptx.lang = "zh-CN";
pptx.theme = {
  headFontFace: FONTS.head,
  bodyFontFace: FONTS.body,
  lang: "zh-CN",
};

function addBackground(slide, section, page) {
  slide.background = { color: COLORS.bg };
  slide.addShape(pptx.ShapeType.ellipse, {
    x: 11.18,
    y: 0.06,
    w: 1.72,
    h: 1.72,
    line: { color: COLORS.accentSoft, transparency: 100 },
    fill: { color: COLORS.accentSoft, transparency: 38 },
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 0.62,
    y: 7.08,
    w: 12.1,
    h: 0,
    line: { color: COLORS.line, width: 1.1 },
  });
  addPill(slide, 0.62, 0.34, 1.35, 0.34, section, {
    fill: COLORS.accentSoft,
    line: COLORS.accentSoft,
    color: COLORS.accentDeep,
    fontSize: 10.5,
    bold: true,
  });
  slide.addText(String(page).padStart(2, "0"), {
    x: 12.0,
    y: 0.28,
    w: 0.7,
    h: 0.3,
    fontFace: FONTS.body,
    fontSize: 11,
    bold: true,
    color: COLORS.slate,
    align: "right",
    margin: 0,
  });
}

function addPill(slide, x, y, w, h, text, opts = {}) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: opts.line || COLORS.border, width: 1 },
    fill: { color: opts.fill || COLORS.panel },
  });
  slide.addText(text, {
    x,
    y: y + 0.02,
    w,
    h: h - 0.02,
    align: "center",
    valign: "mid",
    fontFace: FONTS.body,
    fontSize: opts.fontSize || 10,
    bold: Boolean(opts.bold),
    color: opts.color || COLORS.text,
    margin: 0,
  });
}

function addTitle(slide, title, conclusion) {
  slide.addText(title, {
    x: 0.62,
    y: 0.82,
    w: 8.4,
    h: 0.62,
    fontFace: FONTS.head,
    fontSize: 24,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 0.62,
    y: 1.47,
    w: 8.05,
    h: 0.86,
    rectRadius: 0.08,
    line: { color: "BCD0F8", width: 1.1 },
    fill: { color: COLORS.accentSoft },
    shadow: safeOuterShadow("7EA4F8", 0.08, 45, 2, 1),
  });
  slide.addShape(pptx.ShapeType.rect, {
    x: 0.62,
    y: 1.47,
    w: 0.12,
    h: 0.86,
    line: { color: COLORS.accent, transparency: 100 },
    fill: { color: COLORS.accent },
  });
  slide.addText(conclusion, {
    x: 0.86,
    y: 1.66,
    w: 7.55,
    h: 0.48,
    fontFace: FONTS.body,
    fontSize: 13,
    color: COLORS.text,
    bold: true,
    margin: 0,
    valign: "mid",
  });
}

function addPointCards(slide, points, x, y, w, cardH = 0.96, gap = 0.16) {
  points.forEach((point, index) => {
    const top = y + index * (cardH + gap);
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y: top,
      w,
      h: cardH,
      rectRadius: 0.06,
      line: { color: COLORS.border, width: 1 },
      fill: { color: COLORS.panel },
      shadow: safeOuterShadow("8AA4C7", 0.06, 45, 1.5, 1),
    });
    slide.addShape(pptx.ShapeType.ellipse, {
      x: x + 0.18,
      y: top + 0.22,
      w: 0.44,
      h: 0.44,
      line: { color: COLORS.accent, transparency: 100 },
      fill: { color: COLORS.accent },
    });
    slide.addText(String(index + 1), {
      x: x + 0.18,
      y: top + 0.255,
      w: 0.44,
      h: 0.16,
      fontFace: FONTS.body,
      fontSize: 10,
      bold: true,
      color: "FFFFFF",
      align: "center",
      margin: 0,
    });
    slide.addText(point, {
      x: x + 0.78,
      y: top + 0.2,
      w: w - 1.0,
      h: cardH - 0.26,
      fontFace: FONTS.body,
      fontSize: 12.5,
      color: COLORS.text,
      margin: 0,
      valign: "mid",
    });
  });
}

function addSectionFooter(slide, text) {
  slide.addText(text, {
    x: 0.65,
    y: 6.88,
    w: 10.8,
    h: 0.15,
    fontFace: FONTS.body,
    fontSize: 8.5,
    color: COLORS.slate,
    margin: 0,
  });
}

function iconSvg(kind) {
  const accent = "#2F6FED";
  const teal = "#0F9FA8";
  const ink = "#526173";
  if (kind === "code") {
    return `<svg width="180" height="120" viewBox="0 0 180 120"><rect x="18" y="18" width="144" height="84" rx="16" fill="#EFF5FF" stroke="${accent}" stroke-width="4"/><path d="M66 44 L44 60 L66 76" fill="none" stroke="${accent}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M114 44 L136 60 L114 76" fill="none" stroke="${accent}" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/><path d="M98 36 L82 84" fill="none" stroke="${teal}" stroke-width="6" stroke-linecap="round"/></svg>`;
  }
  if (kind === "git") {
    return `<svg width="180" height="120" viewBox="0 0 180 120"><rect x="18" y="18" width="144" height="84" rx="16" fill="#F7FAFD" stroke="${ink}" stroke-width="4"/><circle cx="54" cy="60" r="10" fill="${accent}"/><circle cx="90" cy="42" r="10" fill="${teal}"/><circle cx="126" cy="72" r="10" fill="${accent}"/><path d="M64 56 L80 46" stroke="${ink}" stroke-width="4"/><path d="M100 48 L116 68" stroke="${ink}" stroke-width="4"/></svg>`;
  }
  if (kind === "deliverable") {
    return `<svg width="180" height="120" viewBox="0 0 180 120"><rect x="22" y="20" width="56" height="74" rx="10" fill="#EFF5FF" stroke="${accent}" stroke-width="4"/><rect x="62" y="28" width="56" height="74" rx="10" fill="#FFFFFF" stroke="${ink}" stroke-width="4"/><rect x="102" y="36" width="56" height="74" rx="10" fill="#E8FAFB" stroke="${teal}" stroke-width="4"/></svg>`;
  }
  return `<svg width="180" height="120" viewBox="0 0 180 120"><rect x="18" y="18" width="144" height="84" rx="16" fill="#F7FAFD" stroke="${accent}" stroke-width="4"/><rect x="36" y="34" width="108" height="52" rx="10" fill="#FFFFFF" stroke="${ink}" stroke-width="3"/><path d="M36 44 H144" stroke="${accent}" stroke-width="3"/><circle cx="50" cy="39" r="3" fill="${accent}"/><circle cx="60" cy="39" r="3" fill="${teal}"/></svg>`;
}

function resolveAsset(source) {
  if (!source) {
    return source;
  }
  return path.isAbsolute(source) ? source : path.resolve(__dirname, source);
}

function getPanelTone(item) {
  if (item.kind === "doc" || item.kind === "plan" || item.kind === "deliverable") {
    return {
      fill: COLORS.tealSoft,
      line: COLORS.tealSoft,
      color: "0B5960",
    };
  }
  if (item.kind === "git") {
    return {
      fill: COLORS.amberSoft,
      line: COLORS.amberSoft,
      color: "7A5B14",
    };
  }
  return {
    fill: COLORS.accentSoft,
    line: COLORS.accentSoft,
    color: COLORS.accentDeep,
  };
}

function badgeWidth(text, min = 1.22, max = 1.94) {
  if (!text) {
    return min;
  }
  return Math.min(max, Math.max(min, 0.4 + text.length * 0.22));
}

function addPanelFrame(slide, x, y, w, h) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: COLORS.border, width: 1.1 },
    fill: { color: COLORS.panel },
    shadow: safeOuterShadow("8AA4C7", 0.05, 45, 1.2, 1),
  });
}

function addPanelBadge(slide, item, x, y) {
  const tone = getPanelTone(item);
  const label = item.badge || "真实材料";
  addPill(slide, x, y, badgeWidth(label), 0.3, label, {
    fill: tone.fill,
    line: tone.line,
    color: tone.color,
    fontSize: 8.8,
    bold: true,
  });
}

function addPanelSource(slide, text, x, y, w, compact = false) {
  if (!text) {
    return;
  }
  slide.addText(text, {
    x,
    y,
    w,
    h: compact ? 0.12 : 0.14,
    fontFace: FONTS.mono,
    fontSize: compact ? 7.1 : 7.4,
    color: COLORS.slate,
    margin: 0,
  });
}

function addImageCard(slide, item, x, y, w, h) {
  const imagePath = resolveAsset(item.path);
  const labelH = 0.24;
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.06,
    line: { color: COLORS.border, width: 0.9 },
    fill: { color: "FBFCFF" },
  });
  slide.addImage({
    path: imagePath,
    ...imageSizingCrop(imagePath, x + 0.06, y + 0.06, w - 0.12, h - labelH - 0.14),
  });
  slide.addText(item.label, {
    x: x + 0.08,
    y: y + h - labelH,
    w: w - 0.16,
    h: 0.14,
    fontFace: FONTS.body,
    fontSize: 8.8,
    bold: true,
    color: COLORS.text,
    align: "center",
    margin: 0,
  });
}

function addGalleryPanel(slide, item, x, y, w, h) {
  addPanelFrame(slide, x, y, w, h);
  addPanelBadge(slide, item, x + 0.18, y + 0.16);
  slide.addText(item.title, {
    x: x + 0.18,
    y: y + 0.54,
    w: w - 0.36,
    h: 0.22,
    fontFace: FONTS.head,
    fontSize: 13.4,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  if (item.desc) {
    slide.addText(item.desc, {
      x: x + 0.18,
      y: y + 0.8,
      w: w - 0.36,
      h: 0.22,
      fontFace: FONTS.body,
      fontSize: 9.7,
      color: COLORS.muted,
      margin: 0,
    });
  }

  const gallery = item.gallery || [];
  const top = item.desc ? y + 1.1 : y + 0.92;
  const footH = 0.18;
  const gap = 0.12;
  const cols = gallery.length <= 3 ? gallery.length : 2;
  const rows = Math.ceil(gallery.length / cols);
  const innerW = w - 0.36;
  const innerH = h - (top - y) - footH - 0.14;
  const cardW = (innerW - gap * (cols - 1)) / cols;
  const cardH = (innerH - gap * (rows - 1)) / rows;

  gallery.forEach((entry, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    addImageCard(
      slide,
      entry,
      x + 0.18 + col * (cardW + gap),
      top + row * (cardH + gap),
      cardW,
      cardH,
    );
  });

  addPanelSource(slide, item.sourceLabel || item.source, x + 0.18, y + h - 0.23, w - 0.36);
}

function addImagePanel(slide, item, x, y, w, h) {
  const imagePath = resolveAsset(item.imagePath);
  addPanelFrame(slide, x, y, w, h);
  addPanelBadge(slide, item, x + 0.18, y + 0.16);
  slide.addText(item.title, {
    x: x + 0.18,
    y: y + 0.54,
    w: w - 0.36,
    h: 0.24,
    fontFace: FONTS.head,
    fontSize: 13.2,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  if (item.desc) {
    slide.addText(item.desc, {
      x: x + 0.18,
      y: y + 0.8,
      w: w - 0.36,
      h: 0.26,
      fontFace: FONTS.body,
      fontSize: 9.5,
      color: COLORS.muted,
      margin: 0,
    });
  }
  const imageTop = item.desc ? y + 1.1 : y + 0.86;
  const imageH = h - (imageTop - y) - 0.34;
  slide.addImage({
    path: imagePath,
    ...imageSizingCrop(imagePath, x + 0.2, imageTop + 0.02, w - 0.4, imageH - 0.04),
  });
  addPanelSource(slide, item.sourceLabel || item.source, x + 0.18, y + h - 0.21, w - 0.36);
}

function addExcerptPanel(slide, item, x, y, w, h, compact = false) {
  addPanelFrame(slide, x, y, w, h);
  addPanelBadge(slide, item, x + 0.18, y + (compact ? 0.14 : 0.16));
  slide.addText(item.title, {
    x: x + 0.18,
    y: y + (compact ? 0.46 : 0.54),
    w: w - 0.36,
    h: compact ? 0.2 : 0.24,
    fontFace: FONTS.head,
    fontSize: compact ? 12.2 : 13.2,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  if (item.desc) {
    slide.addText(item.desc, {
      x: x + 0.18,
      y: y + (compact ? 0.7 : 0.8),
      w: w - 0.36,
      h: compact ? 0.18 : 0.24,
      fontFace: FONTS.body,
      fontSize: compact ? 8.8 : 9.4,
      color: COLORS.muted,
      margin: 0,
    });
  }
  const contentTop = item.desc ? y + (compact ? 0.98 : 1.08) : y + (compact ? 0.82 : 0.9);
  const contentH = h - (contentTop - y) - (compact ? 0.32 : 0.36);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: x + 0.18,
    y: contentTop,
    w: w - 0.36,
    h: contentH,
    rectRadius: 0.05,
    line: { color: item.mono ? "D5DEEA" : "DCE5ED", width: 0.8 },
    fill: { color: item.mono ? "F6F8FC" : "F8FBFD" },
  });
  slide.addText((item.excerpt || []).join("\n"), {
    x: x + 0.3,
    y: contentTop + 0.12,
    w: w - 0.6,
    h: contentH - 0.24,
    fontFace: item.mono ? FONTS.mono : FONTS.body,
    fontSize: compact ? (item.mono ? 7.6 : 8.2) : (item.mono ? 8.2 : 9.0),
    color: COLORS.text,
    margin: 0,
    valign: "top",
  });
  addPanelSource(slide, item.sourceLabel || item.source, x + 0.18, y + h - (compact ? 0.17 : 0.21), w - 0.36, compact);
}

function addPlaceholderPanel(slide, item, x, y, w, h) {
  if (item?.gallery?.length) {
    addGalleryPanel(slide, item, x, y, w, h);
    return;
  }
  if (item?.imagePath) {
    addImagePanel(slide, item, x, y, w, h);
    return;
  }
  if (item?.excerpt?.length) {
    addExcerptPanel(slide, item, x, y, w, h);
    return;
  }
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: "B7C8DE", width: 1.2, dash: "dash" },
    fill: { color: "FCFDFF" },
  });
  addPill(slide, x + 0.22, y + 0.18, 1.56, 0.32, "案例占位区", {
    fill: COLORS.accentSoft,
    line: COLORS.accentSoft,
    color: COLORS.accentDeep,
    fontSize: 9.5,
    bold: true,
  });
  slide.addImage({
    data: svgToDataUri(iconSvg(item.kind)),
    x: x + 0.28,
    y: y + 0.7,
    w: 1.38,
    h: 0.92,
  });
  slide.addText(item.title, {
    x: x + 1.86,
    y: y + 0.72,
    w: w - 2.12,
    h: 0.28,
    fontFace: FONTS.head,
    fontSize: 14,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(item.desc, {
    x: x + 1.86,
    y: y + 1.08,
    w: w - 2.12,
    h: 0.82,
    fontFace: FONTS.body,
    fontSize: 11.5,
    color: COLORS.muted,
    margin: 0,
    valign: "top",
  });
  slide.addShape(pptx.ShapeType.roundRect, {
    x: x + 0.22,
    y: y + h - 0.6,
    w: w - 0.44,
    h: 0.38,
    rectRadius: 0.06,
    line: { color: COLORS.border, width: 0.8 },
    fill: { color: "F2F6FB" },
  });
  slide.addText(`建议替换素材：${item.source}`, {
    x: x + 0.34,
    y: y + h - 0.51,
    w: w - 0.66,
    h: 0.18,
    fontFace: FONTS.mono,
    fontSize: 8.2,
    color: COLORS.slate,
    margin: 0,
  });
}

function addCompactPlaceholderPanel(slide, item, x, y, w, h) {
  if (item?.excerpt?.length) {
    addExcerptPanel(slide, item, x, y, w, h, true);
    return;
  }
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h,
    rectRadius: 0.08,
    line: { color: "B7C8DE", width: 1.1, dash: "dash" },
    fill: { color: "FCFDFF" },
  });
  addPill(slide, x + 0.16, y + 0.16, 1.2, 0.28, "交付占位", {
    fill: COLORS.tealSoft,
    line: COLORS.tealSoft,
    color: "0B5960",
    fontSize: 8.8,
    bold: true,
  });
  slide.addText(item.title, {
    x: x + 0.18,
    y: y + 0.56,
    w: w - 0.36,
    h: 0.22,
    fontFace: FONTS.head,
    fontSize: 12.5,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(item.desc, {
    x: x + 0.18,
    y: y + 0.86,
    w: w - 0.36,
    h: 0.48,
    fontFace: FONTS.body,
    fontSize: 10.2,
    color: COLORS.muted,
    margin: 0,
  });
  slide.addText(`素材来源：${item.source}`, {
    x: x + 0.18,
    y: y + h - 0.28,
    w: w - 0.36,
    h: 0.14,
    fontFace: FONTS.mono,
    fontSize: 7.7,
    color: COLORS.slate,
    margin: 0,
  });
}

function addCallout(slide, callout, x, y, w) {
  const tone = callout.tone === "warning"
    ? { fill: COLORS.amberSoft, line: COLORS.amber, title: COLORS.amber, body: "7A5B14" }
    : callout.tone === "info"
    ? { fill: COLORS.tealSoft, line: COLORS.teal, title: COLORS.teal, body: "0B5960" }
    : { fill: COLORS.dangerSoft, line: COLORS.danger, title: COLORS.danger, body: "8B2E3E" };
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.86,
    rectRadius: 0.08,
    line: { color: tone.line, width: 1 },
    fill: { color: tone.fill },
  });
  slide.addText(callout.title, {
    x: x + 0.2,
    y: y + 0.14,
    w: w - 0.4,
    h: 0.2,
    fontFace: FONTS.body,
    fontSize: 11,
    bold: true,
    color: tone.title,
    margin: 0,
  });
  slide.addText(callout.body, {
    x: x + 0.2,
    y: y + 0.36,
    w: w - 0.4,
    h: 0.34,
    fontFace: FONTS.body,
    fontSize: 10.8,
    color: tone.body,
    margin: 0,
  });
}

function addFlowRow(slide, steps, x, y, w, h, tone = "accent") {
  const gap = 0.16;
  const itemW = (w - gap * (steps.length - 1)) / steps.length;
  steps.forEach((step, index) => {
    const left = x + index * (itemW + gap);
    slide.addShape(pptx.ShapeType.roundRect, {
      x: left,
      y,
      w: itemW,
      h,
      rectRadius: 0.07,
      line: { color: tone === "teal" ? "98D7DB" : "C3D6FB", width: 1.1 },
      fill: { color: tone === "teal" ? COLORS.tealSoft : COLORS.accentSoft },
    });
    slide.addText(step, {
      x: left + 0.16,
      y: y + 0.19,
      w: itemW - 0.32,
      h: h - 0.32,
      fontFace: FONTS.body,
      fontSize: 11.5,
      bold: true,
      align: "center",
      valign: "mid",
      color: tone === "teal" ? "0B5960" : COLORS.accentDeep,
      margin: 0,
    });
    if (index < steps.length - 1) {
      slide.addShape(pptx.ShapeType.line, {
        x: left + itemW,
        y: y + h / 2,
        w: gap,
        h: 0,
        line: { color: COLORS.slate, width: 1.3, endArrowType: "triangle" },
      });
    }
  });
}

function addCompareColumns(slide, compare, x, y, w, h) {
  const gap = 0.22;
  const colW = (w - gap) / 2;
  [
    { title: compare.leftTitle, items: compare.leftItems, tone: "accent", x },
    { title: compare.rightTitle, items: compare.rightItems, tone: "teal", x: x + colW + gap },
  ].forEach((column) => {
    slide.addShape(pptx.ShapeType.roundRect, {
      x: column.x,
      y,
      w: colW,
      h,
      rectRadius: 0.08,
      line: { color: COLORS.border, width: 1 },
      fill: { color: COLORS.panel },
    });
    addPill(slide, column.x + 0.2, y + 0.2, 1.5, 0.34, column.title, {
      fill: column.tone === "teal" ? COLORS.tealSoft : COLORS.accentSoft,
      line: column.tone === "teal" ? COLORS.tealSoft : COLORS.accentSoft,
      color: column.tone === "teal" ? "0B5960" : COLORS.accentDeep,
      bold: true,
      fontSize: 9.5,
    });
    column.items.forEach((item, idx) => {
      slide.addShape(pptx.ShapeType.ellipse, {
        x: column.x + 0.24,
        y: y + 0.74 + idx * 0.57,
        w: 0.16,
        h: 0.16,
        line: { color: column.tone === "teal" ? COLORS.teal : COLORS.accent, transparency: 100 },
        fill: { color: column.tone === "teal" ? COLORS.teal : COLORS.accent },
      });
      slide.addText(item, {
        x: column.x + 0.48,
        y: y + 0.68 + idx * 0.57,
        w: colW - 0.72,
        h: 0.24,
        fontFace: FONTS.body,
        fontSize: 11.5,
        color: COLORS.text,
        margin: 0,
      });
    });
  });
}

function addAgentCards(slide, items, x, y, w, h) {
  const gap = 0.2;
  const colW = (w - gap * (items.length - 1)) / items.length;
  items.forEach((item, idx) => {
    const left = x + idx * (colW + gap);
    slide.addShape(pptx.ShapeType.roundRect, {
      x: left,
      y,
      w: colW,
      h,
      rectRadius: 0.08,
      line: { color: COLORS.border, width: 1 },
      fill: { color: COLORS.panel },
      shadow: safeOuterShadow("8AA4C7", 0.05, 45, 1.5, 1),
    });
    addPill(slide, left + 0.18, y + 0.18, 1.12, 0.32, item.name, {
      fill: idx === 1 ? COLORS.tealSoft : COLORS.accentSoft,
      line: idx === 1 ? COLORS.tealSoft : COLORS.accentSoft,
      color: idx === 1 ? "0B5960" : COLORS.accentDeep,
      fontSize: 9.5,
      bold: true,
    });
    slide.addText(item.role, {
      x: left + 0.18,
      y: y + 0.58,
      w: colW - 0.36,
      h: 0.32,
      fontFace: FONTS.head,
      fontSize: 14,
      bold: true,
      color: COLORS.ink,
      margin: 0,
    });
    slide.addText(item.detail, {
      x: left + 0.18,
      y: y + 1.02,
      w: colW - 0.36,
      h: h - 1.22,
      fontFace: FONTS.body,
      fontSize: 11.2,
      color: COLORS.text,
      margin: 0,
      valign: "top",
    });
  });
}

function addCommitList(slide, items, x, y, w) {
  items.forEach((item, idx) => {
    const top = y + idx * 0.44;
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y: top,
      w,
      h: 0.34,
      rectRadius: 0.04,
      line: { color: COLORS.border, width: 0.8 },
      fill: { color: idx % 2 === 0 ? "F8FAFD" : COLORS.panel },
    });
    slide.addText(item, {
      x: x + 0.16,
      y: top + 0.08,
      w: w - 0.32,
      h: 0.18,
      fontFace: FONTS.mono,
      fontSize: 8.8,
      color: COLORS.text,
      margin: 0,
    });
  });
}

function addSourceLinks(slide, sources) {
  if (!sources?.length) {
    return;
  }
  slide.addText(`材料来源：${sources.join("  |  ")}`, {
    x: 0.65,
    y: 6.6,
    w: 12.0,
    h: 0.18,
    fontFace: FONTS.mono,
    fontSize: 7.6,
    color: COLORS.slate,
    margin: 0,
  });
}

function renderHero(slide, data) {
  slide.addText("需求分析设计 / Coding Agent / 智能报告系统", {
    x: 0.65,
    y: 2.48,
    w: 6.4,
    h: 0.18,
    fontFace: FONTS.body,
    fontSize: 10.5,
    color: COLORS.slate,
    margin: 0,
  });
  slide.addText(data.title, {
    x: 0.62,
    y: 2.72,
    w: 7.4,
    h: 0.86,
    fontFace: FONTS.head,
    fontSize: 28,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  slide.addText(data.conclusion, {
    x: 0.65,
    y: 3.72,
    w: 6.72,
    h: 0.9,
    fontFace: FONTS.body,
    fontSize: 14,
    color: COLORS.text,
    margin: 0,
  });
  let chipX = 0.65;
  for (const tag of data.tags || []) {
    addPill(slide, chipX, 4.82, 1.58, 0.36, tag, {
      fill: COLORS.panel,
      line: COLORS.border,
      color: COLORS.text,
      fontSize: 9.5,
    });
    chipX += 1.72;
  }
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 8.25,
    y: 2.15,
    w: 4.34,
    h: 3.02,
    rectRadius: 0.09,
    line: { color: COLORS.border, width: 1.2 },
    fill: { color: COLORS.panel },
    shadow: safeOuterShadow("8AA4C7", 0.08, 45, 2, 1),
  });
  slide.addText("分享主线", {
    x: 8.55,
    y: 2.45,
    w: 1.2,
    h: 0.2,
    fontFace: FONTS.body,
    fontSize: 10,
    color: COLORS.slate,
    margin: 0,
  });
  addFlowRow(slide, ["背景边界", "工具理念", "外网到内网", "案例证据"], 8.52, 2.85, 3.78, 0.58);
  addFlowRow(slide, ["多 agent 协作", "调教经验", "demo 转交付件"], 8.92, 3.78, 3.0, 0.58, "teal");
  addSectionFooter(slide, `${meta.audience} · ${meta.duration} · ${meta.style}`);
}

function renderCompare(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 5.65, 0.94);
  addCompareColumns(slide, data.compare, 6.6, 2.55, 6.06, 2.62);
  addSectionFooter(slide, "观点优先，边界先行，避免对 agent 产生错误预期。");
}

function renderSplitDiagram(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 5.7, 0.94);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.72,
    y: 2.55,
    w: 5.9,
    h: 2.84,
    rectRadius: 0.08,
    line: { color: COLORS.border, width: 1 },
    fill: { color: COLORS.panel },
  });
  slide.addText("为什么没有代码编辑区？", {
    x: 6.98,
    y: 2.78,
    w: 3.4,
    h: 0.24,
    fontFace: FONTS.head,
    fontSize: 15,
    bold: true,
    color: COLORS.ink,
    margin: 0,
  });
  addFlowRow(slide, data.diagramSteps, 6.98, 3.34, 5.1, 0.56);
  slide.addText("重点不是让人盯着代码逐行编辑，而是让 agent 先理解任务、环境、工具和验证方式，再决定如何执行。", {
    x: 6.98,
    y: 4.2,
    w: 5.0,
    h: 0.9,
    fontFace: FONTS.body,
    fontSize: 11.5,
    color: COLORS.text,
    margin: 0,
  });
  addSectionFooter(slide, "Codex 是会读环境、调工具、做验证的 agent，不是传统在线 IDE。");
}

function renderCards(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 5.48, 0.94);
  const cards = data.valueCards || [];
  const cols = cards.length > 4 ? 3 : 2;
  const cardW = 2.02;
  const cardH = 1.0;
  const startX = 6.64;
  const startY = 2.55;
  const gapX = 0.18;
  const gapY = 0.18;
  cards.forEach((card, index) => {
    const col = index % cols;
    const row = Math.floor(index / cols);
    const x = startX + col * (cardW + gapX);
    const y = startY + row * (cardH + gapY);
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y,
      w: cardW,
      h: cardH,
      rectRadius: 0.06,
      line: { color: index % 2 ? "CFE2E7" : "C3D6FB", width: 1 },
      fill: { color: index % 2 ? COLORS.tealSoft : COLORS.accentSoft },
    });
    slide.addText(card, {
      x: x + 0.18,
      y: y + 0.28,
      w: cardW - 0.36,
      h: 0.34,
      fontFace: FONTS.body,
      fontSize: 12.4,
      bold: true,
      color: index % 2 ? "0B5960" : COLORS.accentDeep,
      align: "center",
      margin: 0,
    });
  });
  addSectionFooter(slide, "输入越完整，agent 产出的第一轮质量越高。");
}

function renderTimeline(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 5.3, 0.94);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 6.3,
    y: 2.55,
    w: 6.32,
    h: 2.05,
    rectRadius: 0.08,
    line: { color: COLORS.border, width: 1 },
    fill: { color: COLORS.panel },
  });
  addFlowRow(slide, data.flowSteps, 6.58, 3.18, 5.75, 0.66);
  slide.addText("推荐路径", {
    x: 6.58,
    y: 2.82,
    w: 1.1,
    h: 0.2,
    fontFace: FONTS.body,
    fontSize: 10,
    color: COLORS.slate,
    margin: 0,
  });
  if (data.callout) {
    addCallout(slide, data.callout, 6.3, 4.78, 6.32);
  }
  addSectionFooter(slide, "企业环境里，流程设计必须与安全边界一起考虑。");
}

function renderStack(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 5.55, 0.94);
  const items = data.stackItems || [];
  const baseX = 7.2;
  const baseY = 5.4;
  items.forEach((item, idx) => {
    const width = 4.4 - idx * 0.4;
    const x = baseX - (width - 3.2) / 2;
    const y = baseY - idx * 0.55;
    slide.addShape(pptx.ShapeType.roundRect, {
      x,
      y,
      w: width,
      h: 0.45,
      rectRadius: 0.05,
      line: { color: idx % 2 ? "CFE2E7" : "C3D6FB", width: 1 },
      fill: { color: idx % 2 ? COLORS.tealSoft : COLORS.accentSoft },
    });
    slide.addText(item, {
      x,
      y: y + 0.1,
      w: width,
      h: 0.18,
      align: "center",
      fontFace: FONTS.body,
      fontSize: 11,
      bold: true,
      color: idx % 2 ? "0B5960" : COLORS.accentDeep,
      margin: 0,
    });
  });
  addSectionFooter(slide, "设计上下文不该只停留在设计会议里，而应该成为后续开发共享的输入。");
}

function renderSplitPlaceholder(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  if (data.commitItems?.length) {
    addPointCards(slide, data.points, 0.66, 2.55, 5.4, 0.72, 0.12);
  } else {
    addPointCards(slide, data.points, 0.66, 2.55, 5.4, 0.94);
  }
  addPlaceholderPanel(slide, data.placeholderItems[0], 6.36, 2.55, 6.28, 2.9);
  if (data.commitItems?.length) {
    addCommitList(slide, data.commitItems, 0.78, 5.12, 5.18);
  }
  addSourceLinks(slide, data.sources);
}

function renderWorkflow(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 4.9, 0.94);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 5.92,
    y: 2.55,
    w: 6.7,
    h: 2.9,
    rectRadius: 0.08,
    line: { color: COLORS.border, width: 1 },
    fill: { color: COLORS.panel },
  });
  addFlowRow(slide, data.flowSteps, 6.16, 3.16, 6.18, 0.68);
  slide.addText("人负责判断与取舍", {
    x: 6.22,
    y: 4.28,
    w: 2.0,
    h: 0.18,
    fontFace: FONTS.body,
    fontSize: 10.5,
    bold: true,
    color: COLORS.accentDeep,
    margin: 0,
  });
  slide.addText("agent 负责落地与验证", {
    x: 9.76,
    y: 4.28,
    w: 2.1,
    h: 0.18,
    fontFace: FONTS.body,
    fontSize: 10.5,
    bold: true,
    color: "0B5960",
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.line, {
    x: 8.45,
    y: 4.36,
    w: 1.1,
    h: 0,
    line: { color: COLORS.slate, width: 1.2, endArrowType: "triangle" },
  });
  addSectionFooter(slide, "目标不是得到一段代码，而是得到一条可复用的原型生产线。");
}

function renderDualPlaceholder(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 4.62, 0.94);
  addPlaceholderPanel(slide, data.placeholderItems[0], 5.62, 2.55, 3.38, 3.05);
  addPlaceholderPanel(slide, data.placeholderItems[1], 9.2, 2.55, 3.38, 3.05);
  addSourceLinks(slide, data.sources);
}

function renderTrio(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 4.8, 0.94);
  addAgentCards(slide, data.agentCards, 5.78, 2.55, 6.82, 2.82);
  addSectionFooter(slide, "同一阶段不必只押一个 agent，关键是清楚谁负责什么。");
}

function renderDelivery(slide, data) {
  addTitle(slide, data.title, data.conclusion);
  addPointCards(slide, data.points, 0.66, 2.55, 4.9, 0.94);
  slide.addShape(pptx.ShapeType.roundRect, {
    x: 5.92,
    y: 2.55,
    w: 6.72,
    h: 1.56,
    rectRadius: 0.08,
    line: { color: COLORS.border, width: 1 },
    fill: { color: COLORS.panel },
  });
  addFlowRow(slide, data.flowSteps, 6.16, 3.0, 6.22, 0.64, "teal");
  addCompactPlaceholderPanel(slide, data.placeholderItems[0], 5.92, 4.28, 3.98, 1.9);
  addCallout(slide, data.callout, 10.1, 4.44, 2.52);
  addSectionFooter(slide, "先原型，后工程化；先对齐上下文，再交付版本。");
}

function renderSlide(slide, data) {
  addBackground(slide, data.section, data.page);
  switch (data.layout) {
    case "hero":
      renderHero(slide, data);
      break;
    case "compare":
      renderCompare(slide, data);
      break;
    case "split-diagram":
      renderSplitDiagram(slide, data);
      break;
    case "cards":
      renderCards(slide, data);
      break;
    case "timeline":
      renderTimeline(slide, data);
      break;
    case "stack":
      renderStack(slide, data);
      break;
    case "split-placeholder":
      renderSplitPlaceholder(slide, data);
      break;
    case "workflow":
      renderWorkflow(slide, data);
      break;
    case "dual-placeholder":
      renderDualPlaceholder(slide, data);
      break;
    case "trio":
      renderTrio(slide, data);
      break;
    case "delivery":
      renderDelivery(slide, data);
      break;
    default:
      addTitle(slide, data.title, data.conclusion);
      addPointCards(slide, data.points, 0.66, 2.55, 5.5, 0.94);
      break;
  }
  warnIfSlideHasOverlaps(slide, pptx, { ignoreDecorativeShapes: true, muteContainment: true });
  warnIfSlideElementsOutOfBounds(slide, pptx);
}

async function main() {
  for (const data of slides) {
    const slide = pptx.addSlide();
    renderSlide(slide, data);
  }
  const outputPath = path.resolve(__dirname, meta.deckOutput);
  await pptx.writeFile({ fileName: outputPath });
  console.log(`Deck written to ${outputPath}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
