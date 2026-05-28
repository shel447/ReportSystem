package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum InteractionMode {
    @JsonProperty("form")
    FORM,
    @JsonProperty("natural_language")
    NATURAL_LANGUAGE
}
