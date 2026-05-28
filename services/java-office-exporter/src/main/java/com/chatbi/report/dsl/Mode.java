package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Mode {
    @JsonProperty("draft")
    DRAFT("draft"),
    @JsonProperty("published")
    PUBLISHED("published");

    private final String value;

    Mode(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static Mode fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (Mode item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown Mode value: " + value);
    }
}
