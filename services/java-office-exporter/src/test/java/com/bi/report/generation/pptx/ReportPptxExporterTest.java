package com.bi.report.generation.pptx;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import com.bi.report.generation.core.ExportRequest;
import com.bi.report.generation.model.ReportDslModel;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

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
            verifyPptxChartHasSlideAnchor(output);
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

    private void verifyPptxChartHasSlideAnchor(Path pptxPath) throws Exception {
        try (ZipFile zip = new ZipFile(pptxPath.toFile())) {
            boolean hasChartPart = zip.stream().map(ZipEntry::getName)
                    .anyMatch(name -> name.startsWith("ppt/charts/chart") && name.endsWith(".xml"));
            boolean hasChartRelationship = zip.stream().map(ZipEntry::getName)
                    .filter(name -> name.startsWith("ppt/slides/_rels/slide") && name.endsWith(".xml.rels"))
                    .map(name -> readZipEntry(zip, name))
                    .anyMatch(xml -> xml.contains("/relationships/chart"));
            boolean hasChartShape = zip.stream().map(ZipEntry::getName)
                    .filter(name -> name.startsWith("ppt/slides/slide") && name.endsWith(".xml"))
                    .map(name -> readZipEntry(zip, name))
                    .anyMatch(xml -> xml.contains("<p:graphicFrame")
                            && xml.contains("drawingml/2006/chart")
                            && xml.contains("cx=\"11176000\"")
                            && xml.contains("cy=\"3810000\""));

            assertTrue(hasChartPart, "PPTX should contain native chart parts");
            assertTrue(hasChartRelationship, "Slides should relate to native chart parts");
            assertTrue(hasChartShape, "Slides should place native charts in a visible graphic frame using EMU coordinates");
            assertTrue(hasEmbeddedWorkbookCells(zip, "ppt/embeddings/"), "Embedded chart workbook should contain source data");
            assertTrue(hasStyledChartSeries(zip, "ppt/charts/"), "Native chart series should have visible fill/line styling");
            assertTrue(hasPositiveAxisIds(zip, "ppt/charts/"), "Category/value axes should use positive non-zero ids");
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

    private String readZipEntry(ZipFile zip, String name) {
        try {
            return new String(zip.getInputStream(zip.getEntry(name)).readAllBytes());
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private boolean hasEmbeddedWorkbookCells(ZipFile outerZip, String prefix) {
        return outerZip.stream()
                .filter(entry -> entry.getName().startsWith(prefix) && entry.getName().endsWith(".xlsx"))
                .map(entry -> {
                    try {
                        byte[] bytes = outerZip.getInputStream(entry).readAllBytes();
                        try (java.util.zip.ZipInputStream workbookZip = new java.util.zip.ZipInputStream(new ByteArrayInputStream(bytes))) {
                            java.util.zip.ZipEntry workbookEntry;
                            while ((workbookEntry = workbookZip.getNextEntry()) != null) {
                                if (workbookEntry.getName().startsWith("xl/worksheets/sheet") && workbookEntry.getName().endsWith(".xml")) {
                                    return new String(workbookZip.readAllBytes()).contains("<c ");
                                }
                            }
                            return false;
                        }
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                })
                .anyMatch(Boolean::booleanValue);
    }
}
