package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum Status {
    @JsonProperty("Running")
    RUNNING("Running"),
    @JsonProperty("Success")
    SUCCESS("Success"),
    @JsonProperty("Aborted")
    ABORTED("Aborted"),
    @JsonProperty("Failed")
    FAILED("Failed");

    private final String value;

    Status(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static Status fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (Status item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown Status value: " + value);
    }
}
