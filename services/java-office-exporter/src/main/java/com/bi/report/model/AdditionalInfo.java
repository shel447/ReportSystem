package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class AdditionalInfo {
    @JsonProperty("type")
    public AdditionalInfoType type;

    @JsonProperty("name")
    public String name;

    @JsonProperty("value")
    public String value;

    @JsonProperty("appendix")
    public String appendix;

}
