package com.chatbi.exporter.chart;

/**
 * 图表字段绑定描述。
 * <p>
 * 该模型用于统一表达前端 DSL 中 "role/field/agg" 三元信息，
 * 例如：x=day，y=latency_ms，agg=avg。
 * </p>
 */
public final class ChartBinding {
    private final String role;
    private final String field;
    private final String agg;
    private final String axis;

    /**
     * @param role 绑定角色（如 x/y/series/y2）
     * @param field 字段名
     * @param agg 聚合函数（如 sum/avg），可为空
     */
    public ChartBinding(String role, String field, String agg) {
        this(role, field, agg, "");
    }

    /**
     * @param role 绑定角色（如 x/y/series/y2）
     * @param field 字段名
     * @param agg 聚合函数（如 sum/avg），可为空
     * @param axis 轴语义（primary/secondary/数字），可为空
     */
    public ChartBinding(String role, String field, String agg, String axis) {
        this.role = role;
        this.field = field;
        this.agg = agg;
        this.axis = axis;
    }

    public String role() {
        return role;
    }

    public String field() {
        return field;
    }

    public String agg() {
        return agg;
    }

    public String axis() {
        return axis;
    }
}
