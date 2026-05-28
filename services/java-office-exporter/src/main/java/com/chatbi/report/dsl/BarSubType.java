package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum BarSubType {
    @JsonProperty("horizontal")
    HORIZONTAL("horizontal");

    private final String value;

    BarSubType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static BarSubType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (BarSubType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown BarSubType value: " + value);
    }
}
