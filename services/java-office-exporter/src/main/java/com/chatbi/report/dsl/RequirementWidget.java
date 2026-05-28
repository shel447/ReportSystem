package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum RequirementWidget {
    @JsonProperty("input")
    INPUT("input"),
    @JsonProperty("textarea")
    TEXTAREA("textarea"),
    @JsonProperty("select")
    SELECT("select"),
    @JsonProperty("multi_select")
    MULTI_SELECT("multi_select"),
    @JsonProperty("date")
    DATE("date"),
    @JsonProperty("date_range")
    DATE_RANGE("date_range");

    private final String value;

    RequirementWidget(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static RequirementWidget fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (RequirementWidget item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown RequirementWidget value: " + value);
    }
}
