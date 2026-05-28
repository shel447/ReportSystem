package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ValueFormatType {
    @JsonProperty("time")
    TIME("time"),
    @JsonProperty("percentage")
    PERCENTAGE("percentage"),
    @JsonProperty("number")
    NUMBER("number"),
    @JsonProperty("byte")
    BYTE("byte");

    private final String value;

    ValueFormatType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ValueFormatType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ValueFormatType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ValueFormatType value: " + value);
    }
}
