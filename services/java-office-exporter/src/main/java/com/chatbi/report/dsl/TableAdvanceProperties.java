package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TableAdvanceProperties {
    public Boolean showHeader;
    public Boolean showTitle;
    public TablePaginationProperties pagination;
}
