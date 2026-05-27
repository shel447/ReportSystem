package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ExportPayload {
    @JsonProperty("requestId")
    public String requestId;

    @JsonProperty("reportId")
    public String reportId;

    @JsonProperty("dslSchemaVersion")
    public String dslSchemaVersion;

    @JsonProperty("reportDsl")
    public ReportDslModel reportDsl;

    @JsonProperty("options")
    public ExportOptions options;

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ExportOptions {
        @JsonProperty("theme")
        public String theme;

        @JsonProperty("strictValidation")
        public boolean strictValidation;

        @JsonProperty("pdfSource")
        public String pdfSource;
    }
}
