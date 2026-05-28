package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class MergeRowInfo {
    @JsonProperty("startRowIndex")
    public Integer startRowIndex;

    @JsonProperty("rowSpan")
    public Integer rowSpan;

    @JsonProperty("column")
    public String column;

    @JsonProperty("mergedText")
    public String mergedText;

}
