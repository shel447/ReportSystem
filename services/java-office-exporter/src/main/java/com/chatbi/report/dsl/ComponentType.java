package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum ComponentType {
    @JsonProperty("text")
    TEXT,
    @JsonProperty("table")
    TABLE,
    @JsonProperty("chart")
    CHART,
    @JsonProperty("markdown")
    MARKDOWN,
    @JsonProperty("compositeTable")
    COMPOSITE_TABLE
}
