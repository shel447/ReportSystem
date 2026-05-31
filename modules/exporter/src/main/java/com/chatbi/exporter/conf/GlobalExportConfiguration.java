package com.chatbi.exporter.conf;

/**
 * 不区分文档类型的通用导出配置。
 */
public record GlobalExportConfiguration(
        String themeOverride,
        boolean strictValidation
) {
    public static GlobalExportConfiguration defaults() {
        return new GlobalExportConfiguration(null, false);
    }
}
