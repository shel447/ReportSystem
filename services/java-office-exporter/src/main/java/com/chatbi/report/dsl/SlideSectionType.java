package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum SlideSectionType {
    @JsonProperty("section")
    SECTION("section");

    private final String value;

    SlideSectionType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static SlideSectionType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (SlideSectionType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown SlideSectionType value: " + value);
    }
}
