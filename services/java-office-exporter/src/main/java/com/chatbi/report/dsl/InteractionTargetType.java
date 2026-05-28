package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum InteractionTargetType {
    @JsonProperty("filter")
    FILTER,
    @JsonProperty("jump")
    JUMP,
    @JsonProperty("highlight")
    HIGHLIGHT
}
