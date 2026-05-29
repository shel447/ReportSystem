package com.chatbi.exporter.conf;

/**
 * PPT 母版页眉/页脚配置。
 */
public record PptMasterConfiguration(
        boolean showAccentLines
) {
    public static PptMasterConfiguration defaults() {
        return new PptMasterConfiguration(false);
    }
}
