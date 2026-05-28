package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class BasicInfo {
    public String id;
    public String schemaVersion;
    public Mode mode;
    public String name;
    public String title;
    public String description;
    public String templateId;
    public String templateName;
    public String version;
    public Status status;
    public ReportType reportType;
    public String category;
    public String creator;
    public String modifier;
    public String createdAt;
    public String updatedAt;
    public String createDate;
    public String modifyDate;
    public String header;
    public String footer;
    public String remark;
    public Map<String, Parameter> parameters;
}
