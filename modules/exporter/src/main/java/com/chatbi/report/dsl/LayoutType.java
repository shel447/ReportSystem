package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum LayoutType {
    @JsonProperty("grid")
    GRID("grid"),
    @JsonProperty("flow")
    FLOW("flow"),
    @JsonProperty("absolute")
    ABSOLUTE("absolute");

    private final String value;

    LayoutType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static LayoutType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (LayoutType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown LayoutType value: " + value);
    }
}
