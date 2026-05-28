package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum RequirementWidget {
    @JsonProperty("input")
    INPUT,
    @JsonProperty("textarea")
    TEXTAREA,
    @JsonProperty("select")
    SELECT,
    @JsonProperty("multi_select")
    MULTI_SELECT,
    @JsonProperty("date")
    DATE,
    @JsonProperty("date_range")
    DATE_RANGE
}
