package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum AxisType {
    @JsonProperty("category")
    CATEGORY("category"),
    @JsonProperty("value")
    VALUE("value");

    private final String value;

    AxisType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static AxisType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (AxisType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown AxisType value: " + value);
    }
}
