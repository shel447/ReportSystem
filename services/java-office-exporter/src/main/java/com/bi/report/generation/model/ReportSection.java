package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSection {
    @JsonProperty("id")
    public String id;

    @JsonProperty("title")
    public String title;

    @JsonProperty("description")
    public String description;

    @JsonProperty("order")
    public Integer order;

    @JsonProperty("components")
    public List<ReportComponent> components;

    @JsonProperty("summary")
    public ReportSummary summary;

    @JsonProperty("layout")
    public Map<String, Object> layout;
}
