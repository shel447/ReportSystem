package com.chatbi.exporter.chart;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * ChartSpec -> ChartDataset 构建器。
 * <p>
 * 支持两种模式：
 * - 普通模式：每个 measure 一条序列
 * - 透视模式：按 seriesField 拆分序列（可叠加 measure）
 * </p>
 */
public final class ChartDatasetBuilder {
    /**
     * 默认使用 spec.sampleRows 构建。
     */
    public ChartDataset build(ChartSpec spec) {
        return build(spec, spec == null ? Collections.emptyList() : spec.sampleRows());
    }

    /**
     * 基于外部传入行数据构建图表数据集。
     */
    public ChartDataset build(ChartSpec spec, List<Map<String, Object>> rows) {
        if (spec == null || rows == null || rows.isEmpty()) {
            return new ChartDataset("", Collections.emptyList(), new LinkedHashMap<>());
        }

        String categoryField = blank(spec.dimensionField()) ? "__row__" : spec.dimensionField();
        List<String> categories = collectCategories(rows, categoryField);
        if (categories.isEmpty()) {
            return new ChartDataset(categoryField, Collections.emptyList(), new LinkedHashMap<>());
        }

        List<String> measures = resolveMeasures(spec, rows);
        if (measures.isEmpty()) {
            return new ChartDataset(categoryField, categories, new LinkedHashMap<>());
        }

        LinkedHashMap<String, List<Double>> series = blank(spec.seriesField())
                ? buildMeasureSeries(rows, categories, categoryField, measures)
                : buildPivotSeries(rows, categories, categoryField, spec.seriesField(), measures);

        return new ChartDataset(categoryField, categories, series);
    }

    /**
     * 提取类目轴，保持输入顺序且去重。
     */
    private List<String> collectCategories(List<Map<String, Object>> rows, String categoryField) {
        LinkedHashSet<String> categories = new LinkedHashSet<>();
        for (int i = 0; i < rows.size(); i++) {
            Map<String, Object> row = rows.get(i);
            String category = "__row__".equals(categoryField)
                    ? "Row " + (i + 1)
                    : asString(row.get(categoryField), "Row " + (i + 1));
            categories.add(category);
        }
        return new ArrayList<>(categories);
    }

    /**
     * 解析指标字段：
     * - 优先使用 spec.measureFields
     * - 否则从首行推断数值字段
     */
    private List<String> resolveMeasures(ChartSpec spec, List<Map<String, Object>> rows) {
        if (!spec.measureFields().isEmpty()) {
            return spec.measureFields();
        }
        if (rows.isEmpty()) {
            return Collections.emptyList();
        }
        Map<String, Object> first = rows.get(0);
        Set<String> excludes = new LinkedHashSet<>();
        excludes.add(spec.dimensionField());
        excludes.add(spec.seriesField());
        if (!blank(spec.secondAxisField())) {
            excludes.add(spec.secondAxisField());
        }

        List<String> inferred = new ArrayList<>();
        for (Map.Entry<String, Object> entry : first.entrySet()) {
            if (entry.getKey() == null || excludes.contains(entry.getKey())) {
                continue;
            }
            if (toDouble(entry.getValue()) != null) {
                inferred.add(entry.getKey());
            }
        }
        return inferred;
    }

    /**
     * 构建普通模式序列（measure -> values）。
     */
    private LinkedHashMap<String, List<Double>> buildMeasureSeries(
            List<Map<String, Object>> rows,
            List<String> categories,
            String categoryField,
            List<String> measures
    ) {
        LinkedHashMap<String, List<Double>> series = new LinkedHashMap<>();
        for (String measure : measures) {
            series.put(measure, zeroList(categories.size()));
        }

        Map<String, Integer> index = indexMap(categories);
        for (int i = 0; i < rows.size(); i++) {
            Map<String, Object> row = rows.get(i);
            String category = "__row__".equals(categoryField)
                    ? "Row " + (i + 1)
                    : asString(row.get(categoryField), "Row " + (i + 1));
            Integer position = index.get(category);
            if (position == null) {
                continue;
            }
            for (String measure : measures) {
                Double value = toDouble(row.get(measure));
                if (value != null) {
                    series.get(measure).set(position, value);
                }
            }
        }
        return series;
    }

    /**
     * 构建透视序列（seriesField + measure 组合）。
     */
    private LinkedHashMap<String, List<Double>> buildPivotSeries(
            List<Map<String, Object>> rows,
            List<String> categories,
            String categoryField,
            String seriesField,
            List<String> measures
    ) {
        LinkedHashMap<String, List<Double>> series = new LinkedHashMap<>();
        Map<String, Integer> index = indexMap(categories);

        for (int i = 0; i < rows.size(); i++) {
            Map<String, Object> row = rows.get(i);
            String category = "__row__".equals(categoryField)
                    ? "Row " + (i + 1)
                    : asString(row.get(categoryField), "Row " + (i + 1));
            Integer position = index.get(category);
            if (position == null) {
                continue;
            }
            String seriesKey = asString(row.get(seriesField), "Series");
            for (String measure : measures) {
                String name = measures.size() == 1 ? seriesKey : seriesKey + "/" + measure;
                List<Double> values = series.computeIfAbsent(name, ignored -> zeroList(categories.size()));
                Double value = toDouble(row.get(measure));
                if (value != null) {
                    values.set(position, value);
                }
            }
        }
        return series;
    }

    /**
     * 构建类目 -> 下标映射。
     */
    private Map<String, Integer> indexMap(List<String> categories) {
        LinkedHashMap<String, Integer> map = new LinkedHashMap<>();
        for (int i = 0; i < categories.size(); i++) {
            map.put(categories.get(i), i);
        }
        return map;
    }

    /**
     * 生成固定长度的 0 值数组，用于补齐缺失点。
     */
    private List<Double> zeroList(int size) {
        List<Double> values = new ArrayList<>(size);
        for (int i = 0; i < size; i++) {
            values.add(0.0);
        }
        return values;
    }

    /**
     * 容错转数值，失败返回 null。
     */
    private Double toDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String str) {
            try {
                return Double.parseDouble(str);
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    /**
     * 容错转字符串，为空时返回 fallback。
     */
    private String asString(Object value, String fallback) {
        if (value == null) {
            return fallback;
        }
        String str = String.valueOf(value);
        if (blank(str)) {
            return fallback;
        }
        return str;
    }

    private boolean blank(String value) {
        return value == null || value.isBlank();
    }
}
