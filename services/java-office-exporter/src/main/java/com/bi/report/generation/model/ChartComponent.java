package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ChartComponent extends ReportComponent {
    @JsonProperty("dataProperties")
    public ChartDataProperties dataProperties;

    @JsonProperty("options")
    public Map<String, Object> options;
}
