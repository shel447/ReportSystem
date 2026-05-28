package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class SlideSection implements PagedContentItem {
    public String id;
    public SlideSectionType type;
    public String title;
    public String description;
    public List<Slide> slides;
}
