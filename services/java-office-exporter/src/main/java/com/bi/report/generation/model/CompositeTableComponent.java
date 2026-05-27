package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CompositeTableComponent extends ReportComponent {
    @JsonProperty("tables")
    public List<TableComponent> tables;

    @JsonProperty("dataProperties")
    public CompositeTableDataProperties dataProperties;
}
