package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class PieSeries implements Series {
    public SeriesType type;
    public PieSubType subType;
    public String centerText;
    public String subCenterText;
    public NameValueEncode encode;
    public String name;
}
