package com.chatbi.exporter.table;

/**
 * 表格列定义。
 */
public record TableColumn(
        String key,
        String title,
        double width,
        String align,
        String format
) {
    /**
     * 统一列字段兜底与宽度下限，减少下游渲染分支。
     */
    public TableColumn {
        key = key == null ? "" : key;
        title = title == null || title.isBlank() ? key : title;
        width = Math.max(48.0, width);
        align = normalizeAlign(align);
        format = format == null ? "" : format;
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
