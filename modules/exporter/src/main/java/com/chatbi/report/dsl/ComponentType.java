package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ComponentType {
    @JsonProperty("text")
    TEXT("text"),
    @JsonProperty("table")
    TABLE("table"),
    @JsonProperty("chart")
    CHART("chart"),
    @JsonProperty("markdown")
    MARKDOWN("markdown"),
    @JsonProperty("compositeTable")
    COMPOSITE_TABLE("compositeTable");

    private final String value;

    ComponentType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ComponentType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ComponentType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ComponentType value: " + value);
    }
}
