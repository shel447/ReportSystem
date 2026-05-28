package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum Mode {
    @JsonProperty("draft")
    DRAFT,
    @JsonProperty("published")
    PUBLISHED
}
