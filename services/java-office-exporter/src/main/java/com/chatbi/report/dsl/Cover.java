package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Cover {
    public String title;
    public String subTitle;
    public String author;
    public String date;
    public CoverLayoutType layoutTemplate;
    public String image;
    public List<CoverContent> contents;
}
