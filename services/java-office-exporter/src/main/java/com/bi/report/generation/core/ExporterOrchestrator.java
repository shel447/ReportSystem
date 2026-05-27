package com.bi.report.generation.core;

import com.bi.report.generation.model.ReportDslModel;

import java.io.IOException;
import java.nio.file.Path;
import java.util.EnumMap;
import java.util.List;

public final class ExporterOrchestrator {
    private final EnumMap<ExportTarget, DocumentExporter> exporters = new EnumMap<>(ExportTarget.class);

    public ExporterOrchestrator(List<DocumentExporter> exporterList) {
        for (DocumentExporter e : exporterList) {
            exporters.put(e.target(), e);
        }
    }

    public void export(ReportDslModel dsl, ExportTarget target, Path output, ExportRequest request) throws IOException {
        ExportRequest safeRequest = request != null ? request : ExportRequest.defaults();
        DslValidator.validate(dsl, safeRequest.strictValidation());
        DocumentExporter exporter = exporters.get(target);
        if (exporter == null) {
            throw new IllegalArgumentException("No exporter registered for target: " + target);
        }
        if (!exporter.supports(dsl)) {
            throw new IllegalArgumentException("Exporter " + target + " does not support this DSL");
        }
        exporter.export(dsl, output, safeRequest);
    }
}
