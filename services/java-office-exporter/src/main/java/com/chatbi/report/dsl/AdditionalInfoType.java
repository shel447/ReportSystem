package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum AdditionalInfoType {
    @JsonProperty("Prompt")
    PROMPT,
    @JsonProperty("Summary")
    SUMMARY,
    @JsonProperty("SQL")
    SQL,
    @JsonProperty("API")
    API,
    @JsonProperty("Knowledge")
    KNOWLEDGE
}
