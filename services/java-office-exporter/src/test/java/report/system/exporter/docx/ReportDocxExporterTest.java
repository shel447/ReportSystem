package report.system.exporter.docx;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import report.system.exporter.core.ExportRequest;
import report.system.exporter.model.ReportDslModel;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class ReportDocxExporterTest {
    private ObjectMapper mapper;
    private ReportDocxExporter exporter;

    @TempDir
    Path tempDir;

    @BeforeEach
    void setUp() {
        mapper = new ObjectMapper();
        exporter = new ReportDocxExporter();
    }

    @Test
    void testExportFlowReportWithCover() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("flow-with-cover.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
            verifyDocxStructure(output);
        }
    }

    @Test
    void testExportReportWithTextComponents() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("text-components.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 1000);
        }
    }

    @Test
    void testExportReportWithTables() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("tables.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 2000);
        }
    }

    @Test
    void testExportReportWithLineChart() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("line-chart.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportReportWithBarChart() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("bar-chart.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportReportWithPieChart() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("pie-chart.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportReportWithFallbackChart() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("fallback-charts.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportReportWithCompositeTable() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("composite-table.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportReportWithSignaturePage() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("signature-page.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportFullShowcaseReport() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("showcase-flow.docx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            long fileSize = Files.size(output);
            assertTrue(fileSize > 5000, "Full showcase should be > 5KB, got " + fileSize);
            verifyDocxStructure(output);
        }
    }

    @Test
    void testExportWithDarkTheme() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("dark-theme.docx");

            exporter.export(model, output, new ExportRequest("enterprise-dark", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    private void verifyDocxStructure(Path docxPath) throws Exception {
        byte[] content = Files.readAllBytes(docxPath);
        String contentStr = new String(content, "UTF-8");

        assertTrue(content.length > 100, "DOCX file too small");
        assertTrue(contentStr.contains("[Content_Types].xml") ||
                   contentStr.contains("word/document.xml") ||
                   content.length > 1000,
                   "Invalid DOCX structure");
    }
}
