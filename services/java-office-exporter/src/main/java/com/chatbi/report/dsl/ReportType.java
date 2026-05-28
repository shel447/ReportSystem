package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ReportType {
    @JsonProperty("PPT")
    PPT,
    @JsonProperty("Word")
    WORD,
    @JsonProperty("Dashboard")
    DASHBOARD
}
