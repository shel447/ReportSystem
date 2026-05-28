package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class TableDataProperty {
    @JsonProperty("dataType")
    public String dataType;

    @JsonProperty("sourceId")
    public String sourceId;

    @JsonProperty("url")
    public String url;

    @JsonProperty("method")
    public String method;

    @JsonProperty("autoRefresh")
    public Boolean autoRefresh;

    @JsonProperty("refreshInterval")
    public Double refreshInterval;

    @JsonProperty("title")
    public String title;

    @JsonProperty("columns")
    public List<Column> columns;

    @JsonProperty("data")
    public List<Map<String, Object>> data;

    @JsonProperty("mergeColumns")
    public List<MergeColumnInfo> mergeColumns;

    @JsonProperty("mergeRows")
    public List<MergeRowInfo> mergeRows;

    @JsonProperty("hasMerge")
    public Boolean hasMerge;

}
