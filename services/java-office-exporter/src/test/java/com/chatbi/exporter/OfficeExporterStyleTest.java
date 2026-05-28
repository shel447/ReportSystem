package com.chatbi.exporter;

import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.docx.ReportDocxExporter;
import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;
import com.chatbi.exporter.pptx.DeckPptxExporter;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OfficeExporterStyleTest {
    @TempDir
    Path tempDir;

    @Test
    void docxTextBlocksRenderAsPlainParagraphs() throws Exception {
        Path output = tempDir.resolve("plain-text.docx");

        new ReportDocxExporter().export(textOnlyReport(), output, ExportRequest.defaults());

        try (InputStream input = Files.newInputStream(output);
             XWPFDocument document = new XWPFDocument(input)) {
            assertEquals(0, document.getTables().size());
            assertTrue(document.getParagraphs().stream()
                    .anyMatch(paragraph -> paragraph.getText().contains("这是一段普通正文")));
        }
    }

    @Test
    void pptxMasterKeepsHeaderFooterTextWithoutAccentLines() throws Exception {
        Path output = tempDir.resolve("no-master-lines.pptx");

        new DeckPptxExporter().export(singleSlideDeck(), output, ExportRequest.defaults());

        String slideXml = zipEntry(output, "ppt/slides/slide1.xml");
        assertTrue(slideXml.contains("页眉"));
        assertTrue(slideXml.contains("页脚"));
        assertTrue(slideXml.contains("#1/1"));
        assertFalse(slideXml.toLowerCase().contains("1d4ed8"));
    }

    @Test
    void pptxTextBoxesDoNotRenderBorders() throws Exception {
        Path output = tempDir.resolve("text-without-border.pptx");

        new DeckPptxExporter().export(textBoxDeck(), output, ExportRequest.defaults());

        String slideXml = zipEntry(output, "ppt/slides/slide1.xml").toLowerCase();
        String textShapeXml = enclosingShape(slideXml, "ppt 正文");
        assertTrue(slideXml.contains("ppt 正文"));
        assertFalse(textShapeXml.contains("<a:ln"));
        assertFalse(textShapeXml.contains("d7e3f7"));
    }

    private static VDoc textOnlyReport() {
        VDoc doc = new VDoc();
        doc.docId = "plain-text";
        doc.docType = "report";
        doc.schemaVersion = "1.0.0";
        doc.title = "纯正文测试";

        VNode text = new VNode();
        text.id = "text";
        text.kind = "text";
        text.props = Map.of("text", "这是一段普通正文");

        VNode section = new VNode();
        section.id = "section";
        section.kind = "section";
        section.props = Map.of("title", "正文章节");
        section.children = List.of(text);

        VNode root = new VNode();
        root.id = "root";
        root.kind = "container";
        root.props = Map.of(
                "coverEnabled", false,
                "tocShow", false,
                "summaryEnabled", false,
                "signatureEnabled", false,
                "headerShow", false,
                "footerShow", false
        );
        root.children = List.of(section);
        doc.root = root;
        return doc;
    }

    private static VDoc singleSlideDeck() {
        VDoc doc = new VDoc();
        doc.docId = "single-slide";
        doc.docType = "ppt";
        doc.schemaVersion = "1.0.0";
        doc.title = "母版样式测试";

        VNode slide = new VNode();
        slide.id = "slide";
        slide.kind = "slide";
        slide.props = Map.of("title", "第一页");

        VNode root = new VNode();
        root.id = "root";
        root.kind = "container";
        root.props = Map.of(
                "masterShowHeader", true,
                "masterHeaderText", "页眉",
                "masterShowFooter", true,
                "masterFooterText", "页脚",
                "masterShowSlideNumber", true,
                "masterAccentColor", "#1d4ed8"
        );
        root.children = List.of(slide);
        doc.root = root;
        return doc;
    }

    private static VDoc textBoxDeck() {
        VDoc doc = new VDoc();
        doc.docId = "text-box";
        doc.docType = "ppt";
        doc.schemaVersion = "1.0.0";
        doc.title = "文本框样式测试";

        VNode text = new VNode();
        text.id = "text";
        text.kind = "text";
        text.props = Map.of("text", "PPT 正文");
        text.layout = Map.of("mode", "absolute", "x", 80, "y", 120, "w", 420, "h", 120);

        VNode slide = new VNode();
        slide.id = "slide";
        slide.kind = "slide";
        slide.props = Map.of("title", "文本框");
        slide.children = List.of(text);

        VNode root = new VNode();
        root.id = "root";
        root.kind = "container";
        root.props = Map.of(
                "masterShowHeader", false,
                "masterShowFooter", false,
                "masterShowSlideNumber", false
        );
        root.children = List.of(slide);
        doc.root = root;
        return doc;
    }

    private static String zipEntry(Path zipPath, String entryName) throws IOException {
        try (ZipFile zip = new ZipFile(zipPath.toFile())) {
            ZipEntry entry = zip.getEntry(entryName);
            if (entry == null) {
                return "";
            }
            try (InputStream input = zip.getInputStream(entry)) {
                return new String(input.readAllBytes(), StandardCharsets.UTF_8);
            }
        }
    }

    private static String enclosingShape(String xml, String text) {
        int textIndex = xml.indexOf(text);
        if (textIndex < 0) {
            return "";
        }
        int shapeStart = xml.lastIndexOf("<p:sp", textIndex);
        int shapeEnd = xml.indexOf("</p:sp>", textIndex);
        if (shapeStart < 0 || shapeEnd < 0) {
            return "";
        }
        return xml.substring(shapeStart, shapeEnd);
    }
}
