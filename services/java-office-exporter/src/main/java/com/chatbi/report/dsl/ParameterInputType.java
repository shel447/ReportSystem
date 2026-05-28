package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ParameterInputType {
    @JsonProperty("free_text")
    FREE_TEXT,
    @JsonProperty("date")
    DATE,
    @JsonProperty("enum")
    ENUM,
    @JsonProperty("dynamic")
    DYNAMIC
}
