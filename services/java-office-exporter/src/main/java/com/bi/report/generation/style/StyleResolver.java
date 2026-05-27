package com.bi.report.generation.style;

public final class StyleResolver {
    private final ThemeTokens tokens;

    public StyleResolver(String themeId) {
        this.tokens = resolve(themeId);
    }

    public ThemeTokens tokens() {
        return tokens;
    }

    private static ThemeTokens resolve(String themeId) {
        if (themeId == null) return ThemeTokens.enterpriseLight();
        return switch (themeId.trim().toLowerCase()) {
            case "enterprise-dark" -> ThemeTokens.enterpriseDark();
            default -> ThemeTokens.enterpriseLight();
        };
    }

    public static int hexToRgbInt(String hex) {
        String clean = hex.replace("#", "").trim();
        if (clean.length() == 6) {
            return Integer.parseInt(clean, 16);
        }
        return 0;
    }

    public static byte[] hexToRgb(String hex) {
        int rgb = hexToRgbInt(hex);
        return new byte[]{(byte) ((rgb >> 16) & 0xFF), (byte) ((rgb >> 8) & 0xFF), (byte) (rgb & 0xFF)};
    }
}
