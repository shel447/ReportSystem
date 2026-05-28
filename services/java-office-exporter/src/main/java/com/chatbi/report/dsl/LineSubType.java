package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum LineSubType {
    @JsonProperty("area")
    AREA("area");

    private final String value;

    LineSubType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static LineSubType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (LineSubType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown LineSubType value: " + value);
    }
}
