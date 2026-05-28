package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Catalog {
    public String id;
    public String name;
    public Double order;
    public List<Catalog> subCatalogs;
    public List<Section> sections;
}
