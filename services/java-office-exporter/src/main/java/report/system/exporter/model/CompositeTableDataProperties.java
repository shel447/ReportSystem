package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CompositeTableDataProperties {
    @JsonProperty("dataType")
    public String dataType;

    @JsonProperty("sourceId")
    public String sourceId;

    @JsonProperty("url")
    public String url;

    @JsonProperty("method")
    public String method;

    @JsonProperty("autoRefresh")
    public Boolean autoRefresh;

    @JsonProperty("refreshInterval")
    public Double refreshInterval;

    @JsonProperty("title")
    public String title;
}
