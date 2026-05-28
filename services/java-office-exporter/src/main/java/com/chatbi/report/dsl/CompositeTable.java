package com.chatbi.report.dsl;

import java.util.List;

public class CompositeTable implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public CompositeTableBasicProperties basicProperties;
    public CompositeTableAdvanceProperties advanceProperties;
    public CompositeTableDataProperty dataProperties;
    public List<TableComponent> tables;
    public List<Interaction> interactions;
}
