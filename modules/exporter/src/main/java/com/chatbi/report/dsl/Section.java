package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Section {
    public String id;
    public String title;
    public Double order;
    public List<BIEngineComponent> components;
    public ReportSummary summary;
}
