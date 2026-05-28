package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
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
    ENUM;
}
