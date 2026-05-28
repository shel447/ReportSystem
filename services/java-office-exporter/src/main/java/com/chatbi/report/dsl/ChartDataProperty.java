package com.chatbi.report.dsl;

import java.util.List;
import java.util.Map;

public class ChartDataProperty extends CommonDataProperty {
    public List<Column> columns;
    public List<Map<String, Object>> data;
    public List<Series> series;
    public List<String> axisGroup;
    public Object xAxis;
    public Object yAxis;
}
