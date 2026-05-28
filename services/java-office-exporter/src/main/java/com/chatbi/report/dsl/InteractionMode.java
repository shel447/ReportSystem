package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum InteractionMode {
    @JsonProperty("form")
    FORM("form"),
    @JsonProperty("natural_language")
    NATURAL_LANGUAGE("natural_language");

    private final String value;

    InteractionMode(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static InteractionMode fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (InteractionMode item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown InteractionMode value: " + value);
    }
}
