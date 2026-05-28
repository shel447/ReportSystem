package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class NumericValueFormat implements ValueFormat {
    public ValueFormatType type;
    public Double decimal;
    public String unit;
}
