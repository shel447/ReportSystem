package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ColumnLineageSource {
    @JsonProperty("dataSourceName")
    public String dataSourceName;

    @JsonProperty("field")
    public String field;

    @JsonProperty("businessName")
    public String businessName;

    @JsonProperty("businessName_cn")
    public String businessName_cn;

    @JsonProperty("enumValues")
    public String enumValues;

    @JsonProperty("ui")
    public String ui;

}
