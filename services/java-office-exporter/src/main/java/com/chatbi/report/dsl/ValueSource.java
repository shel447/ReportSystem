package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ValueSource {
    @JsonProperty("user_input")
    USER_INPUT,
    @JsonProperty("default")
    DEFAULT,
    @JsonProperty("parameter_ref")
    PARAMETER_REF,
    @JsonProperty("system_fill")
    SYSTEM_FILL
}
