package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum RequirementKind {
    @JsonProperty("search_target")
    SEARCH_TARGET("search_target"),
    @JsonProperty("search_condition")
    SEARCH_CONDITION("search_condition"),
    @JsonProperty("metric")
    METRIC("metric"),
    @JsonProperty("time_range")
    TIME_RANGE("time_range"),
    @JsonProperty("filter")
    FILTER("filter"),
    @JsonProperty("threshold")
    THRESHOLD("threshold"),
    @JsonProperty("sort")
    SORT("sort"),
    @JsonProperty("free_text")
    FREE_TEXT("free_text"),
    @JsonProperty("parameter_ref")
    PARAMETER_REF("parameter_ref");

    private final String value;

    RequirementKind(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static RequirementKind fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (RequirementKind item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown RequirementKind value: " + value);
    }
}
