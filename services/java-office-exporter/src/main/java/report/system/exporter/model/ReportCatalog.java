package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportCatalog {
    @JsonProperty("id")
    public String id;

    @JsonProperty("name")
    public String name;

    @JsonProperty("title")
    public String title;

    @JsonProperty("description")
    public String description;

    @JsonProperty("order")
    public Integer order;

    @JsonProperty("subCatalogs")
    public List<ReportCatalog> subCatalogs;

    @JsonProperty("sections")
    public List<ReportSection> sections;

    public String resolvedTitle() {
        if (title != null && !title.isBlank()) return title;
        if (name != null && !name.isBlank()) return name;
        return id != null ? id : "";
    }
}
