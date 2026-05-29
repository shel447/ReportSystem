package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
@JsonIgnoreProperties(ignoreUnknown = true)
public class ColumnLineageSource {
    public String dataSourceName;
    public String businessName;
    public String businessName_cn;
    public String field;
    public String enumValues;
    public String ui;
}
