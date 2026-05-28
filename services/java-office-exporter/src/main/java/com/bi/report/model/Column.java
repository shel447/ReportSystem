package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Column {
    @JsonProperty("title")
    public String title;

    @JsonProperty("key")
    public String key;

    @JsonProperty("type")
    public FieldType type;

    @JsonProperty("enumConfig")
    public List<EnumValue> enumConfig;

    @JsonProperty("uiConfig")
    public FieldUI uiConfig;

    @JsonProperty("lineageTracing")
    public ColumnLineageTracing lineageTracing;

    @JsonProperty("order")
    public Double order;

    @JsonProperty("colSpan")
    public Double colSpan;

    @JsonProperty("children")
    public List<Column> children;

    @JsonProperty("sortable")
    public Boolean sortable;

    @JsonProperty("filterable")
    public Boolean filterable;

    @JsonProperty("width")
    public Object width;

}
