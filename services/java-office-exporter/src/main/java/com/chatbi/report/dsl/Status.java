package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum Status {
    @JsonProperty("Running")
    RUNNING,
    @JsonProperty("Success")
    SUCCESS,
    @JsonProperty("Aborted")
    ABORTED,
    @JsonProperty("Failed")
    FAILED
}
