package com.chatbi.exporter.table;

/**
 * 表格单元格模型。
 * <p>
 * 通过 rowSpan/colSpan + hidden 实现“锚点单元格 + 被覆盖单元格”的合并表达，
 * 便于在 DOCX/PPTX 两端统一渲染策略。
 * </p>
 */
public record TableCell(
        String text,
        int rowSpan,
        int colSpan,
        String align,
        boolean header,
        boolean hidden
) {
    /**
     * 规范化字段，保证 span 最小为 1，align 合法。
     */
    public TableCell {
        text = text == null ? "" : text;
        rowSpan = Math.max(1, rowSpan);
        colSpan = Math.max(1, colSpan);
        align = normalizeAlign(align);
    }

    /**
     * 构造可见锚点单元格。
     */
    public static TableCell anchor(String text, String align, boolean header) {
        return new TableCell(text, 1, 1, align, header, false);
    }

    /**
     * 构造“被合并覆盖”的隐藏单元格占位。
     */
    public static TableCell hidden(String align, boolean header) {
        return new TableCell("", 1, 1, align, header, true);
    }

    /**
     * 返回新的跨行跨列锚点副本。
     */
    public TableCell withSpan(int rowSpan, int colSpan) {
        return new TableCell(text, rowSpan, colSpan, align, header, false);
    }

    private static String normalizeAlign(String raw) {
        if (raw == null) {
            return "left";
        }
        return switch (raw.toLowerCase()) {
            case "left", "center", "right" -> raw.toLowerCase();
            default -> "left";
        };
    }
}
