package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportBasicInfo {
    @JsonProperty("id")
    public String id;

    @JsonProperty("schemaVersion")
    public String schemaVersion;

    @JsonProperty("name")
    public String name;

    @JsonProperty("title")
    public String title;

    @JsonProperty("subTitle")
    public String subTitle;

    @JsonProperty("description")
    public String description;

    @JsonProperty("version")
    public String version;

    @JsonProperty("status")
    public String status;

    @JsonProperty("mode")
    public String mode;

    @JsonProperty("templateId")
    public String templateId;

    @JsonProperty("templateName")
    public String templateName;

    @JsonProperty("header")
    public String header;

    @JsonProperty("footer")
    public String footer;

    @JsonProperty("category")
    public String category;

    @JsonProperty("creator")
    public String creator;

    @JsonProperty("modifier")
    public String modifier;

    @JsonProperty("createDate")
    public String createDate;

    @JsonProperty("modifyDate")
    public String modifyDate;

    @JsonProperty("createdAt")
    public String createdAt;

    @JsonProperty("updatedAt")
    public String updatedAt;

    @JsonProperty("remark")
    public String remark;

    @JsonProperty("parameters")
    public Map<String, Object> parameters;
}
