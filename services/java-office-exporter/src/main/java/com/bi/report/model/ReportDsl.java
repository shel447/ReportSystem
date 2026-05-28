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
public class ReportDsl {
    @JsonProperty("structureType")
    public String structureType;

    @JsonProperty("basicInfo")
    public BasicInfo basicInfo;

    @JsonProperty("cover")
    public Cover cover;

    @JsonProperty("backCover")
    public BackCoverConfig backCover;

    @JsonProperty("signaturePage")
    public SignaturePage signaturePage;

    @JsonProperty("catalogs")
    public List<Catalog> catalogs;

    @JsonProperty("summary")
    public ReportSummary summary;

    @JsonProperty("reportMeta")
    public ReportMeta reportMeta;

    @JsonProperty("layout")
    public PageLayout layout;

    @JsonProperty("content")
    public PagedContent content;

}
