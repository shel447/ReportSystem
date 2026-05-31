package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;

public enum AdditionalInfoType {
    @JsonProperty("Prompt")
    PROMPT("Prompt"),
    @JsonProperty("Summary")
    SUMMARY("Summary"),
    @JsonProperty("SQL")
    SQL("SQL"),
    @JsonProperty("API")
    API("API"),
    @JsonProperty("Knowledge")
    KNOWLEDGE("Knowledge");

    private final String value;

    AdditionalInfoType(String value) {
        this.value = value;
    }

    @JsonValue
    public String value() {
        return value;
    }

    @JsonCreator
    public static AdditionalInfoType fromValue(String value) {
        if (value == null) {
            return null;
        }
        for (AdditionalInfoType item : values()) {
            if (item.value.equals(value)) {
                return item;
            }
        }
        throw new IllegalArgumentException("Unknown AdditionalInfoType value: " + value);
    }
}
