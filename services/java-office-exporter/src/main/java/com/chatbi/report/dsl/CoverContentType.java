package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum CoverContentType {
    @JsonProperty("image")
    IMAGE("image"),
    @JsonProperty("text")
    TEXT("text");

    private final String value;

    CoverContentType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static CoverContentType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (CoverContentType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown CoverContentType value: " + value);
    }
}
