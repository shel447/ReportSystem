package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ChartAdvanceProperties {
    public String centerText;
    public String subCenterText;
    public Map<String, Object> eChartOption;
    public ResponsiveConfig responsive;
    public String xAxisLabelMode;
    public String sqlExplanation;
}
