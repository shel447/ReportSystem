package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum InteractionAction {
    @JsonProperty("click")
    CLICK("click"),
    @JsonProperty("hover")
    HOVER("hover"),
    @JsonProperty("change")
    CHANGE("change"),
    @JsonProperty("select")
    SELECT("select");

    private final String value;

    InteractionAction(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static InteractionAction fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (InteractionAction item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown InteractionAction value: " + value);
    }
}
