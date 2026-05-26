package report.system.exporter.core;

import report.system.exporter.model.ReportDslModel;

import java.io.IOException;
import java.nio.file.Path;

public interface DocumentExporter {
    ExportTarget target();

    boolean supports(ReportDslModel dsl);

    void export(ReportDslModel dsl, Path output, ExportRequest request) throws IOException;
}
