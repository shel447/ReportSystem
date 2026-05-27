package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportLayout {
    @JsonProperty("type")
    public String type;

    @JsonProperty("autoLayout")
    public Boolean autoLayout;

    @JsonProperty("grid")
    public GridDefinition grid;
}
