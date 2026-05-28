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
public class MarkdownComponent {
    @JsonProperty("id")
    public String id;

    @JsonProperty("layout")
    public ComponentLayout layout;

    @JsonProperty("basicProperties")
    public MarkdownBasicProperties basicProperties;

    @JsonProperty("advanceProperties")
    public MarkdownAdvanceProperties advanceProperties;

    @JsonProperty("interactions")
    public List<Interaction> interactions;

    @JsonProperty("type")
    public String type;

    @JsonProperty("dataProperties")
    public MarkdownDataProperty dataProperties;

}
