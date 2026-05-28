package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TableDataProperty extends CommonDataProperty {
    public List<Column> columns;
    public List<Map<String, Object>> data;
    public Boolean hasMerge;
    public List<MergeColumnInfo> mergeColumns;
    public List<MergeRowInfo> mergeRows;
}
