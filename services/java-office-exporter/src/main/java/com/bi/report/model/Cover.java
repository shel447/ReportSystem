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
public class Cover {
    @JsonProperty("title")
    public String title;

    @JsonProperty("subTitle")
    public String subTitle;

    @JsonProperty("author")
    public String author;

    @JsonProperty("date")
    public String date;

    @JsonProperty("layoutTemplate")
    public CoverLayoutType layoutTemplate;

    @JsonProperty("image")
    public String image;

    @JsonProperty("contents")
    public List<CoverContent> contents;

}
