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
public class ChartComponent {
    @JsonProperty("id")
    public String id;

    @JsonProperty("layout")
    public ComponentLayout layout;

    @JsonProperty("basicProperties")
    public ChartBasicProperties basicProperties;

    @JsonProperty("advanceProperties")
    public ChartAdvanceProperties advanceProperties;

    @JsonProperty("interactions")
    public List<Interaction> interactions;

    @JsonProperty("type")
    public String type;

    @JsonProperty("dataProperties")
    public ChartDataProperty dataProperties;

    @JsonProperty("options")
    public ChartOption options;

}
