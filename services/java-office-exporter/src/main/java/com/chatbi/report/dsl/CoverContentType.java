package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum CoverContentType {
    @JsonProperty("image")
    IMAGE,
    @JsonProperty("text")
    TEXT
}
