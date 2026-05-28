package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class MergeRowInfo {
    public Integer startRowIndex;
    public Integer rowSpan;
    public String column;
    public String mergedText;
}
