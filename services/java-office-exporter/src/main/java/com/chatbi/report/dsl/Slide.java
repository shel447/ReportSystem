package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Slide implements PagedContentItem {
    public String id;
    public String title;
    public String description;
    public PageLayout layout;
    public List<BIEngineComponent> components;
}
