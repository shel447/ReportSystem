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
public class RequirementItem {
    @JsonProperty("id")
    public String id;

    @JsonProperty("label")
    public String label;

    @JsonProperty("kind")
    public String kind;

    @JsonProperty("required")
    public Boolean required;

    @JsonProperty("multi")
    public Boolean multi;

    @JsonProperty("description")
    public String description;

    @JsonProperty("sourceParameterId")
    public String sourceParameterId;

    @JsonProperty("widget")
    public String widget;

    @JsonProperty("defaultValue")
    public List<ParameterValue> defaultValue;

    @JsonProperty("values")
    public List<ParameterValue> values;

    @JsonProperty("valueSource")
    public String valueSource;

}
