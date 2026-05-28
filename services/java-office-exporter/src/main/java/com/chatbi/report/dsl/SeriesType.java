package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum SeriesType {
    @JsonProperty("line")
    LINE,
    @JsonProperty("bar")
    BAR,
    @JsonProperty("pie")
    PIE,
    @JsonProperty("scatter")
    SCATTER,
    @JsonProperty("radar")
    RADAR,
    @JsonProperty("gauge")
    GAUGE,
    @JsonProperty("candlestick")
    CANDLESTICK
}
