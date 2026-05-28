package com.chatbi.report.dsl;

import java.util.List;

public class TableComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public TableBasicProperties basicProperties;
    public TableAdvanceProperties advanceProperties;
    public TableDataProperty dataProperties;
    public List<Interaction> interactions;
}
