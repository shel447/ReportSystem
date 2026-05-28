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
public class CandlestickSeries {
    @JsonProperty("type")
    public String type;

    @JsonProperty("encode")
    public Map<String, Object> encode;

    @JsonProperty("name")
    public String name;

}
