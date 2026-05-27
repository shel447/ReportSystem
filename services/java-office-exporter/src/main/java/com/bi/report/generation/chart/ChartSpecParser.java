package com.bi.report.generation.chart;

import com.bi.report.generation.model.ChartDataProperties;
import com.bi.report.generation.model.ReportColumn;

import java.util.*;

public final class ChartSpecParser {

    private ChartSpecParser() {}

    public static ChartSpec parse(ChartDataProperties props) {
        return parse(props, null);
    }

    public static ChartSpec parse(ChartDataProperties props, String chartTypeHint) {
        if (props == null) {
            return new ChartSpec("unknown", "", List.of(), List.of(), false);
        }

        String title = str(props.title);
        String chartType = resolveChartType(props, chartTypeHint);

        List<ReportColumn> columns = props.columns != null ? props.columns : List.of();
        List<Map<String, Object>> data = props.data != null ? props.data : List.of();
        List<Map<String, Object>> series = props.series != null ? props.series : List.of();

        if (data.isEmpty() || columns.isEmpty()) {
            return new ChartSpec(chartType, title, List.of(), List.of(), false);
        }

        String categoryCol = findCategoryColumn(columns);
        List<String> valueCols = findValueColumns(columns, categoryCol);

        if (categoryCol.isEmpty() || valueCols.isEmpty()) {
            return new ChartSpec(chartType, title, List.of(), List.of(), false);
        }

        List<String> categories = new ArrayList<>();
        for (Map<String, Object> row : data) {
            categories.add(str(row.get(categoryCol)));
        }

        List<ChartSpec.Series> seriesList = new ArrayList<>();
        if (!series.isEmpty()) {
            for (Map<String, Object> s : series) {
                String sName = str(s.get("name"));
                String encodeField = extractEncodeField(s);
                if (encodeField.isEmpty() && !valueCols.isEmpty()) {
                    encodeField = valueCols.get(0);
                }
                List<Double> values = extractValues(data, encodeField);
                seriesList.add(new ChartSpec.Series(sName.isEmpty() ? encodeField : sName, values));
            }
        } else {
            for (String col : valueCols) {
                seriesList.add(new ChartSpec.Series(col, extractValues(data, col)));
            }
        }

        boolean canRender = !categories.isEmpty() && !seriesList.isEmpty();
        return new ChartSpec(chartType, title, categories, seriesList, canRender);
    }

    private static String resolveChartType(ChartDataProperties props, String hint) {
        if (hint != null && !hint.isBlank()) return hint.trim();
        if (props.series != null) {
            for (Map<String, Object> s : props.series) {
                String t = str(s.get("type"));
                if (!t.isEmpty()) return t;
            }
        }
        return "unknown";
    }

    private static String findCategoryColumn(List<ReportColumn> columns) {
        for (ReportColumn col : columns) {
            if ("dimension".equalsIgnoreCase(col.type) || "category".equalsIgnoreCase(col.type)) {
                return str(col.key);
            }
        }
        if (!columns.isEmpty()) {
            return str(columns.get(0).key);
        }
        return "";
    }

    private static List<String> findValueColumns(List<ReportColumn> columns, String categoryCol) {
        List<String> result = new ArrayList<>();
        for (ReportColumn col : columns) {
            String key = str(col.key);
            if (!key.equals(categoryCol)) {
                result.add(key);
            }
        }
        return result;
    }

    @SuppressWarnings("unchecked")
    private static String extractEncodeField(Map<String, Object> seriesItem) {
        Object encode = seriesItem.get("encode");
        if (encode instanceof Map<?, ?> map) {
            Object y = ((Map<String, Object>) map).get("y");
            if (y instanceof List<?> list && !list.isEmpty()) {
                return str(list.get(0));
            }
            return str(y);
        }
        return str(seriesItem.get("field"));
    }

    private static List<Double> extractValues(List<Map<String, Object>> data, String field) {
        List<Double> values = new ArrayList<>();
        for (Map<String, Object> row : data) {
            Object val = row.get(field);
            values.add(toDouble(val));
        }
        return values;
    }

    private static Double toDouble(Object val) {
        if (val == null) return 0.0;
        if (val instanceof Number n) return n.doubleValue();
        try {
            return Double.parseDouble(val.toString().trim());
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private static String str(Object val) {
        return val == null ? "" : val.toString().trim();
    }
}
