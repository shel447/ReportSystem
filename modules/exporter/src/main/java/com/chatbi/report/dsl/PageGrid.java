package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PageGrid {
    public Integer cols;
    public Double rowHeight;
    public Double gap;
    public Double paddingX;
    public Double paddingTop;
    public Double paddingBottom;
}
