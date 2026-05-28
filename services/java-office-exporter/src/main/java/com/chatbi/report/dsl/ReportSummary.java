package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSummary {
    public String id;
    public String overview;
}
