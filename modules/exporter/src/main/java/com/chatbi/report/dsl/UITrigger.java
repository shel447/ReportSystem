package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum UITrigger {
    @JsonProperty("click")
    CLICK("click"),
    @JsonProperty("dblclick")
    DBLCLICK("dblclick"),
    @JsonProperty("hover")
    HOVER("hover");

    private final String value;

    UITrigger(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static UITrigger fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (UITrigger item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown UITrigger value: " + value);
    }
}
