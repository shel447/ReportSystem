package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.Map;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class PageLayout {
    @JsonProperty("type")
    public LayoutType type;

    @JsonProperty("autoLayout")
    public Boolean autoLayout;

    @JsonProperty("grid")
    public Map<String, Object> grid;

}
