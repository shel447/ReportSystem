package com.chatbi.exporter.style;

import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.model.VDoc;

import java.awt.Color;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 默认主题解析器。
 * <p>
 * 解析优先级：
 * 1) ExportRequest.themeOverride
 * 2) VDoc.themeId
 * 3) root.props.themeId
 * 4) 默认 enterprise-light
 *
 * 同时支持 root.props.theme 局部覆盖颜色/字体/调色板。
 * </p>
 */
public class DefaultStyleResolver implements StyleResolver {
    /**
     * 解析最终主题令牌。
     */
    @Override
    public ThemeTokens resolve(VDoc doc, ExportRequest request) {
        ExportRequest safeRequest = request == null ? ExportRequest.defaults() : request;
        String resolvedThemeId = normalizeThemeId(doc, safeRequest);
        ThemeTokens base = switch (resolvedThemeId) {
            case "enterprise-dark" -> darkTheme();
            case "ocean-contrast" -> oceanTheme();
            default -> lightTheme();
        };

        Map<String, Object> themeOverrides = resolveThemeOverrideMap(doc);
        if (themeOverrides.isEmpty()) {
            return base;
        }

        return new ThemeTokens(
                base.id(),
                str(themeOverrides.get("fontPrimary"), base.fontPrimary()),
                str(themeOverrides.get("fontMono"), base.fontMono()),
                parseColor(themeOverrides.get("canvas"), base.canvas()),
                parseColor(themeOverrides.get("panel"), base.panel()),
                parseColor(themeOverrides.get("panelAlt"), base.panelAlt()),
                parseColor(themeOverrides.get("border"), base.border()),
                parseColor(themeOverrides.get("text"), base.text()),
                parseColor(themeOverrides.get("muted"), base.muted()),
                parseColor(themeOverrides.get("primary"), base.primary()),
                parseColor(themeOverrides.get("primarySoft"), base.primarySoft()),
                parsePalette(themeOverrides.get("palette"), base.palette())
        );
    }

    /**
     * 统一解析主题 ID，避免多端大小写与空白不一致。
     */
    private String normalizeThemeId(VDoc doc, ExportRequest request) {
        if (doc == null) {
            return "enterprise-light";
        }
        if (request.themeOverride() != null && !request.themeOverride().isBlank()) {
            return request.themeOverride().trim().toLowerCase();
        }
        if (doc.themeId != null && !doc.themeId.isBlank()) {
            return doc.themeId.trim().toLowerCase();
        }
        if (doc.root != null) {
            String fromRoot = doc.root.propString("themeId", "");
            if (!fromRoot.isBlank()) {
                return fromRoot.trim().toLowerCase();
            }
        }
        return "enterprise-light";
    }

    /**
     * 从 DSL 中读取主题覆盖对象（若存在）。
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> resolveThemeOverrideMap(VDoc doc) {
        if (doc == null || doc.root == null) {
            return Collections.emptyMap();
        }
        Object raw = doc.root.propsOrEmpty().get("theme");
        if (raw instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Collections.emptyMap();
    }

    /**
     * 企业浅色主题默认值。
     */
    private ThemeTokens lightTheme() {
        return new ThemeTokens(
                "enterprise-light",
                "Source Sans 3",
                "Consolas",
                VisualStyle.color("#ffffff"),
                VisualStyle.color("#ffffff"),
                VisualStyle.color("#f8fbff"),
                VisualStyle.color("#d9e2f2"),
                VisualStyle.color("#1f2937"),
                VisualStyle.color("#6b7280"),
                VisualStyle.color("#1d4ed8"),
                VisualStyle.color("#dbeafe"),
                VisualStyle.palette("#1d4ed8", "#0ea5e9", "#14b8a6", "#22c55e", "#f59e0b", "#ef4444")
        );
    }

    /**
     * 企业深色主题默认值。
     */
    private ThemeTokens darkTheme() {
        return new ThemeTokens(
                "enterprise-dark",
                "Source Sans 3",
                "Consolas",
                VisualStyle.color("#0f172a"),
                VisualStyle.color("#111827"),
                VisualStyle.color("#1f2937"),
                VisualStyle.color("#334155"),
                VisualStyle.color("#e5e7eb"),
                VisualStyle.color("#94a3b8"),
                VisualStyle.color("#38bdf8"),
                VisualStyle.color("#0c4a6e"),
                VisualStyle.palette("#38bdf8", "#22d3ee", "#2dd4bf", "#4ade80", "#facc15", "#f97316")
        );
    }

    /**
     * 高对比海洋主题默认值。
     */
    private ThemeTokens oceanTheme() {
        return new ThemeTokens(
                "ocean-contrast",
                "Source Sans 3",
                "Consolas",
                VisualStyle.color("#f0f9ff"),
                VisualStyle.color("#ffffff"),
                VisualStyle.color("#ecfeff"),
                VisualStyle.color("#bae6fd"),
                VisualStyle.color("#0c4a6e"),
                VisualStyle.color("#0369a1"),
                VisualStyle.color("#0284c7"),
                VisualStyle.color("#bae6fd"),
                VisualStyle.palette("#0284c7", "#06b6d4", "#14b8a6", "#10b981", "#84cc16", "#f59e0b")
        );
    }

    private String str(Object value, String fallback) {
        return value == null ? fallback : String.valueOf(value);
    }

    /**
     * 颜色容错解析，失败时回退到 fallback。
     */
    private Color parseColor(Object raw, Color fallback) {
        if (raw == null) {
            return fallback;
        }
        String value = String.valueOf(raw);
        if (value.isBlank()) {
            return fallback;
        }
        try {
            return VisualStyle.color(value);
        } catch (RuntimeException ignored) {
            return fallback;
        }
    }

    /**
     * 调色板容错解析，忽略非法颜色项。
     */
    @SuppressWarnings("unchecked")
    private List<Color> parsePalette(Object raw, List<Color> fallback) {
        if (!(raw instanceof List<?> list)) {
            return fallback;
        }
        List<Color> result = new ArrayList<>();
        for (Object item : list) {
            try {
                result.add(VisualStyle.color(String.valueOf(item)));
            } catch (RuntimeException ignored) {
                // ignore invalid color item
            }
        }
        if (result.isEmpty()) {
            return fallback;
        }
        return Collections.unmodifiableList(result);
    }
}
