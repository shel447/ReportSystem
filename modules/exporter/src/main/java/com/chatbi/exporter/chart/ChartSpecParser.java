package com.chatbi.exporter.chart;

import com.chatbi.exporter.model.VNode;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * VNode(chart) -> ChartSpec 解析器。
 * <p>
 * 负责将前端多种历史字段与新字段统一收敛到稳定结构：
 * - xField / yField / yFields / measures / bindings
 * - legend/axis/stack/smooth
 * - palette / optionPatch
 * </p>
 */
public final class ChartSpecParser {
    /**
     * 解析图表节点语义规格。
     */
    public ChartSpec parse(VNode chartNode) {
        if (chartNode == null) {
            return emptySpec();
        }
        Map<String, Object> props = chartNode.propsOrEmpty();
        String title = resolveTitle(chartNode);
        String chartType = str(props.get("chartType"), "line");
        boolean legendShow = bool(props.get("legendShow"), true);
        String legendPos = str(props.get("legendPos"), "top");
        String xAxisTitle = str(props.get("xAxisTitle"), "");
        String yAxisTitle = str(props.get("yAxisTitle"), "");
        List<ChartBinding> bindings = parseBindings(props.get("bindings"));
        String dimension = resolveDimension(props, bindings);
        List<String> measures = resolveMeasures(props, bindings);
        String series = resolveSeries(props, bindings);
        String aggregate = str(props.get("aggregate"), str(props.get("agg"), "sum"));
        String secondAxis = resolveSecondAxis(props, bindings);
        boolean stacked = bool(props.get("stacked"), false);
        boolean smooth = bool(props.get("smooth"), false);
        int filtersCount = listSize(props.get("filters"));
        int computedCount = Math.max(listSize(props.get("computedFields")), listSize(props.get("calculatedFields")));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> sampleRows = props.get("sampleRows") instanceof List<?> rows
                ? (List<Map<String, Object>>) rows
                : Collections.emptyList();

        List<String> palette = readPalette(chartNode, props);
        Map<String, Object> optionPatch = readOptionPatch(props);

        return new ChartSpec(
                title,
                chartType,
                legendShow,
                legendPos,
                xAxisTitle,
                yAxisTitle,
                dimension,
                measures,
                series,
                aggregate,
                secondAxis,
                stacked,
                smooth,
                filtersCount,
                computedCount,
                bindings,
                sampleRows,
                palette,
                optionPatch
        );
    }

    /**
     * 返回空安全默认规格。
     */
    private ChartSpec emptySpec() {
        return new ChartSpec(
                "图表",
                "line",
                true,
                "top",
                "",
                "",
                "",
                Collections.emptyList(),
                "",
                "sum",
                "",
                false,
                false,
                0,
                0,
                Collections.emptyList(),
                Collections.emptyList(),
                Collections.emptyList(),
                Collections.emptyMap()
        );
    }

    /**
     * 标题优先级：titleText > node.name > "图表"。
     */
    private String resolveTitle(VNode node) {
        String title = node.propString("titleText", "");
        if (!title.isBlank()) {
            return title;
        }
        if (node.name != null && !node.name.isBlank()) {
            return node.name;
        }
        return "图表";
    }

    /**
     * 解析维度字段（X 轴）。
     */
    private String resolveDimension(Map<String, Object> props, List<ChartBinding> bindings) {
        String direct = str(props.get("xField"), "");
        if (!direct.isBlank()) {
            return direct;
        }
        for (ChartBinding binding : bindings) {
            String role = binding.role().toLowerCase();
            if ("x".equals(role) || "dimension".equals(role) || "category".equals(role)) {
                return binding.field();
            }
        }
        return "";
    }

    /**
     * 解析指标字段列表（Y 轴）。
     */
    private List<String> resolveMeasures(Map<String, Object> props, List<ChartBinding> bindings) {
        Set<String> result = new LinkedHashSet<>();
        addField(result, props.get("yField"));
        addStringList(result, props.get("yFields"));
        addMeasureObjects(result, props.get("measures"));
        for (ChartBinding binding : bindings) {
            String role = binding.role().toLowerCase();
            if ("y".equals(role)
                    || "y1".equals(role)
                    || "measure".equals(role)
                    || "value".equals(role)
                    || "secondary".equals(role)
                    || "ysecondary".equals(role)
                    || "y2".equals(role)) {
                addField(result, binding.field());
            }
        }
        return new ArrayList<>(result);
    }

    /**
     * 解析系列分组字段。
     */
    private String resolveSeries(Map<String, Object> props, List<ChartBinding> bindings) {
        String direct = str(props.get("seriesField"), "");
        if (!direct.isBlank()) {
            return direct;
        }
        for (ChartBinding binding : bindings) {
            String role = binding.role().toLowerCase();
            if ("series".equals(role) || "group".equals(role) || "color".equals(role)) {
                return binding.field();
            }
        }
        return "";
    }

    /**
     * 解析第二轴字段。
     */
    private String resolveSecondAxis(Map<String, Object> props, List<ChartBinding> bindings) {
        String direct = str(props.get("secondAxisField"), "");
        if (!direct.isBlank()) {
            return direct;
        }
        for (ChartBinding binding : bindings) {
            String role = binding.role().toLowerCase();
            String axis = binding.axis() == null ? "" : binding.axis().trim().toLowerCase();
            if ("y2".equals(role)
                    || "secondary".equals(role)
                    || "ysecondary".equals(role)
                    || "secondary".equals(axis)
                    || "1".equals(axis)) {
                return binding.field();
            }
        }
        return "";
    }

    /**
     * 解析 bindings 配置。
     */
    @SuppressWarnings("unchecked")
    private List<ChartBinding> parseBindings(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        List<ChartBinding> result = new ArrayList<>();
        for (Object item : list) {
            if (!(item instanceof Map<?, ?> map)) {
                continue;
            }
            Map<String, Object> typed = (Map<String, Object>) map;
            String role = str(typed.get("role"), "");
            String field = str(typed.get("field"), "");
            String agg = str(typed.get("agg"), "");
            String axis = str(typed.get("axis"), "");
            if (role.isBlank() || field.isBlank()) {
                continue;
            }
            result.add(new ChartBinding(role, field, agg, axis));
        }
        return result;
    }

    /**
     * 兼容 measures 中对象结构（{ field: ... }）。
     */
    @SuppressWarnings("unchecked")
    private void addMeasureObjects(Set<String> result, Object raw) {
        if (!(raw instanceof List<?> list)) {
            return;
        }
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                addField(result, ((Map<String, Object>) map).get("field"));
            } else {
                addField(result, item);
            }
        }
    }

    /**
     * 兼容 yFields 中字符串/对象混合结构。
     */
    @SuppressWarnings("unchecked")
    private void addStringList(Set<String> result, Object raw) {
        if (!(raw instanceof List<?> list)) {
            return;
        }
        for (Object item : list) {
            addField(result, item);
            if (item instanceof Map<?, ?> map) {
                addField(result, ((Map<String, Object>) map).get("field"));
            }
        }
    }

    /**
     * 解析调色板，优先 props.palette，回退 style.palette。
     */
    @SuppressWarnings("unchecked")
    private List<String> readPalette(VNode node, Map<String, Object> props) {
        Object raw = props.get("palette");
        if (!(raw instanceof List<?>)) {
            raw = node.styleOrEmpty().get("palette");
        }
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        List<String> result = new ArrayList<>();
        for (Object item : list) {
            String color = str(item, "");
            if (!color.isBlank()) {
                result.add(color);
            }
        }
        return result;
    }

    private void addField(Set<String> result, Object raw) {
        String field = str(raw, "");
        if (!field.isBlank()) {
            result.add(field);
        }
    }

    /**
     * 读取 optionPatch，缺失则返回空 Map。
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> readOptionPatch(Map<String, Object> props) {
        Object raw = props.get("optionPatch");
        if (raw instanceof Map<?, ?> map) {
            return (Map<String, Object>) map;
        }
        return Collections.emptyMap();
    }

    private int listSize(Object raw) {
        return raw instanceof List<?> list ? list.size() : 0;
    }

    private boolean bool(Object raw, boolean fallback) {
        if (raw instanceof Boolean b) {
            return b;
        }
        if (raw instanceof String s) {
            if ("true".equalsIgnoreCase(s)) {
                return true;
            }
            if ("false".equalsIgnoreCase(s)) {
                return false;
            }
        }
        return fallback;
    }

    private String str(Object raw, String fallback) {
        if (raw == null) {
            return fallback;
        }
        String value = String.valueOf(raw);
        return value == null ? fallback : value;
    }
}
