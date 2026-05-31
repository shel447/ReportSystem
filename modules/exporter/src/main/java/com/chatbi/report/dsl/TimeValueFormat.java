package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TimeValueFormat implements ValueFormat {
    public ValueFormatType type;
    public String format;
}
