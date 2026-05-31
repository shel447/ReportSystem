package com.chatbi.exporter.conf;

/**
 * PPT 文本框配置。
 */
public record PptTextBoxConfiguration(
        boolean showBorder
) {
    public static PptTextBoxConfiguration defaults() {
        return new PptTextBoxConfiguration(false);
    }
}
