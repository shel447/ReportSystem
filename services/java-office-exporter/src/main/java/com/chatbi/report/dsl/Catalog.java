package com.chatbi.report.dsl;

import java.util.List;

public class Catalog {
    public String id;
    public String name;
    public Double order;
    public List<Catalog> subCatalogs;
    public List<Section> sections;
}
