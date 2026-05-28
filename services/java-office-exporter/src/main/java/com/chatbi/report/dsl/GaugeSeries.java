package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GaugeSeries implements Series {
    public SeriesType type;
    public ValueEncode encode;
    public String name;
    public GaugeConfig config;
}
