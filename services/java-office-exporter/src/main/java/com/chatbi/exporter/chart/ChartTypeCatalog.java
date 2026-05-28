package com.chatbi.exporter.chart;

import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.Locale;
import java.util.Set;

/**
 * 图表类型目录。
 * <p>
 * 维护与 Web 编辑器一致的 chartType 枚举，
 * 供校验与渲染映射共用。
 * </p>
 */
public final class ChartTypeCatalog {
    private static final Set<String> WEB_TYPES;

    static {
        LinkedHashSet<String> types = new LinkedHashSet<>();
        types.add("auto");
        types.add("line");
        types.add("bar");
        types.add("pie");
        types.add("scatter");
        types.add("radar");
        types.add("heatmap");
        types.add("kline");
        types.add("boxplot");
        types.add("sankey");
        types.add("graph");
        types.add("treemap");
        types.add("sunburst");
        types.add("parallel");
        types.add("funnel");
        types.add("gauge");
        types.add("calendar");
        types.add("custom");
        types.add("combo");
        WEB_TYPES = Collections.unmodifiableSet(types);
    }

    private ChartTypeCatalog() {
    }

    /**
     * @return Web 端支持的图表类型集合
     */
    public static Set<String> webTypes() {
        return WEB_TYPES;
    }

    /**
     * 标准化 chartType，空值回退到 line。
     */
    public static String normalize(String chartType) {
        if (chartType == null || chartType.isBlank()) {
            return "line";
        }
        return chartType.trim().toLowerCase(Locale.ROOT);
    }

    /**
     * 判断是否为 Web 支持类型（兼容 auto 原始值）。
     */
    public static boolean isWebChartType(String chartType) {
        return WEB_TYPES.contains(normalize(chartType)) || "auto".equalsIgnoreCase(chartType);
    }
}
