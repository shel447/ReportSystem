package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum RequirementKind {
    @JsonProperty("search_target")
    SEARCH_TARGET,
    @JsonProperty("search_condition")
    SEARCH_CONDITION,
    @JsonProperty("metric")
    METRIC,
    @JsonProperty("time_range")
    TIME_RANGE,
    @JsonProperty("filter")
    FILTER,
    @JsonProperty("threshold")
    THRESHOLD,
    @JsonProperty("sort")
    SORT,
    @JsonProperty("free_text")
    FREE_TEXT,
    @JsonProperty("parameter_ref")
    PARAMETER_REF
}
