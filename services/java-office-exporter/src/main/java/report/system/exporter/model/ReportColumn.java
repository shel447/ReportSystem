package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportColumn {
    @JsonProperty("key")
    public String key;

    @JsonProperty("title")
    public String title;

    @JsonProperty("type")
    public String type;

    @JsonProperty("width")
    public Object width;

    @JsonProperty("sortable")
    public Boolean sortable;

    @JsonProperty("filterable")
    public Boolean filterable;

    @JsonProperty("align")
    public String align;

    @JsonProperty("children")
    public List<ReportColumn> children;
}
