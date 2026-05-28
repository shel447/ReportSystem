package com.bi.report.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

/**
 * Generated Report DSL contract model.
 * <p>These classes mirror design/report_system/schemas/report-dsl.schema.json
 * and are intentionally not wired into the current exporter runtime.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class ResponsiveConfig {
    @JsonProperty("enabled")
    public Boolean enabled;

    @JsonProperty("levels")
    public List<ResponsiveLevelConfig> levels;

    @JsonProperty("aspectRatio")
    public Double aspectRatio;

    @JsonProperty("minHeight")
    public Double minHeight;

}
