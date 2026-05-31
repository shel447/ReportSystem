package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class XYEncode {
    public String x;
    public String y;
    public Double xAxisIndex;
    public Double yAxisIndex;
}
