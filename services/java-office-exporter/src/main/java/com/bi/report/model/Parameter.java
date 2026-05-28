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
public class Parameter {
    @JsonProperty("id")
    public String id;

    @JsonProperty("label")
    public String label;

    @JsonProperty("description")
    public String description;

    @JsonProperty("inputType")
    public String inputType;

    @JsonProperty("required")
    public Boolean required;

    @JsonProperty("multi")
    public Boolean multi;

    @JsonProperty("interactionMode")
    public String interactionMode;

    @JsonProperty("priority")
    public Integer priority;

    @JsonProperty("placeholder")
    public String placeholder;

    @JsonProperty("defaultValue")
    public List<ParameterValue> defaultValue;

    @JsonProperty("options")
    public List<ParameterValue> options;

    @JsonProperty("values")
    public List<ParameterValue> values;

    @JsonProperty("runtimeContext")
    public Object runtimeContext;

    @JsonProperty("source")
    public String source;

}
