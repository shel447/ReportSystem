package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class RadarSeries implements Series {
    public SeriesType type;
    public NameValueEncode encode;
    public String name;
}
