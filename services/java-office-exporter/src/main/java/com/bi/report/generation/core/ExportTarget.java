package com.bi.report.generation.core;

public enum ExportTarget {
    DOCX,
    PPTX;

    public static ExportTarget fromFormat(String format) {
        if (format == null) throw new IllegalArgumentException("format is null");
        return switch (format.trim().toLowerCase()) {
            case "word", "docx" -> DOCX;
            case "ppt", "pptx" -> PPTX;
            default -> throw new IllegalArgumentException("Unsupported format: " + format);
        };
    }

    public String extension() {
        return switch (this) {
            case DOCX -> ".docx";
            case PPTX -> ".pptx";
        };
    }

    public String contentType() {
        return switch (this) {
            case DOCX -> "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
            case PPTX -> "application/vnd.openxmlformats-officedocument.presentationml.presentation";
        };
    }
}
