package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum AxisType {
    @JsonProperty("category")
    CATEGORY,
    @JsonProperty("value")
    VALUE
}
