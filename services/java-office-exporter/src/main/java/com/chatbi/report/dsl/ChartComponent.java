package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ChartComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public ChartBasicProperties basicProperties;
    public ChartAdvanceProperties advanceProperties;
    public ChartDataProperty dataProperties;
    public ChartOption options;
    public List<Interaction> interactions;
}
