package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class LineSeries implements Series {
    public SeriesType type;
    public LineSubType subType;
    public XYEncode encode;
    public String name;
}
