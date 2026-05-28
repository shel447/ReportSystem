package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ValueFormatType {
    @JsonProperty("time")
    TIME,
    @JsonProperty("percentage")
    PERCENTAGE,
    @JsonProperty("number")
    NUMBER,
    @JsonProperty("byte")
    BYTE
}
