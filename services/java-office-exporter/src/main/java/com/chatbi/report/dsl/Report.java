package com.chatbi.report.dsl;

import java.util.List;
import java.util.Map;

/**
 * Root object for the Report DSL schema.
 */
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
    public List<PagedContentItem> content;
}
