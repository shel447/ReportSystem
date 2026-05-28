package com.chatbi.report.dsl;

import java.util.List;

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
