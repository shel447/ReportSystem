package com.bi.report.generation.style;

public record ThemeTokens(
        String primary,
        String secondary,
        String accent,
        String fontPrimary,
        String fontSecondary,
        int titleSizePt,
        int heading1SizePt,
        int heading2SizePt,
        int heading3SizePt,
        int bodySizePt,
        int smallSizePt,
        int tableHeaderSizePt,
        String tableHeaderBg,
        String tableAltRowBg,
        String[] palette
) {
    public static ThemeTokens enterpriseLight() {
        return new ThemeTokens(
                "1d4ed8", "475569", "2563eb",
                "Microsoft YaHei", "Arial",
                22, 16, 14, 12, 11, 9, 10,
                "1d4ed8", "f1f5f9",
                new String[]{"1d4ed8", "2563eb", "3b82f6", "60a5fa", "93c5fd", "bfdbfe", "f59e0b", "10b981", "ef4444", "8b5cf6"}
        );
    }

    public static ThemeTokens enterpriseDark() {
        return new ThemeTokens(
                "60a5fa", "94a3b8", "3b82f6",
                "Microsoft YaHei", "Arial",
                22, 16, 14, 12, 11, 9, 10,
                "1e3a5f", "1e293b",
                new String[]{"60a5fa", "3b82f6", "2563eb", "93c5fd", "bfdbfe", "dbeafe", "fbbf24", "34d399", "f87171", "a78bfa"}
        );
    }
}
