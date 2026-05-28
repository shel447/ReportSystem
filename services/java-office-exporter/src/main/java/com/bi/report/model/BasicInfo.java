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
public class BasicInfo {
    @JsonProperty("id")
    public String id;

    @JsonProperty("schemaVersion")
    public String schemaVersion;

    @JsonProperty("mode")
    public String mode;

    @JsonProperty("status")
    public Status status;

    @JsonProperty("name")
    public String name;

    @JsonProperty("reportType")
    public ReportType reportType;

    @JsonProperty("title")
    public String title;

    @JsonProperty("description")
    public String description;

    @JsonProperty("templateId")
    public String templateId;

    @JsonProperty("templateName")
    public String templateName;

    @JsonProperty("remark")
    public String remark;

    @JsonProperty("version")
    public String version;

    @JsonProperty("createDate")
    public String createDate;

    @JsonProperty("modifyDate")
    public String modifyDate;

    @JsonProperty("createdAt")
    public String createdAt;

    @JsonProperty("updatedAt")
    public String updatedAt;

    @JsonProperty("creator")
    public String creator;

    @JsonProperty("modifier")
    public String modifier;

    @JsonProperty("header")
    public String header;

    @JsonProperty("footer")
    public String footer;

    @JsonProperty("category")
    public String category;

    @JsonProperty("parameters")
    public Map<String, Parameter> parameters;

}
