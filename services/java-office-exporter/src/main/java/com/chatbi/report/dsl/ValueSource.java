package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ValueSource {
    @JsonProperty("user_input")
    USER_INPUT("user_input"),
    @JsonProperty("default")
    DEFAULT("default"),
    @JsonProperty("parameter_ref")
    PARAMETER_REF("parameter_ref"),
    @JsonProperty("system_fill")
    SYSTEM_FILL("system_fill");

    private final String value;

    ValueSource(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ValueSource fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ValueSource item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ValueSource value: " + value);
    }
}
