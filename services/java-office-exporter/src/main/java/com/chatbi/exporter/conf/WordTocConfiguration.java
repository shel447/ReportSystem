package com.chatbi.exporter.conf;

/**
 * Word 静态目录配置。
 */
public record WordTocConfiguration(
        boolean enabled,
        double topOffsetRatio,
        boolean linkEnabled
) {
    public static WordTocConfiguration defaults() {
        return new WordTocConfiguration(true, 0.05, true);
    }
}
