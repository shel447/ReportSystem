package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ResponsiveSize {
    @JsonProperty("standard")
    STANDARD,
    @JsonProperty("compact")
    COMPACT
}
