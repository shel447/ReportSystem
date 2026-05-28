package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum LayoutType {
    @JsonProperty("grid")
    GRID,
    @JsonProperty("flow")
    FLOW,
    @JsonProperty("absolute")
    ABSOLUTE
}
