package com.chatbi.exporter.conf;

/**
 * PDF 导出配置占位对象。
 */
public record PdfExportConfiguration() {
    public static PdfExportConfiguration defaults() {
        return new PdfExportConfiguration();
    }
}
