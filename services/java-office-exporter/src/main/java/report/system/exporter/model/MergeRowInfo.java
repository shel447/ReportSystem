package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class MergeRowInfo {
    @JsonProperty("startRowIndex")
    public int startRowIndex;

    @JsonProperty("rowSpan")
    public int rowSpan;

    @JsonProperty("column")
    public String column;

    @JsonProperty("mergedText")
    public String mergedText;
}
