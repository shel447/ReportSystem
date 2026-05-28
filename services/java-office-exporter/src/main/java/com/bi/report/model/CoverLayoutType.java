package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonProperty;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
public enum CoverLayoutType {
    @JsonProperty("TITLE_TOP")
    TITLE_TOP,
    @JsonProperty("TITLE_CENTER")
    TITLE_CENTER;
}
