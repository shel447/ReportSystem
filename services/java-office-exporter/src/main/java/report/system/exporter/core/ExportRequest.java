package report.system.exporter.core;

public record ExportRequest(String theme, boolean strictValidation) {
    public static ExportRequest defaults() {
        return new ExportRequest("enterprise-light", false);
    }
}
