package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TablePaginationProperties {
    public Boolean showPagination;
    public Double defaultDisplayRows;
    public List<Double> pageSizeOptions;
}
