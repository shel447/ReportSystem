package com.chatbi.report.dsl;

import java.util.List;

public class Slide implements PagedContentItem {
    public String id;
    public String title;
    public String description;
    public PageLayout layout;
    public List<BIEngineComponent> components;
}
