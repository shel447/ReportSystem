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
public class TablePaginationProperties {
    @JsonProperty("showPagination")
    public Boolean showPagination;

    @JsonProperty("defaultDisplayRows")
    public Double defaultDisplayRows;

    @JsonProperty("pageSizeOptions")
    public List<Double> pageSizeOptions;

}
