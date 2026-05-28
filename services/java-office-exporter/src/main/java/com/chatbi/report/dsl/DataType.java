package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum DataType {
    @JsonProperty("static")
    STATIC("static"),
    @JsonProperty("datasource")
    DATASOURCE("datasource"),
    @JsonProperty("api")
    API("api");

    private final String value;

    DataType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static DataType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (DataType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown DataType value: " + value);
    }
}
