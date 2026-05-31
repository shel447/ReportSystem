package com.chatbi.exporter.conf;

/**
 * Word 表格配置。
 */
public record WordTableConfiguration(
        boolean fitToPage,
        boolean repeatHeaderOnPageBreak,
        String emptyText,
        TableHeaderBackground headerBackground
) {
    public WordTableConfiguration {
        emptyText = emptyText == null || emptyText.isBlank() ? "无数据" : emptyText;
        headerBackground = headerBackground == null ? TableHeaderBackground.THEME_PRIMARY_SOFT : headerBackground;
    }

    public static WordTableConfiguration defaults() {
        return new WordTableConfiguration(true, false, "无数据", TableHeaderBackground.THEME_PRIMARY_SOFT);
    }
}
