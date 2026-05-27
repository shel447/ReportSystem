package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportGenerateMeta {
    @JsonProperty("status")
    public String status;

    @JsonProperty("question")
    public String question;

    @JsonProperty("additionalInfos")
    public List<ReportAdditionalInfo> additionalInfos;

    @JsonProperty("outline")
    public Map<String, Object> outline;

    @JsonProperty("parameters")
    public Map<String, Object> parameters;
}
