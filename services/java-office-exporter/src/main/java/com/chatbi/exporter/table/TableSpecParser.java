package com.chatbi.exporter.table;

import com.chatbi.exporter.model.VNode;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * 表格 DSL 解析器。
 * <p>
 * 能力覆盖：
 * - 静态列定义与自动推断
 * - 多级表头（headerRows + rowSpan/colSpan）
 * - 数据区渲染与格式化
 * - mergeCells 合并规则
 * - pivot 动态列展开（按 columnField/valueField）
 * </p>
 */
public final class TableSpecParser {
    /**
     * 将 table 节点解析为统一 TableModel。
     *
     * @param tableNode 表格节点
     * @param resolvedRows 上游已解析的数据行（query/source 结果）
     */
    public TableModel parse(VNode tableNode, List<Map<String, Object>> resolvedRows) {
        Map<String, Object> props = tableNode == null ? Collections.emptyMap() : tableNode.propsOrEmpty();
        String title = str(props.get("titleText"), "表格");
        boolean repeatHeader = bool(props.get("repeatHeader"), bool(props.get("headerRepeat"), true));
        boolean zebra = bool(props.get("zebra"), true);
        int maxRows = (int) Math.max(1, Math.round(num(props.get("maxRows"), 200)));

        List<TableColumn> declaredColumns = parseColumns(props.get("columns"));
        List<Map<String, Object>> rowsInput = resolveRowsInput(props, declaredColumns, resolvedRows);
        PivotResult pivotResult = buildPivot(rowsInput, props.get("pivot"), declaredColumns);
        List<Map<String, Object>> rows = (pivotResult == null ? rowsInput : pivotResult.rows);

        List<TableColumn> columns = pivotResult == null ? declaredColumns : pivotResult.columns;
        if (columns.isEmpty()) {
            columns = inferColumns(rows);
        }
        if (columns.isEmpty()) {
            columns = List.of(new TableColumn("value", "value", 120.0, "left", ""));
        }

        List<List<TableCell>> headerRows;
        if (hasList(props.get("headerRows"))) {
            headerRows = buildHeaderGrid(props.get("headerRows"), columns);
        } else if (pivotResult != null && !pivotResult.headerDefs.isEmpty()) {
            headerRows = buildHeaderGrid(pivotResult.headerDefs, columns);
        } else {
            ArrayList<TableCell> header = new ArrayList<>();
            for (TableColumn column : columns) {
                header.add(TableCell.anchor(column.title(), "center", true));
            }
            headerRows = List.of(header);
        }

        List<List<TableCell>> bodyRows = buildBodyGrid(limitRows(rows, maxRows), columns);
        applyMergeSpecs(headerRows, props.get("mergeCells"), "header");
        applyMergeSpecs(bodyRows, props.get("mergeCells"), "body");

        return new TableModel(title, columns, headerRows, bodyRows, repeatHeader, zebra);
    }

    /**
     * 行数限流，避免超大表格导致导出文档过重。
     */
    private List<Map<String, Object>> limitRows(List<Map<String, Object>> rows, int maxRows) {
        if (rows.size() <= maxRows) {
            return rows;
        }
        return rows.subList(0, maxRows);
    }

    /**
     * 解析输入行数据：
     * - 优先 props.rows
     * - 缺失时回退 resolvedRows
     *
     * 同时兼容数组行（按列序映射到 key）。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> resolveRowsInput(
            Map<String, Object> props,
            List<TableColumn> declaredColumns,
            List<Map<String, Object>> resolvedRows
    ) {
        Object raw = props.get("rows");
        if (!(raw instanceof List<?> list) || list.isEmpty()) {
            return resolvedRows == null ? Collections.emptyList() : resolvedRows;
        }
        ArrayList<Map<String, Object>> rows = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                rows.add((Map<String, Object>) map);
                continue;
            }
            if (item instanceof List<?> values) {
                LinkedHashMap<String, Object> row = new LinkedHashMap<>();
                for (int i = 0; i < values.size(); i++) {
                    String key = i < declaredColumns.size() ? declaredColumns.get(i).key() : "c" + (i + 1);
                    row.put(key, values.get(i));
                }
                rows.add(row);
            }
        }
        return rows;
    }

    /**
     * 解析列定义，兼容字符串列与对象列。
     */
    private List<TableColumn> parseColumns(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        ArrayList<TableColumn> columns = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof String keyText) {
                String key = keyText.trim();
                if (!key.isEmpty()) {
                    columns.add(new TableColumn(key, key, 120.0, "left", ""));
                }
                continue;
            }
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            String key = str(((Map<?, ?>) map).get("key"), str(((Map<?, ?>) map).get("field"), "")).trim();
            if (key.isEmpty()) {
                continue;
            }
            String title = str(((Map<?, ?>) map).get("title"), str(((Map<?, ?>) map).get("label"), key));
            double width = Math.max(48.0, num(((Map<?, ?>) map).get("width"), 120.0));
            String align = align(((Map<?, ?>) map).get("align"), "left");
            String format = str(((Map<?, ?>) map).get("format"), "");
            columns.add(new TableColumn(key, title, width, align, format));
        }
        return columns;
    }

    /**
     * 当列定义缺失时，从数据 key 推断列结构。
     */
    private List<TableColumn> inferColumns(List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return Collections.emptyList();
        }
        Set<String> keys = new LinkedHashSet<>();
        for (Map<String, Object> row : rows) {
            keys.addAll(row.keySet());
        }
        ArrayList<TableColumn> columns = new ArrayList<>();
        for (String key : keys) {
            columns.add(new TableColumn(key, key, 120.0, "left", ""));
        }
        return columns;
    }

    /**
     * 构建表头矩阵，并把合并区域转换为锚点 + hidden 占位。
     */
    private List<List<TableCell>> buildHeaderGrid(Object rawDefs, List<TableColumn> columns) {
        if (!(rawDefs instanceof List<?> list) || list.isEmpty()) {
            return Collections.emptyList();
        }
        int rowCount = list.size();
        int colCount = columns.size();
        if (colCount == 0) {
            return Collections.emptyList();
        }

        ArrayList<ArrayList<TableCell>> matrix = new ArrayList<>();
        for (int r = 0; r < rowCount; r++) {
            ArrayList<TableCell> row = new ArrayList<>();
            for (int c = 0; c < colCount; c++) {
                row.add(null);
            }
            matrix.add(row);
        }

        for (int rowIndex = 0; rowIndex < rowCount; rowIndex++) {
            Object rowRaw = list.get(rowIndex);
            if (!(rowRaw instanceof List<?> rowCells)) {
                continue;
            }
            int cursor = 0;
            for (Object cellRaw : rowCells) {
                while (cursor < colCount && matrix.get(rowIndex).get(cursor) != null) {
                    cursor++;
                }
                if (cursor >= colCount) {
                    break;
                }
                Map<?, ?> cellMap = cellRaw instanceof Map<?, ?> map ? map : Collections.emptyMap();
                int colSpan = clamp((int) Math.round(num(cellMap.get("colSpan"), 1)), 1, colCount - cursor);
                int rowSpan = clamp((int) Math.round(num(cellMap.get("rowSpan"), 1)), 1, rowCount - rowIndex);
                String text = str(cellMap.get("text"), str(cellMap.get("title"), ""));
                String align = align(cellMap.get("align"), "center");
                matrix.get(rowIndex).set(cursor, new TableCell(text, rowSpan, colSpan, align, true, false));
                for (int r = rowIndex; r < rowIndex + rowSpan; r++) {
                    for (int c = cursor; c < cursor + colSpan; c++) {
                        if (r == rowIndex && c == cursor) {
                            continue;
                        }
                        matrix.get(r).set(c, TableCell.hidden(align, true));
                    }
                }
                cursor += colSpan;
            }
        }

        for (int r = 0; r < rowCount; r++) {
            for (int c = 0; c < colCount; c++) {
                if (matrix.get(r).get(c) == null) {
                    String fallback = r == rowCount - 1 && c < columns.size() ? columns.get(c).title() : "";
                    matrix.get(r).set(c, TableCell.anchor(fallback, "center", true));
                }
            }
        }
        return new ArrayList<>(matrix);
    }

    /**
     * 构建数据区矩阵。
     */
    private List<List<TableCell>> buildBodyGrid(List<Map<String, Object>> rows, List<TableColumn> columns) {
        if (columns.isEmpty()) {
            return Collections.emptyList();
        }
        ArrayList<List<TableCell>> body = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            ArrayList<TableCell> cells = new ArrayList<>();
            for (TableColumn column : columns) {
                Object value = row.get(column.key());
                String text = formatValue(value, column.format());
                String align = !"left".equals(column.align())
                        ? column.align()
                        : (value instanceof Number ? "right" : "left");
                cells.add(TableCell.anchor(text, align, false));
            }
            body.add(cells);
        }
        return body;
    }

    /**
     * 应用 mergeCells 配置（按 scope 过滤 header/body）。
     */
    private void applyMergeSpecs(List<List<TableCell>> grid, Object rawMerges, String scope) {
        if (!(rawMerges instanceof List<?> merges) || grid.isEmpty()) {
            return;
        }
        for (Object item : merges) {
            if (!(item instanceof Map<?, ?> merge)) {
                continue;
            }
            String mergeScope = str(merge.get("scope"), "body");
            if (!scope.equalsIgnoreCase(mergeScope)) {
                continue;
            }
            int row = (int) Math.round(num(merge.get("row"), -1));
            int col = (int) Math.round(num(merge.get("col"), -1));
            int rowSpan = (int) Math.round(num(merge.get("rowSpan"), 1));
            int colSpan = (int) Math.round(num(merge.get("colSpan"), 1));
            applyMerge(grid, row, col, rowSpan, colSpan);
        }
    }

    /**
     * 在矩阵中执行一次合并。
     */
    private void applyMerge(List<List<TableCell>> grid, int row, int col, int rowSpan, int colSpan) {
        int rowCount = grid.size();
        int colCount = grid.get(0).size();
        if (row < 0 || col < 0 || row >= rowCount || col >= colCount) {
            return;
        }
        TableCell anchor = grid.get(row).get(col);
        if (anchor == null || anchor.hidden()) {
            return;
        }
        int rs = clamp(rowSpan, 1, rowCount - row);
        int cs = clamp(colSpan, 1, colCount - col);
        grid.get(row).set(col, anchor.withSpan(rs, cs));
        for (int r = row; r < row + rs; r++) {
            for (int c = col; c < col + cs; c++) {
                if (r == row && c == col) {
                    continue;
                }
                TableCell current = grid.get(r).get(c);
                String align = current == null ? anchor.align() : current.align();
                boolean header = current != null && current.header();
                grid.get(r).set(c, TableCell.hidden(align, header));
            }
        }
    }

    /**
     * Pivot 解析：
     * - rowFields 作为行维
     * - columnField 展开为动态列
     * - valueField 按 agg 聚合
     */
    @SuppressWarnings("unchecked")
    private PivotResult buildPivot(
            List<Map<String, Object>> rows,
            Object rawPivot,
            List<TableColumn> declaredColumns
    ) {
        if (!(rawPivot instanceof Map<?, ?> pivotMapRaw)) {
            return null;
        }
        Map<String, Object> pivotMap = (Map<String, Object>) pivotMapRaw;
        if (!bool(pivotMap.get("enabled"), true)) {
            return null;
        }
        String columnField = str(pivotMap.get("columnField"), "").trim();
        String valueField = str(pivotMap.get("valueField"), "").trim();
        if (columnField.isEmpty() || valueField.isEmpty()) {
            return null;
        }

        List<String> rowFields = stringList(pivotMap.get("rowFields"));
        String agg = str(pivotMap.get("agg"), "sum").toLowerCase();
        double fill = num(pivotMap.get("fill"), 0.0);
        String valueTitle = str(pivotMap.get("valueTitle"), valueField);

        LinkedHashMap<String, String> titleByField = new LinkedHashMap<>();
        for (TableColumn column : declaredColumns) {
            titleByField.put(column.key(), column.title());
        }

        LinkedHashMap<String, PivotBucket> buckets = new LinkedHashMap<>();
        LinkedHashSet<String> columnValues = new LinkedHashSet<>();

        for (Map<String, Object> row : rows) {
            String colValue = str(row.get(columnField), "").trim();
            if (colValue.isEmpty()) {
                continue;
            }
            columnValues.add(colValue);
            String bucketKey = rowFields.isEmpty() ? "__all__" : joinRowKey(row, rowFields);
            PivotBucket bucket = buckets.get(bucketKey);
            if (bucket == null) {
                LinkedHashMap<String, Object> dims = new LinkedHashMap<>();
                for (String field : rowFields) {
                    dims.put(field, row.get(field));
                }
                bucket = new PivotBucket(dims, new LinkedHashMap<>());
                buckets.put(bucketKey, bucket);
            }
            PivotAggregate aggregate = bucket.values().computeIfAbsent(colValue, ignored -> new PivotAggregate());
            Double value = toDouble(row.get(valueField));
            if ("count".equals(agg)) {
                aggregate.count += 1;
            } else if (value != null) {
                aggregate.sum += value;
                aggregate.count += 1;
                aggregate.min = Math.min(aggregate.min, value);
                aggregate.max = Math.max(aggregate.max, value);
            }
        }

        if (columnValues.isEmpty()) {
            return null;
        }

        ArrayList<TableColumn> columns = new ArrayList<>();
        for (String rowField : rowFields) {
            columns.add(new TableColumn(rowField, titleByField.getOrDefault(rowField, rowField), 130.0, "left", ""));
        }
        for (String colValue : columnValues) {
            columns.add(new TableColumn(colValue, colValue, 120.0, "right", ""));
        }

        ArrayList<Map<String, Object>> outRows = new ArrayList<>();
        for (PivotBucket bucket : buckets.values()) {
            LinkedHashMap<String, Object> out = new LinkedHashMap<>(bucket.dims());
            for (String colValue : columnValues) {
                PivotAggregate aggregate = bucket.values().get(colValue);
                out.put(colValue, aggregate == null ? fill : aggregateValue(aggregate, agg));
            }
            outRows.add(out);
        }

        ArrayList<List<Map<String, Object>>> headerDefs = new ArrayList<>();
        if (!rowFields.isEmpty()) {
            ArrayList<Map<String, Object>> top = new ArrayList<>();
            for (String rowField : rowFields) {
                top.add(Map.of(
                        "text", titleByField.getOrDefault(rowField, rowField),
                        "rowSpan", 2,
                        "colSpan", 1,
                        "align", "center"
                ));
            }
            top.add(Map.of(
                    "text", valueTitle,
                    "rowSpan", 1,
                    "colSpan", Math.max(1, columnValues.size()),
                    "align", "center"
            ));
            headerDefs.add(top);

            ArrayList<Map<String, Object>> second = new ArrayList<>();
            for (String colValue : columnValues) {
                second.add(Map.of("text", colValue, "rowSpan", 1, "colSpan", 1, "align", "center"));
            }
            headerDefs.add(second);
        } else {
            ArrayList<Map<String, Object>> single = new ArrayList<>();
            for (String colValue : columnValues) {
                single.add(Map.of("text", colValue, "rowSpan", 1, "colSpan", 1, "align", "center"));
            }
            headerDefs.add(single);
        }

        return new PivotResult(columns, outRows, headerDefs);
    }

    /**
     * 计算聚合值。
     */
    private double aggregateValue(PivotAggregate aggregate, String agg) {
        return switch (agg) {
            case "avg" -> aggregate.count > 0 ? aggregate.sum / aggregate.count : 0.0;
            case "min" -> Double.isFinite(aggregate.min) ? aggregate.min : 0.0;
            case "max" -> Double.isFinite(aggregate.max) ? aggregate.max : 0.0;
            case "count" -> aggregate.count;
            default -> aggregate.sum;
        };
    }

    /**
     * 读取字符串列表并清洗空值。
     */
    private List<String> stringList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        ArrayList<String> values = new ArrayList<>();
        for (Object item : list) {
            String text = str(item, "").trim();
            if (!text.isEmpty()) {
                values.add(text);
            }
        }
        return values;
    }

    /**
     * 用不可见分隔符拼接多维行键，避免常规字符冲突。
     */
    private String joinRowKey(Map<String, Object> row, List<String> fields) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < fields.size(); i++) {
            if (i > 0) {
                sb.append('\u0001');
            }
            sb.append(str(row.get(fields.get(i)), ""));
        }
        return sb.toString();
    }

    private boolean hasList(Object raw) {
        return raw instanceof List<?> list && !list.isEmpty();
    }

    /**
     * 按列 format 对值做文本格式化。
     */
    private String formatValue(Object value, String format) {
        if (value == null) {
            return "";
        }
        if (value instanceof Number number) {
            double val = number.doubleValue();
            if ("pct".equalsIgnoreCase(format)) {
                return String.format("%.2f%%", val * 100.0);
            }
            if ("int".equalsIgnoreCase(format)) {
                return String.valueOf(Math.round(val));
            }
            if (Math.abs(val - Math.rint(val)) < 1e-9) {
                return String.valueOf((long) Math.rint(val));
            }
            return String.format("%.2f", val);
        }
        return String.valueOf(value);
    }

    private String align(Object value, String fallback) {
        String text = str(value, fallback).toLowerCase();
        return switch (text) {
            case "left", "center", "right" -> text;
            default -> fallback;
        };
    }

    private String str(Object value, String fallback) {
        return value == null ? fallback : String.valueOf(value);
    }

    private boolean bool(Object value, boolean fallback) {
        return VNode.asBoolean(value, fallback);
    }

    private double num(Object value, double fallback) {
        return VNode.asDouble(value, fallback);
    }

    private int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }

    private Double toDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String text) {
            try {
                return Double.parseDouble(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }

    /**
     * Pivot 聚合桶（sum/count/min/max）。
     */
    private static final class PivotAggregate {
        double sum = 0.0;
        int count = 0;
        double min = Double.POSITIVE_INFINITY;
        double max = Double.NEGATIVE_INFINITY;
    }

    /**
     * Pivot 行桶：维度值 + 列聚合映射。
     */
    private record PivotBucket(LinkedHashMap<String, Object> dims, LinkedHashMap<String, PivotAggregate> values) {
    }

    /**
     * Pivot 输出结果：列定义 + 行数据 + 动态表头定义。
     */
    private record PivotResult(
            List<TableColumn> columns,
            List<Map<String, Object>> rows,
            List<List<Map<String, Object>>> headerDefs
    ) {
    }
}
