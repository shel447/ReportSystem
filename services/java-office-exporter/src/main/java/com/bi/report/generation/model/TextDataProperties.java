package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TextDataProperties {
    @JsonProperty("dataType")
    public String dataType;

    @JsonProperty("content")
    public String content;

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
}
