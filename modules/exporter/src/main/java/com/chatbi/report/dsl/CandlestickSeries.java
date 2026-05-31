package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CandlestickSeries implements Series {
    public SeriesType type;
    public CandlestickEncode encode;
    public String name;
}
