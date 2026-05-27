package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ChartDataProperties {
    @JsonProperty("dataType")
    public String dataType;

    @JsonProperty("sourceId")
    public String sourceId;

    @JsonProperty("url")
    public String url;

    @JsonProperty("method")
    public String method;

    @JsonProperty("autoRefresh")
    public Boolean autoRefresh;

    @JsonProperty("refreshInterval")
    public Double refreshInterval;

    @JsonProperty("title")
    public String title;

    @JsonProperty("columns")
    public List<ReportColumn> columns;

    @JsonProperty("data")
    public List<Map<String, Object>> data;

    @JsonProperty("series")
    public List<Map<String, Object>> series;

    @JsonProperty("axisGroup")
    public List<String> axisGroup;

    @JsonProperty("xAxis")
    public Object xAxis;

    @JsonProperty("yAxis")
    public Object yAxis;
}
