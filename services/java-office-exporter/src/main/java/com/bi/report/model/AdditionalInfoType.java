package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
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
    KNOWLEDGE;
}
