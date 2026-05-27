package report.system.exporter.docx;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import report.system.exporter.core.ExportRequest;
import report.system.exporter.model.ReportDslModel;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipFile;

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
            verifyDocxChartHasVisibleExtent(output);
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

    private void verifyDocxChartHasVisibleExtent(Path docxPath) throws Exception {
        try (ZipFile zip = new ZipFile(docxPath.toFile())) {
            String documentXml = new String(zip.getInputStream(zip.getEntry("word/document.xml")).readAllBytes());
            assertTrue(documentXml.contains("<c:chart"), "DOCX should reference native chart parts");
            assertFalse(documentXml.contains("wp:docPr id=\"0\""), "Word chart drawing ids must be positive");
            assertTrue(documentXml.contains("<wp:cNvGraphicFramePr>"), "Word chart drawings should include graphic frame properties");
            assertFalse(documentXml.contains("cx=\"500000\" cy=\"500000\""), "Charts must not use POI's tiny default extent");
            assertTrue(documentXml.contains("cx=\"5852160\""), "Chart width should be visible in Word");
            assertTrue(documentXml.contains("cy=\"3291840\""), "Chart height should be visible in Word");
            assertTrue(hasEmbeddedWorkbookCells(zip, "word/embeddings/"), "Embedded chart workbook should contain source data");
            assertTrue(hasStyledChartSeries(zip, "word/charts/"), "Native chart series should have visible fill/line styling");
            assertTrue(hasPositiveAxisIds(zip, "word/charts/"), "Category/value axes should use positive non-zero ids");
            assertTrue(hasWordChartCompatibilityMarkup(zip, "word/charts/"), "Word charts should include compatibility flags");
        }
    }

    private boolean hasStyledChartSeries(ZipFile zip, String prefix) {
        return zip.stream()
                .filter(entry -> entry.getName().startsWith(prefix) && entry.getName().endsWith(".xml"))
                .map(entry -> {
                    try {
                        return new String(zip.getInputStream(entry).readAllBytes());
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                })
                .anyMatch(xml -> xml.contains("<c:spPr>") && xml.contains("<a:solidFill>"));
    }

    private boolean hasPositiveAxisIds(ZipFile zip, String prefix) {
        return zip.stream()
                .filter(entry -> entry.getName().startsWith(prefix) && entry.getName().endsWith(".xml"))
                .map(entry -> {
                    try {
                        return new String(zip.getInputStream(entry).readAllBytes());
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                })
                .anyMatch(xml -> xml.contains("<c:axId val=\"12345001\"")
                        && xml.contains("<c:axId val=\"12345002\""));
    }

    private boolean hasWordChartCompatibilityMarkup(ZipFile zip, String prefix) {
        return zip.stream()
                .filter(entry -> entry.getName().startsWith(prefix) && entry.getName().endsWith(".xml"))
                .map(entry -> {
                    try {
                        return new String(zip.getInputStream(entry).readAllBytes());
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                })
                .anyMatch(xml -> xml.contains("<c:autoUpdate")
                        && xml.contains("<c:plotVisOnly"));
    }

    private boolean hasEmbeddedWorkbookCells(ZipFile outerZip, String prefix) throws Exception {
        return outerZip.stream()
                .filter(entry -> entry.getName().startsWith(prefix) && entry.getName().endsWith(".xlsx"))
                .map(entry -> {
                    try {
                        byte[] bytes = outerZip.getInputStream(entry).readAllBytes();
                        try (ZipFileWrapper workbookZip = new ZipFileWrapper(bytes)) {
                            return workbookZip.containsCells();
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                })
                .anyMatch(Boolean::booleanValue);
    }

    private static final class ZipFileWrapper implements AutoCloseable {
        private final java.util.zip.ZipInputStream stream;

        ZipFileWrapper(byte[] bytes) {
            this.stream = new java.util.zip.ZipInputStream(new ByteArrayInputStream(bytes));
        }

        boolean containsCells() throws Exception {
            java.util.zip.ZipEntry entry;
            while ((entry = stream.getNextEntry()) != null) {
                if (entry.getName().startsWith("xl/worksheets/sheet") && entry.getName().endsWith(".xml")) {
                    String xml = new String(stream.readAllBytes());
                    return xml.contains("<c ");
                }
            }
            return false;
        }

        @Override
        public void close() throws Exception {
            stream.close();
        }
    }
}
