package com.chatbi.report.dsl;

import java.util.List;

public class SlideSection implements PagedContentItem {
    public String id;
    public SlideSectionType type;
    public String title;
    public String description;
    public List<Slide> slides;
}
