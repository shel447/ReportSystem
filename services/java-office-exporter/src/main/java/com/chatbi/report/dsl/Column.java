package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Column {
    public String title;
    public String key;
    public FieldType type;
    public List<EnumValue> enumConfig;
    public FieldUI uiConfig;
    public ColumnLineageTracing lineageTracing;
    public Double order;
    public Double colSpan;
    public List<Column> children;
    public Boolean sortable;
    public Boolean filterable;
    public Object width;
}
