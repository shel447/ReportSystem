package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type", defaultImpl = ReportSlide.class, visible = true)
@JsonSubTypes({
        @JsonSubTypes.Type(value = ReportSlideSection.class, name = "section"),
})
public abstract class ReportPagedContentItem {
    @JsonProperty("id")
    public String id;

    @JsonProperty("type")
    public String type;

    @JsonProperty("title")
    public String title;

    @JsonProperty("description")
    public String description;
}
