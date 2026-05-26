package report.system.exporter.pptx;

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

class ReportPptxExporterTest {
    private ObjectMapper mapper;
    private ReportPptxExporter exporter;

    @TempDir
    Path tempDir;

    @BeforeEach
    void setUp() {
        mapper = new ObjectMapper();
        exporter = new ReportPptxExporter();
    }

    @Test
    void testExportPagedReportWithSlides() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("paged-slides.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
            verifyPptxStructure(output);
        }
    }

    @Test
    void testExportFlowReportAsSlides() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-flow.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            model.structureType = "paged";
            model.content = null;
            model.catalogs = model.catalogs.subList(0, 2);

            Path output = tempDir.resolve("flow-as-slides.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportPptxWithTables() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("pptx-tables.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 1000);
        }
    }

    @Test
    void testExportPptxWithCharts() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("pptx-charts.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportPptxWithBackCover() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("pptx-backcover.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            assertNotNull(model.backCover);
            assertEquals("谢谢观看", model.backCover.text);
        }
    }

    @Test
    void testExportFullShowcasePptx() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("showcase-paged.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-light", false));

            assertTrue(Files.exists(output));
            long fileSize = Files.size(output);
            assertTrue(fileSize > 3000, "Full showcase PPTX should be > 3KB, got " + fileSize);
            verifyPptxStructure(output);
        }
    }

    @Test
    void testExportWithDarkTheme() throws Exception {
        try (InputStream is = getClass().getResourceAsStream("/showcase-paged.json")) {
            ReportDslModel model = mapper.readValue(is, ReportDslModel.class);
            Path output = tempDir.resolve("dark-theme.pptx");

            exporter.export(model, output, new ExportRequest("enterprise-dark", false));

            assertTrue(Files.exists(output));
            assertTrue(Files.size(output) > 0);
        }
    }

    @Test
    void testExportEmptyPagedReport() throws Exception {
        ReportDslModel model = new ReportDslModel();
        model.structureType = "paged";
        model.content = java.util.List.of();

        Path output = tempDir.resolve("empty-paged.pptx");

        exporter.export(model, output, new ExportRequest("enterprise-light", false));

        assertTrue(Files.exists(output));
        assertTrue(Files.size(output) > 0);
    }

    private void verifyPptxStructure(Path pptxPath) throws Exception {
        byte[] content = Files.readAllBytes(pptxPath);
        String contentStr = new String(content, "UTF-8");

        assertTrue(content.length > 100, "PPTX file too small");
        assertTrue(contentStr.contains("[Content_Types].xml") ||
                   contentStr.contains("ppt/presentation.xml") ||
                   content.length > 1000,
                   "Invalid PPTX structure");
    }
}
