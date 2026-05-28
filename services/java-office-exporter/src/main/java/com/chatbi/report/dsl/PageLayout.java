package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PageLayout {
    public LayoutType type;
    public Boolean autoLayout;
    public PageGrid grid;
}
