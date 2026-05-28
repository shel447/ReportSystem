package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum FieldType {
    @JsonProperty("string")
    STRING("string"),
    @JsonProperty("long")
    LONG("long"),
    @JsonProperty("int")
    INT("int"),
    @JsonProperty("timestamp")
    TIMESTAMP("timestamp"),
    @JsonProperty("double")
    DOUBLE("double"),
    @JsonProperty("float")
    FLOAT("float"),
    @JsonProperty("enum")
    ENUM("enum");

    private final String value;

    FieldType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static FieldType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (FieldType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown FieldType value: " + value);
    }
}
