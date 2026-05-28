package com.chatbi.exporter;

import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.docx.ReportDocxExporter;
import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;
import com.chatbi.exporter.pptx.DeckPptxExporter;
import com.chatbi.exporter.util.DslReader;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
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

    @Test
    void docxCatalogsRenderNumberedTocAndContentWithoutSectionTitles() throws Exception {
        Path input = tempDir.resolve("catalog-flow.json");
        Path output = tempDir.resolve("catalog-flow.docx");
        Files.writeString(input, catalogFlowDsl(), StandardCharsets.UTF_8);

        VDoc doc = DslReader.read(input);
        assertEquals("catalog", doc.root.children.getFirst().kind);
        assertEquals("1", doc.root.children.getFirst().propString("outlineNumber", ""));
        assertEquals("section", doc.root.children.getFirst().children.getFirst().kind);

        new ReportDocxExporter().export(doc, output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("1 运营分析"));
        assertTrue(documentXml.contains("1.1 异常归因"));
        assertTrue(documentXml.contains("2 建议"));
        assertTrue(documentXml.contains("正文一"));
        assertTrue(documentXml.contains("正文二"));
        assertFalse(documentXml.contains("不要显示的章节标题"));
        assertFalse(documentXml.contains("隐藏的二级章节"));
    }

    @Test
    void docxCoverUsesFullPageLayoutWithBottomLeftAuthorAndDate() throws Exception {
        Path output = tempDir.resolve("cover-layout.docx");

        new ReportDocxExporter().export(coverReport(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("经营分析报告"));
        assertTrue(documentXml.contains("报告人：张三"));
        assertTrue(documentXml.contains("时间：2026年5月28日"));
        assertFalse(documentXml.contains("张三 | 2026年5月28日"));
        assertTrue(documentXml.contains("<w:trHeight"));
        assertTrue(documentXml.contains("<w:vAlign w:val=\"bottom\""));
        assertTrue(documentXml.contains("<w:ind w:left=\"720\""));
    }

    @Test
    void docxCoverImageRendersAsFullPageBackgroundBehindText() throws Exception {
        Path output = tempDir.resolve("cover-background.docx");

        new ReportDocxExporter().export(coverReportWithImage(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        String relsXml = zipEntry(output, "word/_rels/document.xml.rels");
        assertTrue(documentXml.contains("<wp:anchor"));
        assertTrue(documentXml.contains("behindDoc=\"true\""));
        assertTrue(documentXml.contains("<wp:positionH relativeFrom=\"page\"><wp:posOffset>0</wp:posOffset></wp:positionH>"));
        assertTrue(documentXml.contains("<wp:positionV relativeFrom=\"page\"><wp:posOffset>0</wp:posOffset></wp:positionV>"));
        assertTrue(documentXml.contains("<wp:extent cx=\"7560310\" cy=\"10692130\""));
        assertTrue(documentXml.contains("背景封面"));
        assertTrue(relsXml.contains("image"));
    }

    @Test
    void docxWideTablesUseFixedWidthsInsideWritablePage() throws Exception {
        Path output = tempDir.resolve("wide-table.docx");

        new ReportDocxExporter().export(wideTableReport(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("w:type=\"fixed\""));
        assertTrue(documentXml.contains("w:type=\"dxa\""));

        Matcher tableWidth = Pattern.compile("<w:tblW[^>]*w:w=\"(\\d+)\"[^>]*w:type=\"dxa\"").matcher(documentXml);
        assertTrue(tableWidth.find());
        int availableWidth = Integer.parseInt(tableWidth.group(1));
        assertTrue(availableWidth <= 10320);

        Matcher gridCol = Pattern.compile("<w:gridCol[^>]*w:w=\"(\\d+)\"").matcher(documentXml);
        int gridWidth = 0;
        int gridColumns = 0;
        while (gridCol.find()) {
            gridWidth += Integer.parseInt(gridCol.group(1));
            gridColumns++;
        }
        assertEquals(12, gridColumns);
        assertTrue(gridWidth <= availableWidth);
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

    private static VDoc coverReport() {
        VDoc doc = new VDoc();
        doc.docId = "cover-layout";
        doc.docType = "report";
        doc.schemaVersion = "1.0.0";
        doc.title = "封面布局测试";

        VNode text = new VNode();
        text.id = "text";
        text.kind = "text";
        text.props = Map.of("text", "正文");

        VNode section = new VNode();
        section.id = "section";
        section.kind = "section";
        section.props = Map.of("title", "正文");
        section.children = List.of(text);

        VNode root = new VNode();
        root.id = "root";
        root.kind = "container";
        root.props = Map.of(
                "coverEnabled", true,
                "coverTitle", "经营分析报告",
                "coverSubtitle", "月度经营复盘",
                "coverAuthor", "张三",
                "coverDate", "2026年5月28日",
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

    private static VDoc coverReportWithImage() {
        VDoc doc = coverReport();
        doc.docId = "cover-background";
        doc.title = "背景封面";
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        props.put("coverEnabled", true);
        props.put("coverTitle", "背景封面");
        props.put("coverSubtitle", "图片铺满首页");
        props.put("coverAuthor", "张三");
        props.put("coverDate", "2026年5月28日");
        props.put("coverImage", "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=");
        props.put("tocShow", false);
        props.put("summaryEnabled", false);
        props.put("signatureEnabled", false);
        props.put("headerShow", false);
        props.put("footerShow", false);
        doc.root.props = props;
        return doc;
    }

    private static VDoc wideTableReport() {
        VDoc doc = new VDoc();
        doc.docId = "wide-table";
        doc.docType = "report";
        doc.schemaVersion = "1.0.0";
        doc.title = "宽表测试";

        List<Map<String, Object>> columns = new ArrayList<>();
        Map<String, Object> row = new LinkedHashMap<>();
        for (int i = 1; i <= 12; i++) {
            String key = "c" + i;
            columns.add(Map.of("key", key, "title", "指标列" + i, "width", 160));
            row.put(key, "长文本值-" + i);
        }

        VNode table = new VNode();
        table.id = "wide-table";
        table.kind = "table";
        table.props = Map.of("columns", columns, "rows", List.of(row));

        VNode section = new VNode();
        section.id = "section";
        section.kind = "section";
        section.props = Map.of("title", "宽表章节");
        section.children = List.of(table);

        VNode root = new VNode();
        root.id = "root";
        root.kind = "container";
        root.props = Map.of(
                "coverEnabled", false,
                "tocShow", false,
                "summaryEnabled", false,
                "signatureEnabled", false,
                "headerShow", false,
                "footerShow", false,
                "pageSize", "A4",
                "marginPreset", "normal"
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

    private static String catalogFlowDsl() {
        return """
                {
                  "structureType": "flow",
                  "basicInfo": {"id": "catalog-flow", "name": "目录层级测试", "schemaVersion": "1.0.0"},
                  "layout": {"type": "flow", "grid": {"gap": 8}},
                  "catalogs": [
                    {
                      "id": "cat_1",
                      "name": "运营分析",
                      "order": 1,
                      "sections": [
                        {
                          "id": "sec_1",
                          "title": "不要显示的章节标题",
                          "order": 1,
                          "components": [
                            {"id": "text_1", "type": "text", "dataProperties": {"content": "正文一"}}
                          ]
                        }
                      ],
                      "subCatalogs": [
                        {
                          "id": "cat_1_1",
                          "name": "异常归因",
                          "order": 1,
                          "sections": [
                            {
                              "id": "sec_2",
                              "title": "隐藏的二级章节",
                              "order": 1,
                              "components": [
                                {"id": "text_2", "type": "text", "dataProperties": {"content": "正文二"}}
                              ]
                            }
                          ]
                        }
                      ]
                    },
                    {
                      "id": "cat_2",
                      "name": "建议",
                      "order": 2,
                      "sections": [
                        {
                          "id": "sec_3",
                          "title": "建议章节标题不展示",
                          "order": 1,
                          "components": [
                            {"id": "text_3", "type": "text", "dataProperties": {"content": "正文三"}}
                          ]
                        }
                      ]
                    }
                  ]
                }
                """;
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
