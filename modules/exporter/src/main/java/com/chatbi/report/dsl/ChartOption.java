package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ChartOption {
    public String centerText;
    public String subCenterText;
    public Map<String, Object> eChartOption;
    public ResponsiveConfig responsive;
}
