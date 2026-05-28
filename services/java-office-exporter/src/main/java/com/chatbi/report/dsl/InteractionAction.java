package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum InteractionAction {
    @JsonProperty("click")
    CLICK,
    @JsonProperty("hover")
    HOVER,
    @JsonProperty("change")
    CHANGE,
    @JsonProperty("select")
    SELECT
}
