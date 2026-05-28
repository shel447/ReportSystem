package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import java.util.List;
import java.util.Map;

/**
 * Root object for the Report DSL schema.
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Report {
    public StructureType structureType;
    public BasicInfo basicInfo;
    public Cover cover;
    public BackCoverConfig backCover;
    public SignaturePage signaturePage;
    public List<Catalog> catalogs;
    public ReportSummary summary;
    public Map<String, GenerateMeta> reportMeta;
    public PageLayout layout;
    @JsonDeserialize(contentUsing = PagedContentItemDeserializer.class)
    public List<PagedContentItem> content;
}
