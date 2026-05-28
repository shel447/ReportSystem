package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum FieldType {
    @JsonProperty("string")
    STRING,
    @JsonProperty("long")
    LONG,
    @JsonProperty("int")
    INT,
    @JsonProperty("timestamp")
    TIMESTAMP,
    @JsonProperty("double")
    DOUBLE,
    @JsonProperty("float")
    FLOAT,
    @JsonProperty("enum")
    ENUM
}
