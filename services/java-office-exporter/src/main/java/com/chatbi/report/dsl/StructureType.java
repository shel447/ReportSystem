package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum StructureType {
    @JsonProperty("flow")
    FLOW("flow"),
    @JsonProperty("paged")
    PAGED("paged");

    private final String value;

    StructureType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static StructureType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (StructureType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown StructureType value: " + value);
    }
}
