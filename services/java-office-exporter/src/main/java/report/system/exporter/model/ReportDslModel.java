package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportDslModel {
    @JsonProperty("structureType")
    public String structureType = "flow";

    @JsonProperty("basicInfo")
    public ReportBasicInfo basicInfo;

    @JsonProperty("cover")
    public ReportCover cover;

    @JsonProperty("backCover")
    public BackCoverConfig backCover;

    @JsonProperty("signaturePage")
    public ReportSignaturePage signaturePage;

    @JsonProperty("catalogs")
    public List<ReportCatalog> catalogs;

    @JsonProperty("layout")
    public ReportLayout layout;

    @JsonProperty("content")
    public List<ReportPagedContentItem> content;

    @JsonProperty("summary")
    public ReportSummary summary;

    @JsonProperty("reportMeta")
    public Map<String, ReportGenerateMeta> reportMeta;
}
