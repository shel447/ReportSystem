package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GridDefinition {
    @JsonProperty("cols")
    public int cols;

    @JsonProperty("rowHeight")
    public int rowHeight;

    @JsonProperty("gap")
    public Integer gap;
}
