package com.chatbi.exporter.chart;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 图表渲染数据集。
 * <p>
 * 结构：
 * - categories：类目轴（X）
 * - series：系列名 -> 数值序列
 * </p>
 */
public final class ChartDataset {
    private final String categoryLabel;
    private final List<String> categories;
    private final LinkedHashMap<String, List<Double>> series;

    /**
     * 构造不可变副本，避免调用方在渲染期间篡改数据。
     */
    public ChartDataset(String categoryLabel, List<String> categories, LinkedHashMap<String, List<Double>> series) {
        this.categoryLabel = categoryLabel;
        this.categories = categories == null ? Collections.emptyList() : List.copyOf(categories);
        this.series = series == null ? new LinkedHashMap<>() : new LinkedHashMap<>(series);
    }

    public String categoryLabel() {
        return categoryLabel;
    }

    public List<String> categories() {
        return categories;
    }

    public LinkedHashMap<String, List<Double>> series() {
        return new LinkedHashMap<>(series);
    }

    /**
     * @return 是否存在类目
     */
    public boolean hasCategories() {
        return !categories.isEmpty();
    }

    /**
     * @return 是否存在至少一个系列
     */
    public boolean hasSeries() {
        return !series.isEmpty();
    }

    /**
     * 判断数据是否可绘制。
     * 要求至少一个非空数值点，避免绘制空图。
     */
    public boolean isRenderable() {
        if (!hasCategories() || !hasSeries()) {
            return false;
        }
        for (List<Double> values : series.values()) {
            if (values == null || values.isEmpty()) {
                continue;
            }
            for (Double value : values) {
                if (value != null) {
                    return true;
                }
            }
        }
        return false;
    }

    /**
     * 将类目列表转换为 POI 接口需要的数组。
     */
    public String[] categoryArray() {
        return categories.toArray(String[]::new);
    }

    /**
     * 将 series 转为 `Map.Entry<name, Double[]>`，并按类目长度对齐。
     */
    public List<Map.Entry<String, Double[]>> seriesArrays() {
        List<Map.Entry<String, Double[]>> entries = new ArrayList<>();
        for (Map.Entry<String, List<Double>> entry : series.entrySet()) {
            Double[] values = new Double[categories.size()];
            for (int i = 0; i < categories.size(); i++) {
                Double value = i < entry.getValue().size() ? entry.getValue().get(i) : null;
                values[i] = value == null ? 0.0 : value;
            }
            entries.add(Map.entry(entry.getKey(), values));
        }
        return entries;
    }
}
