package com.chatbi.exporter.core;

/**
 * 导出目标类型。
 */
public enum ExportTarget {
    DOCX,
    PPTX;

    /**
     * 解析命令行 target 参数。
     *
     * @param value 期望值：docx/pptx
     */
    public static ExportTarget fromCli(String value) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("Target is blank.");
        }
        String normalized = value.trim().toLowerCase();
        return switch (normalized) {
            case "docx" -> DOCX;
            case "pptx" -> PPTX;
            default -> throw new IllegalArgumentException("Unsupported target: " + value);
        };
    }
}
