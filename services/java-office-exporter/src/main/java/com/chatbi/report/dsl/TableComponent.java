package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TableComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public TableBasicProperties basicProperties;
    public TableAdvanceProperties advanceProperties;
    public TableDataProperty dataProperties;
    public List<Interaction> interactions;
}
