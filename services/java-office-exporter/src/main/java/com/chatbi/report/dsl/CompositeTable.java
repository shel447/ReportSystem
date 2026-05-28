package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
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
