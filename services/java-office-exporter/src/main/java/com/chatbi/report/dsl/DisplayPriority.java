package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum DisplayPriority {
    @JsonProperty("high")
    HIGH("high"),
    @JsonProperty("normal")
    NORMAL("normal"),
    @JsonProperty("never")
    NEVER("never");

    private final String value;

    DisplayPriority(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static DisplayPriority fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (DisplayPriority item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown DisplayPriority value: " + value);
    }
}
