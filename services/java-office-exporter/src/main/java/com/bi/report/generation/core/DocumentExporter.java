package com.bi.report.generation.core;

import com.bi.report.generation.model.ReportDslModel;

import java.io.IOException;
import java.nio.file.Path;

public interface DocumentExporter {
    ExportTarget target();

    boolean supports(ReportDslModel dsl);

    void export(ReportDslModel dsl, Path output, ExportRequest request) throws IOException;
}
