package com.chatbi.report.dsl;

import java.util.List;

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
