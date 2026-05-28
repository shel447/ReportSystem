package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum PieSubType {
    @JsonProperty("ring")
    RING("ring");

    private final String value;

    PieSubType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static PieSubType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (PieSubType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown PieSubType value: " + value);
    }
}
