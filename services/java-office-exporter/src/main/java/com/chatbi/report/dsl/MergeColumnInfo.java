package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class MergeColumnInfo {
    public String title;
    public List<String> columns;
    public Boolean isMergeValue;
}
