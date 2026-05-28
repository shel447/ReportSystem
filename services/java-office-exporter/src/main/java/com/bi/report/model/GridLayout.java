package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class GridLayout {
    @JsonProperty("type")
    public String type;

    @JsonProperty("gx")
    public Double gx;

    @JsonProperty("gy")
    public Double gy;

    @JsonProperty("gw")
    public Double gw;

    @JsonProperty("gh")
    public Double gh;

}
