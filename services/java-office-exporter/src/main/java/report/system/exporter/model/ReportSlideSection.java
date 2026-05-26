package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSlideSection extends ReportPagedContentItem {
    @JsonProperty("slides")
    public List<ReportSlide> slides;
}
