package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ResponsiveSize {
    @JsonProperty("compact")
    COMPACT("compact"),
    @JsonProperty("normal")
    NORMAL("normal"),
    @JsonProperty("wide")
    WIDE("wide");

    private final String value;

    ResponsiveSize(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ResponsiveSize fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ResponsiveSize item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ResponsiveSize value: " + value);
    }
}
