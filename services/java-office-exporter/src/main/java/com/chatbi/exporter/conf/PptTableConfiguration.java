package com.chatbi.exporter.conf;

/**
 * PPT 表格默认配置。
 */
public record PptTableConfiguration(
        boolean fitToSlide,
        int safeMarginPx,
        double preferredRowHeightPx,
        double minRowHeightPx,
        double maxRowHeightPx,
        double headerFontSize,
        double bodyFontSize,
        double cellInsetPt
) {
    public PptTableConfiguration {
        safeMarginPx = Math.max(0, safeMarginPx);
        preferredRowHeightPx = positive(preferredRowHeightPx, 18.0);
        minRowHeightPx = positive(minRowHeightPx, 14.0);
        maxRowHeightPx = Math.max(minRowHeightPx, positive(maxRowHeightPx, 20.0));
        headerFontSize = positive(headerFontSize, 7.5);
        bodyFontSize = positive(bodyFontSize, 6.5);
        cellInsetPt = Math.max(0.0, cellInsetPt);
    }

    public static PptTableConfiguration defaults() {
        return new PptTableConfiguration(true, 24, 18.0, 14.0, 20.0, 7.5, 6.5, 1.5);
    }

    private static double positive(double value, double fallback) {
        return value > 0.0 ? value : fallback;
    }
}
