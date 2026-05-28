package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum UITrigger {
    @JsonProperty("click")
    CLICK,
    @JsonProperty("dblclick")
    DBLCLICK,
    @JsonProperty("hover")
    HOVER
}
