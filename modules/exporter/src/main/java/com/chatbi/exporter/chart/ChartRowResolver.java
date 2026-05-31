package com.chatbi.exporter.chart;

import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 图表数据行解析器。
 * <p>
 * 按优先级回填 rows：
 * 1) spec.sampleRows
 * 2) queryId 命中的 query 结果
 * 3) sourceId 命中的 dataSource.staticData
 * 4) sourceId 关联 query 结果
 * 5) 首个可用 dataSource
 * </p>
 */
public final class ChartRowResolver {
    /**
     * 解析图表节点可用的数据行。
     */
    public List<Map<String, Object>> resolve(VDoc doc, VNode chartNode, ChartSpec spec) {
        if (spec != null && !spec.sampleRows().isEmpty()) {
            return spec.sampleRows();
        }

        String sourceId = sourceId(chartNode);
        String queryId = queryId(chartNode);

        List<Map<String, Object>> rows = fromQueryResult(doc, queryId);
        if (!rows.isEmpty()) {
            return rows;
        }

        rows = fromSource(doc, sourceId);
        if (!rows.isEmpty()) {
            return rows;
        }

        rows = fromQueryBySource(doc, sourceId);
        if (!rows.isEmpty()) {
            return rows;
        }

        rows = fromFirstSource(doc);
        if (!rows.isEmpty()) {
            return rows;
        }

        return Collections.emptyList();
    }

    /**
     * 从节点 data 中读取 sourceId。
     */
    @SuppressWarnings("unchecked")
    private String sourceId(VNode chartNode) {
        if (chartNode == null || chartNode.data == null) {
            return "";
        }
        Object value = chartNode.data.get("sourceId");
        return value == null ? "" : String.valueOf(value);
    }

    /**
     * 从节点 data 中读取 queryId。
     */
    @SuppressWarnings("unchecked")
    private String queryId(VNode chartNode) {
        if (chartNode == null || chartNode.data == null) {
            return "";
        }
        Object value = chartNode.data.get("queryId");
        return value == null ? "" : String.valueOf(value);
    }

    /**
     * 从 dataSources 中按 sourceId 查找 staticData。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromSource(VDoc doc, String sourceId) {
        if (doc == null || doc.dataSources == null || doc.dataSources.isEmpty()) {
            return Collections.emptyList();
        }
        for (Map<String, Object> source : doc.dataSources) {
            if (!sourceId.isBlank() && !sourceId.equals(String.valueOf(source.get("id")))) {
                continue;
            }
            List<Map<String, Object>> rows = decodeRows(source.get("staticData"));
            if (!rows.isEmpty()) {
                return rows;
            }
        }
        return Collections.emptyList();
    }

    /**
     * 取第一个可用 dataSource 的数据，作为兜底。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromFirstSource(VDoc doc) {
        if (doc == null || doc.dataSources == null || doc.dataSources.isEmpty()) {
            return Collections.emptyList();
        }
        for (Map<String, Object> source : doc.dataSources) {
            List<Map<String, Object>> rows = decodeRows(source.get("staticData"));
            if (!rows.isEmpty()) {
                return rows;
            }
        }
        return Collections.emptyList();
    }

    /**
     * 按 queryId 查找查询结果。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromQueryResult(VDoc doc, String queryId) {
        if (queryId.isBlank() || doc == null || doc.queries == null) {
            return Collections.emptyList();
        }
        for (Map<String, Object> query : doc.queries) {
            if (!queryId.equals(String.valueOf(query.get("queryId")))) {
                continue;
            }
            List<Map<String, Object>> rows = decodeRows(query.get("rows"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("result"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("data"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("sampleRows"));
            if (!rows.isEmpty()) {
                return rows;
            }
        }
        return Collections.emptyList();
    }

    /**
     * 按 sourceId 关联查询结果。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> fromQueryBySource(VDoc doc, String sourceId) {
        if (sourceId.isBlank() || doc == null || doc.queries == null) {
            return Collections.emptyList();
        }
        for (Map<String, Object> query : doc.queries) {
            if (!sourceId.equals(String.valueOf(query.get("sourceId")))) {
                continue;
            }
            List<Map<String, Object>> rows = decodeRows(query.get("rows"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("result"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("data"));
            if (!rows.isEmpty()) {
                return rows;
            }
            rows = decodeRows(query.get("sampleRows"));
            if (!rows.isEmpty()) {
                return rows;
            }
        }
        return Collections.emptyList();
    }

    /**
     * 统一解码 rows/data/result 等常见结构。
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> decodeRows(Object raw) {
        if (raw == null) {
            return Collections.emptyList();
        }
        if (raw instanceof List<?> list) {
            List<Map<String, Object>> rows = new ArrayList<>();
            for (Object item : list) {
                if (item instanceof Map<?, ?> map) {
                    rows.add((Map<String, Object>) map);
                }
            }
            return rows;
        }
        if (raw instanceof Map<?, ?> map) {
            Map<String, Object> obj = (Map<String, Object>) map;
            Object rows = obj.get("rows");
            if (rows instanceof List<?>) {
                return decodeRows(rows);
            }
            Object data = obj.get("data");
            if (data instanceof List<?>) {
                return decodeRows(data);
            }
            if (data instanceof Map<?, ?> dataMap) {
                return decodeRows(dataMap);
            }
        }
        return Collections.emptyList();
    }
}
