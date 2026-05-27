package com.bi.report.generation;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import com.bi.report.generation.core.ExportRequest;
import com.bi.report.generation.docx.ReportDocxExporter;
import com.bi.report.generation.model.ReportDslModel;
import com.bi.report.generation.pptx.ReportPptxExporter;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class ShowcaseOutputTest {

    @Test
    void generateShowcaseFiles() throws Exception {
        ObjectMapper mapper = new ObjectMapper();
        Path outDir = Path.of("showcase-out");
        Files.createDirectories(outDir);

        try (InputStream flowIs = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel flowModel = mapper.readValue(flowIs, ReportDslModel.class);
            Path docxPath = outDir.resolve("showcase-flow.docx");
            new ReportDocxExporter().export(flowModel, docxPath, new ExportRequest("enterprise-light", false));
            assertTrue(Files.exists(docxPath));
            long size = Files.size(docxPath);
            assertTrue(size > 5000, "DOCX should be > 5KB, got " + size);
            System.out.println("DOCX: " + docxPath.toAbsolutePath() + " (" + size + " bytes)");
        }

        try (InputStream pagedIs = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel pagedModel = mapper.readValue(pagedIs, ReportDslModel.class);
            Path pptxPath = outDir.resolve("showcase-paged.pptx");
            new ReportPptxExporter().export(pagedModel, pptxPath, new ExportRequest("enterprise-light", false));
            assertTrue(Files.exists(pptxPath));
            long size = Files.size(pptxPath);
            assertTrue(size > 3000, "PPTX should be > 3KB, got " + size);
            System.out.println("PPTX: " + pptxPath.toAbsolutePath() + " (" + size + " bytes)");
        }

        try (InputStream flowIs = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel flowModel = mapper.readValue(flowIs, ReportDslModel.class);
            Path docxDark = outDir.resolve("showcase-flow-dark.docx");
            new ReportDocxExporter().export(flowModel, docxDark, new ExportRequest("enterprise-dark", false));
            assertTrue(Files.exists(docxDark));
            System.out.println("DOCX (dark): " + docxDark.toAbsolutePath() + " (" + Files.size(docxDark) + " bytes)");
        }

        try (InputStream pagedIs = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel pagedModel = mapper.readValue(pagedIs, ReportDslModel.class);
            Path pptxDark = outDir.resolve("showcase-paged-dark.pptx");
            new ReportPptxExporter().export(pagedModel, pptxDark, new ExportRequest("enterprise-dark", false));
            assertTrue(Files.exists(pptxDark));
            System.out.println("PPTX (dark): " + pptxDark.toAbsolutePath() + " (" + Files.size(pptxDark) + " bytes)");
        }

        System.out.println("All showcase files generated successfully!");
    }
}
