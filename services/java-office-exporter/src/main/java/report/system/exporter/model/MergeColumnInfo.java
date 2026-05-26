package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class MergeColumnInfo {
    @JsonProperty("title")
    public String title;

    @JsonProperty("columns")
    public List<String> columns;
}
