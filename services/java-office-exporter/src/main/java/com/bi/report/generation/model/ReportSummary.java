package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSummary {
    @JsonProperty("id")
    public String id;

    @JsonProperty("overview")
    public String overview;
}
