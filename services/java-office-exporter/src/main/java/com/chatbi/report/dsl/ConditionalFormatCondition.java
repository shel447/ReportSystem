package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ConditionalFormatCondition {
    public String op;
    public Double value;
    public Double min;
    public Double max;
}
