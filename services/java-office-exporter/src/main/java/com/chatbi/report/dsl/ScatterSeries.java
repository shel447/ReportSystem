package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ScatterSeries implements Series {
    public SeriesType type;
    public XYEncode encode;
    public String name;
}
