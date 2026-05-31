package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum ReportType {
    @JsonProperty("PPT")
    PPT("PPT"),
    @JsonProperty("Word")
    WORD("Word"),
    @JsonProperty("Dashboard")
    DASHBOARD("Dashboard");

    private final String value;

    ReportType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static ReportType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (ReportType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown ReportType value: " + value);
    }
}
