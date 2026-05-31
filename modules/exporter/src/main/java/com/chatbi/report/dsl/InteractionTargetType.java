package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum InteractionTargetType {
    @JsonProperty("filter")
    FILTER("filter"),
    @JsonProperty("jump")
    JUMP("jump"),
    @JsonProperty("highlight")
    HIGHLIGHT("highlight");

    private final String value;

    InteractionTargetType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static InteractionTargetType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (InteractionTargetType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown InteractionTargetType value: " + value);
    }
}
