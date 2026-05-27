package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSlide extends ReportPagedContentItem {
    @JsonProperty("layout")
    public ReportLayout layout;

    @JsonProperty("components")
    public List<ReportComponent> components;
}
