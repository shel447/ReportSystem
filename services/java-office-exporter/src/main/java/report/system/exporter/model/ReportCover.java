package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportCover {
    @JsonProperty("title")
    public String title;

    @JsonProperty("author")
    public String author;

    @JsonProperty("date")
    public String date;

    @JsonProperty("layoutTemplate")
    public String layoutTemplate;

    @JsonProperty("image")
    public String image;

    @JsonProperty("contents")
    public List<ReportCoverContent> contents;

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ReportCoverContent {
        @JsonProperty("type")
        public String type;

        @JsonProperty("content")
        public String content;

        @JsonProperty("elementId")
        public String elementId;
    }
}
