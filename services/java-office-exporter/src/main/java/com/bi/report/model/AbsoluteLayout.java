package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AbsoluteLayout {
    @JsonProperty("type")
    public String type;

    @JsonProperty("x")
    public Double x;

    @JsonProperty("y")
    public Double y;

    @JsonProperty("w")
    public Double w;

    @JsonProperty("h")
    public Double h;

    @JsonProperty("zIndex")
    public Double zIndex;

}
