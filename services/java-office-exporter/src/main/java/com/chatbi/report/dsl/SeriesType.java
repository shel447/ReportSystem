package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum SeriesType {
    @JsonProperty("line")
    LINE("line"),
    @JsonProperty("bar")
    BAR("bar"),
    @JsonProperty("pie")
    PIE("pie"),
    @JsonProperty("scatter")
    SCATTER("scatter"),
    @JsonProperty("radar")
    RADAR("radar"),
    @JsonProperty("gauge")
    GAUGE("gauge"),
    @JsonProperty("candlestick")
    CANDLESTICK("candlestick");

    private final String value;

    SeriesType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static SeriesType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (SeriesType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown SeriesType value: " + value);
    }
}
