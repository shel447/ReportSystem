package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ParameterInputType {
    @JsonProperty("free_text")
    FREE_TEXT("free_text"),
    @JsonProperty("date")
    DATE("date"),
    @JsonProperty("enum")
    ENUM("enum"),
    @JsonProperty("dynamic")
    DYNAMIC("dynamic");

    private final String value;

    ParameterInputType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ParameterInputType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ParameterInputType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ParameterInputType value: " + value);
    }
}
