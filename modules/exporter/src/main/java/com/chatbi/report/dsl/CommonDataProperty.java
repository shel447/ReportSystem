package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CommonDataProperty {
    public DataType dataType;
    public String sourceId;
    public String url;
    public HttpMethod method;
    public Boolean autoRefresh;
    public Double refreshInterval;
    public String title;
}
