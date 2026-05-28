package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum DataType {
    @JsonProperty("static")
    STATIC,
    @JsonProperty("datasource")
    DATASOURCE,
    @JsonProperty("api")
    API
}
