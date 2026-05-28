package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class BarSeries implements Series {
    public SeriesType type;
    public BarSubType subType;
    public String stack;
    public XYEncode encode;
    public String name;
}
