package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum DisplayPriority {
    @JsonProperty("high")
    HIGH,
    @JsonProperty("normal")
    NORMAL,
    @JsonProperty("never")
    NEVER
}
