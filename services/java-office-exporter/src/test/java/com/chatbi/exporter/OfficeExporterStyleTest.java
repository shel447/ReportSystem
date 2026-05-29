package com.chatbi.exporter;

import com.chatbi.exporter.conf.CoverMetaPosition;
import com.chatbi.exporter.conf.DocumentExportConfiguration;
import com.chatbi.exporter.conf.TableHeaderBackground;
import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.docx.ReportDocxExporter;
import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;
import com.chatbi.exporter.pptx.DeckPptxExporter;
import com.chatbi.exporter.util.DslReader;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.util.Units;
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
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class OfficeExporterStyleTest {
    @TempDir
    Path tempDir;

    @Test
    void documentExportConfigurationDefaultsCollectExporterStyleDefaults() {
        DocumentExportConfiguration configuration = DocumentExportConfiguration.defaults();

        assertEquals(null, configuration.global().themeOverride());
        assertFalse(configuration.global().strictValidation());
        assertEquals(CoverMetaPosition.BOTTOM_RIGHT, configuration.word().cover().metaPosition());
        assertTrue(configuration.word().cover().keepMetaOnFirstPage());
        assertTrue(configuration.word().toc().enabled());
        assertEquals(0.05, configuration.word().toc().topOffsetRatio(), 0.0001);
        assertTrue(configuration.word().toc().linkEnabled());
        assertTrue(configuration.word().table().fitToPage());
        assertFalse(configuration.word().table().repeatHeaderOnPageBreak());
        assertEquals("无数据", configuration.word().table().emptyText());
        assertEquals(TableHeaderBackground.THEME_PRIMARY_SOFT, configuration.word().table().headerBackground());
        assertFalse(configuration.ppt().master().showAccentLines());
        assertFalse(configuration.ppt().textBox().showBorder());
        assertTrue(configuration.ppt().table().fitToSlide());
        assertEquals(24, configuration.ppt().table().safeMarginPx());
        assertEquals(15.0, configuration.ppt().table().preferredRowHeightPx(), 0.0001);
        assertEquals(10.0, configuration.ppt().table().minRowHeightPx(), 0.0001);
        assertEquals(18.0, configuration.ppt().table().maxRowHeightPx(), 0.0001);
        assertEquals(7.5, configuration.ppt().table().headerFontSize(), 0.0001);
        assertEquals(6.5, configuration.ppt().table().bodyFontSize(), 0.0001);
        assertEquals(1.5, configuration.ppt().table().cellInsetPt(), 0.0001);
    }

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
    void biEngineNormalizerUsesBasicInfoReportTypeBeforeShapeHints() throws Exception {
        Path pagedInput = tempDir.resolve("paged-with-catalogs.json");
        Path flowInput = tempDir.resolve("flow-with-content.json");
        Path output = tempDir.resolve("paged-with-catalogs.pptx");
        Files.writeString(pagedInput, pagedDslWithCatalogsAndReportTypePpt(), StandardCharsets.UTF_8);
        Files.writeString(flowInput, flowDslWithContentAndReportTypeWord(), StandardCharsets.UTF_8);

        VDoc pagedDoc = DslReader.read(pagedInput);
        VDoc flowDoc = DslReader.read(flowInput);

        assertEquals("ppt", pagedDoc.docType);
        assertEquals("report", flowDoc.docType);
        new DeckPptxExporter().export(pagedDoc, output, ExportRequest.defaults());
        assertTrue(zipEntry(output, "ppt/slides/slide1.xml").contains("这是 PPT 页面"));
        assertEquals("", zipEntry(output, "word/document.xml"));
    }

    @Test
    void cliAutoRejectsOutputExtensionThatConflictsWithDslReportType() throws Exception {
        Path input = tempDir.resolve("paged-with-catalogs.json");
        Path output = tempDir.resolve("wrong-extension.docx");
        Files.writeString(input, pagedDslWithCatalogsAndReportTypePpt(), StandardCharsets.UTF_8);

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> CliMain.main(new String[]{"--input", input.toString(), "--output", output.toString()})
        );
        assertTrue(error.getMessage().contains("Output extension conflicts with DSL report type"));
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
        String stylesXml = zipEntry(output, "word/styles.xml");
        assertTrue(documentXml.contains("1 运营分析"));
        assertTrue(documentXml.contains("1.1 异常归因"));
        assertTrue(documentXml.contains("2 建议"));
        assertTrue(documentXml.contains("<w:hyperlink w:anchor=\"rs_cat_1_"));
        assertTrue(documentXml.contains("<w:hyperlink w:anchor=\"rs_cat_1_1_"));
        assertTrue(documentXml.contains("<w:bookmarkStart"));
        assertTrue(documentXml.contains("w:name=\"rs_cat_1_"));
        assertTrue(documentXml.contains("w:name=\"rs_cat_1_1_"));
        assertTrue(spacingAfterValues(documentXml).stream().anyMatch(value -> value >= 360 && value < 900));
        assertFalse(documentXml.contains("<w:spacing w:after=\"900\""));
        assertHeadingParagraph(documentXml, "1 运营分析", "Heading1", "0");
        assertHeadingParagraph(documentXml, "1.1 异常归因", "Heading2", "1");
        assertHeadingSpacingBefore(documentXml, "1 运营分析", 360);
        assertHeadingSpacingBefore(documentXml, "1.1 异常归因", 240);
        assertTrue(stylesXml.contains("w:styleId=\"Heading1\""));
        assertTrue(stylesXml.contains("w:styleId=\"Heading2\""));
        assertTrue(stylesXml.contains("w:before=\"360\""));
        assertTrue(stylesXml.contains("w:before=\"240\""));
        assertTrue(documentXml.contains("正文一"));
        assertTrue(documentXml.contains("正文二"));
        assertFalse(documentXml.contains("不要显示的章节标题"));
        assertFalse(documentXml.contains("隐藏的二级章节"));
    }

    @Test
    void docxCoverUsesFullPageLayoutWithBottomRightAuthorAndDate() throws Exception {
        Path output = tempDir.resolve("cover-layout.docx");

        new ReportDocxExporter().export(coverReport(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("经营分析报告"));
        assertTrue(documentXml.contains("报告人：张三"));
        assertTrue(documentXml.contains("时间：2026年5月28日"));
        assertFalse(documentXml.contains("张三 | 2026年5月28日"));
        assertTrue(documentXml.contains("<w:trHeight"));
        assertTrue(documentXml.contains("<w:cantSplit"));
        assertTrue(documentXml.contains("<w:vAlign w:val=\"bottom\""));
        assertTrue(documentXml.contains("<w:jc w:val=\"right\""));
        assertFalse(documentXml.contains("<w:ind w:left=\"720\""));
        assertFalse(documentXml.contains("<w:br w:type=\"page\""));
        assertTrue(documentXml.contains("<w:pageBreakBefore"));
        assertBeforeCoverPageBreakControl(documentXml, "报告人：张三");
        assertBeforeCoverPageBreakControl(documentXml, "时间：2026年5月28日");
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
        assertAnchorInsideFirstTable(documentXml);
        assertFalse(documentXml.contains("<w:br w:type=\"page\""));
        assertTrue(documentXml.contains("<w:pageBreakBefore"));
        assertBeforeCoverPageBreakControl(documentXml, "报告人：张三");
        assertBeforeCoverPageBreakControl(documentXml, "时间：2026年5月28日");
        assertTrue(relsXml.contains("image"));
    }

    @Test
    void docxFlatSectionTocEntriesLinkToSectionHeadings() throws Exception {
        Path output = tempDir.resolve("flat-section-toc.docx");

        VDoc doc = textOnlyReport();
        doc.root.props = Map.of(
                "coverEnabled", false,
                "tocShow", true,
                "summaryEnabled", false,
                "signatureEnabled", false,
                "headerShow", false,
                "footerShow", false
        );
        new ReportDocxExporter().export(doc, output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("<w:hyperlink w:anchor=\"rs_section_"));
        assertTrue(documentXml.contains("<w:bookmarkStart"));
        assertHeadingParagraph(documentXml, "正文章节", "Heading1", "0");
        assertHeadingSpacingBefore(documentXml, "正文章节", 360);
        assertTrue(documentXml.contains("正文章节"));
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
        assertFalse(documentXml.contains("<w:tblHeader"));
    }

    @Test
    void docxEmptyTablesRenderMergedNoDataRowWithoutRepeatedHeader() throws Exception {
        Path output = tempDir.resolve("empty-table.docx");

        new ReportDocxExporter().export(emptyTableReport(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("无数据"));
        assertTrue(documentXml.contains("<w:gridSpan w:val=\"3\""));
        assertFalse(documentXml.contains("<w:tblHeader"));
    }

    @Test
    void compositeTablesStaySingleNodeWithTableChildren() throws Exception {
        Path input = tempDir.resolve("composite-flow.json");
        Files.writeString(input, compositeFlowDsl(), StandardCharsets.UTF_8);

        VDoc doc = DslReader.read(input);
        VNode composite = doc.root.children.getFirst().children.getFirst().children.getFirst();

        assertEquals("compositeTable", composite.kind);
        assertEquals(2, composite.children.size());
        assertEquals("table", composite.children.get(0).kind);
        assertEquals("table", composite.children.get(1).kind);
    }

    @Test
    void docxCompositeTablesRenderContiguouslyWithAlignedTotalWidth() throws Exception {
        Path input = tempDir.resolve("composite-flow.json");
        Path output = tempDir.resolve("composite-flow.docx");
        Files.writeString(input, compositeFlowDsl(), StandardCharsets.UTF_8);

        new ReportDocxExporter().export(DslReader.read(input), output, ExportRequest.defaults());

        try (InputStream inputStream = Files.newInputStream(output);
             XWPFDocument document = new XWPFDocument(inputStream)) {
            assertEquals(1, document.getTables().size());
        }

        String documentXml = zipEntry(output, "word/document.xml");
        Matcher tableMatcher = Pattern.compile("<w:tbl>.*?</w:tbl>", Pattern.DOTALL).matcher(documentXml);
        List<String> tables = new ArrayList<>();
        while (tableMatcher.find()) {
            tables.add(tableMatcher.group());
        }
        assertEquals(1, tables.size());

        String tableXml = tables.get(0);
        assertTrue(tableWidth(tableXml) > 0);
        assertEquals(6, countMatches(tableXml, "<w:gridCol"));
        assertTrue(tableXml.contains("<w:gridSpan w:val=\"2\""));
        assertTrue(tableXml.contains("<w:gridSpan w:val=\"3\""));
        assertTrue(countMatches(tableXml, "w:fill=\"DBEAFE\"") >= 5);
        assertTrue(tableXml.contains("官网"));
        assertTrue(tableXml.contains("经销商"));
        assertFalse(tableXml.contains("<w:tblHeader"));
    }

    @Test
    void docxCompositeTablesRenderEmptySegmentsAsMergedNoDataRows() throws Exception {
        Path output = tempDir.resolve("empty-composite.docx");

        new ReportDocxExporter().export(emptyCompositeTableReport(), output, ExportRequest.defaults());

        String documentXml = zipEntry(output, "word/document.xml");
        assertTrue(documentXml.contains("无数据"));
        assertTrue(documentXml.contains("<w:gridSpan w:val=\"6\""));
        assertFalse(documentXml.contains("<w:tblHeader"));
    }

    @Test
    void pptxCompositeTablesRenderStackedWithAlignedTotalWidth() throws Exception {
        Path input = tempDir.resolve("composite-paged.json");
        Path output = tempDir.resolve("composite-paged.pptx");
        Files.writeString(input, compositePagedDsl(), StandardCharsets.UTF_8);

        new DeckPptxExporter().export(DslReader.read(input), output, ExportRequest.defaults());

        String slideXml = zipEntry(output, "ppt/slides/slide1.xml");
        List<TableAnchor> anchors = tableAnchors(slideXml);
        assertEquals(2, anchors.size());
        assertEquals(anchors.get(0).x(), anchors.get(1).x());
        assertEquals(anchors.get(0).width(), anchors.get(1).width());
        assertEquals(anchors.get(0).y() + anchors.get(0).height(), anchors.get(1).y());
        assertTrue(anchors.get(1).height() > 0);
    }

    @Test
    void pptxTablesUseCompactDefaultsAndStayInsideSlide() throws Exception {
        Path output = tempDir.resolve("three-compact-tables.pptx");

        new DeckPptxExporter().export(threeCompactTablesDeck(), output, ExportRequest.defaults());

        String slideXml = zipEntry(output, "ppt/slides/slide1.xml");
        List<TableAnchor> anchors = tableAnchors(slideXml);
        assertEquals(3, anchors.size());
        long slideWidth = Units.toEMU(960);
        long slideHeight = Units.toEMU(540);
        long compactHeight = Units.toEMU(170);
        for (TableAnchor anchor : anchors) {
            assertTrue(anchor.x() >= 0, anchor.toString());
            assertTrue(anchor.y() >= 0, anchor.toString());
            assertTrue(anchor.x() + anchor.width() <= slideWidth, anchor.toString());
            assertTrue(anchor.y() + anchor.height() <= slideHeight, anchor.toString());
            assertTrue(anchor.height() <= compactHeight, anchor.toString());
        }
        assertFalse(overlaps(anchors.get(0), anchors.get(1)));
        assertFalse(overlaps(anchors.get(0), anchors.get(2)));
        assertFalse(overlaps(anchors.get(1), anchors.get(2)));
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
        props.put("coverContents", List.of(
                "封面图背景不应占用正文流高度",
                "报告人和时间必须仍停留在首页",
                "即使封面说明有多行，也不能把元信息挤到第二页"
        ));
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

    private static VDoc emptyTableReport() {
        VDoc doc = new VDoc();
        doc.docId = "empty-table";
        doc.docType = "report";
        doc.schemaVersion = "1.0.0";
        doc.title = "空表测试";

        VNode table = new VNode();
        table.id = "empty-table";
        table.kind = "table";
        table.props = Map.of(
                "columns", List.of(
                        Map.of("key", "region", "title", "区域"),
                        Map.of("key", "revenue", "title", "收入"),
                        Map.of("key", "profit", "title", "利润")
                ),
                "rows", List.of()
        );

        VNode section = new VNode();
        section.id = "section";
        section.kind = "section";
        section.props = Map.of("title", "空表章节");
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
                "footerShow", false
        );
        root.children = List.of(section);
        doc.root = root;
        return doc;
    }

    private static VDoc emptyCompositeTableReport() {
        VDoc doc = new VDoc();
        doc.docId = "empty-composite";
        doc.docType = "report";
        doc.schemaVersion = "1.0.0";
        doc.title = "组合空表测试";

        VNode emptyTable = new VNode();
        emptyTable.id = "empty-segment";
        emptyTable.kind = "table";
        emptyTable.props = Map.of(
                "columns", List.of(
                        Map.of("key", "channel", "title", "渠道"),
                        Map.of("key", "orders", "title", "订单数")
                ),
                "rows", List.of()
        );

        VNode dataTable = new VNode();
        dataTable.id = "data-segment";
        dataTable.kind = "table";
        dataTable.props = Map.of(
                "columns", List.of(
                        Map.of("key", "channel", "title", "渠道"),
                        Map.of("key", "revenue", "title", "收入"),
                        Map.of("key", "profit", "title", "利润")
                ),
                "rows", List.of(Map.of("channel", "官网", "revenue", 1280, "profit", 320))
        );

        VNode composite = new VNode();
        composite.id = "composite";
        composite.kind = "compositeTable";
        composite.children = List.of(emptyTable, dataTable);

        VNode section = new VNode();
        section.id = "section";
        section.kind = "section";
        section.props = Map.of("title", "组合空表章节");
        section.children = List.of(composite);

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

    private static VDoc threeCompactTablesDeck() {
        VDoc doc = new VDoc();
        doc.docId = "three-compact-tables";
        doc.docType = "ppt";
        doc.schemaVersion = "1.0.0";
        doc.title = "三表紧凑布局";

        VNode slide = new VNode();
        slide.id = "slide";
        slide.kind = "slide";
        slide.props = Map.of("title", "三表紧凑布局");
        slide.children = List.of(
                compactTable("left_top", 46, 72, 410, 190),
                compactTable("right_top", 504, 72, 410, 190),
                compactTable("bottom", 46, 292, 868, 210)
        );

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

    private static VNode compactTable(String id, int x, int y, int w, int h) {
        VNode table = new VNode();
        table.id = id;
        table.kind = "table";
        table.layout = Map.of("mode", "absolute", "x", x, "y", y, "w", w, "h", h);
        table.props = Map.of(
                "columns", List.of(
                        Map.of("key", "metric", "title", "指标", "width", 120),
                        Map.of("key", "current", "title", "当前值", "width", 90, "align", "right"),
                        Map.of("key", "target", "title", "目标值", "width", 90, "align", "right"),
                        Map.of("key", "status", "title", "状态", "width", 80)
                ),
                "rows", compactRows(id)
        );
        return table;
    }

    private static List<Map<String, Object>> compactRows(String prefix) {
        ArrayList<Map<String, Object>> rows = new ArrayList<>();
        for (int i = 1; i <= 10; i++) {
            rows.add(Map.of(
                    "metric", prefix + "-指标" + i,
                    "current", 80 + i,
                    "target", 95,
                    "status", i % 3 == 0 ? "关注" : "正常"
            ));
        }
        return rows;
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

    private static String compositeFlowDsl() {
        return """
                {
                  "structureType": "flow",
                  "basicInfo": {"id": "composite-flow", "name": "组合表格验证", "schemaVersion": "1.0.0"},
                  "layout": {"type": "flow", "grid": {"gap": 12}},
                  "catalogs": [
                    {
                      "id": "cat_composite",
                      "name": "组合表格",
                      "order": 1,
                      "sections": [
                        {
                          "id": "sec_composite",
                          "title": "不应输出为小标题",
                          "order": 1,
                          "components": [
                            {
                              "id": "composite_sales",
                              "type": "compositeTable",
                              "dataProperties": {"dataType": "static", "title": "渠道经营组合表"},
                              "tables": [
                                {
                                  "id": "online_table",
                                  "type": "table",
                                  "dataProperties": {
                                    "dataType": "static",
                                    "columns": [
                                      {"key": "channel", "title": "渠道"},
                                      {"key": "revenue", "title": "收入"},
                                      {"key": "profit", "title": "利润"}
                                    ],
                                    "data": [
                                      {"channel": "官网", "revenue": 1280, "profit": 320},
                                      {"channel": "小程序", "revenue": 960, "profit": 210}
                                    ]
                                  }
                                },
                                {
                                  "id": "offline_table",
                                  "type": "table",
                                  "dataProperties": {
                                    "dataType": "static",
                                    "columns": [
                                      {"key": "channel", "title": "渠道"},
                                      {"key": "orders", "title": "订单数"}
                                    ],
                                    "data": [
                                      {"channel": "门店", "orders": 310},
                                      {"channel": "经销商", "orders": 180}
                                    ]
                                  }
                                }
                              ]
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
                """;
    }

    private static String compositePagedDsl() {
        return """
                {
                  "structureType": "paged",
                  "basicInfo": {"id": "composite-paged", "name": "组合表格验证PPT", "schemaVersion": "1.0.0"},
                  "layout": {"type": "paged", "page": {"size": "16:9"}},
                  "content": [
                    {
                      "id": "slide_composite",
                      "type": "slide",
                      "title": "组合表格",
                      "components": [
                        {
                          "id": "composite_ppt",
                          "type": "compositeTable",
                          "layout": {"type": "absolute", "x": 80, "y": 90, "w": 760, "h": 300},
                          "dataProperties": {"dataType": "static", "title": "渠道经营组合表"},
                          "tables": [
                            {
                              "id": "online_table",
                              "type": "table",
                              "dataProperties": {
                                "dataType": "static",
                                "columns": [
                                  {"key": "channel", "title": "渠道"},
                                  {"key": "revenue", "title": "收入"},
                                  {"key": "profit", "title": "利润"}
                                ],
                                "data": [
                                  {"channel": "官网", "revenue": 1280, "profit": 320},
                                  {"channel": "小程序", "revenue": 960, "profit": 210}
                                ]
                              }
                            },
                            {
                              "id": "offline_table",
                              "type": "table",
                              "dataProperties": {
                                "dataType": "static",
                                "columns": [
                                  {"key": "channel", "title": "渠道"},
                                  {"key": "orders", "title": "订单数"}
                                ],
                                "data": [
                                  {"channel": "门店", "orders": 310},
                                  {"channel": "经销商", "orders": 180}
                                ]
                              }
                            }
                          ]
                        }
                      ]
                    }
                  ]
                }
                """;
    }

    private static String pagedDslWithCatalogsAndReportTypePpt() {
        return """
                {
                  "structureType": "flow",
                  "basicInfo": {
                    "id": "paged-with-catalogs",
                    "name": "按 reportType 路由的 PPT",
                    "schemaVersion": "1.0.0",
                    "reportType": "PPT"
                  },
                  "catalogs": [
                    {
                      "id": "cat_should_not_win",
                      "name": "不应作为 Word 目录",
                      "sections": [
                        {
                          "id": "sec_should_not_win",
                          "components": [
                            {"id": "wrong_text", "type": "text", "dataProperties": {"content": "不应导出到 Word"}}
                          ]
                        }
                      ]
                    }
                  ],
                  "content": [
                    {
                      "id": "slide_report_type",
                      "type": "slide",
                      "title": "ReportType PPT",
                      "components": [
                        {
                          "id": "ppt_text",
                          "type": "text",
                          "layout": {"type": "absolute", "x": 80, "y": 120, "w": 720, "h": 80},
                          "dataProperties": {"content": "这是 PPT 页面"}
                        }
                      ]
                    }
                  ]
                }
                """;
    }

    private static String flowDslWithContentAndReportTypeWord() {
        return """
                {
                  "structureType": "paged",
                  "basicInfo": {
                    "id": "flow-with-content",
                    "name": "按 reportType 路由的 Word",
                    "schemaVersion": "1.0.0",
                    "reportType": "Word"
                  },
                  "content": [
                    {
                      "id": "slide_should_not_win",
                      "type": "slide",
                      "title": "不应作为 PPT"
                    }
                  ],
                  "catalogs": [
                    {
                      "id": "cat_report_type",
                      "name": "Word 目录",
                      "sections": [
                        {
                          "id": "sec_report_type",
                          "components": [
                            {"id": "word_text", "type": "text", "dataProperties": {"content": "这是 Word 正文"}}
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

    private static void assertBeforeCoverPageBreakControl(String documentXml, String text) {
        int textIndex = documentXml.indexOf(text);
        int pageBreakIndex = documentXml.indexOf("<w:pageBreakBefore");
        assertTrue(textIndex >= 0, text);
        assertTrue(pageBreakIndex >= 0);
        assertTrue(textIndex < pageBreakIndex, text);
    }

    private static void assertAnchorInsideFirstTable(String documentXml) {
        int tableStart = documentXml.indexOf("<w:tbl>");
        int tableEnd = documentXml.indexOf("</w:tbl>", tableStart);
        int anchor = documentXml.indexOf("<wp:anchor");
        assertTrue(tableStart >= 0);
        assertTrue(tableEnd > tableStart);
        assertTrue(anchor > tableStart && anchor < tableEnd);
    }

    private static void assertHeadingParagraph(String documentXml, String text, String styleId, String outlineLevel) {
        String paragraph = paragraphContaining(documentXml, text, true);
        assertTrue(paragraph.contains("<w:pStyle w:val=\"" + styleId + "\""), paragraph);
        assertTrue(paragraph.contains("<w:outlineLvl w:val=\"" + outlineLevel + "\""), paragraph);
    }

    private static void assertHeadingSpacingBefore(String documentXml, String text, int minimumTwips) {
        String paragraph = paragraphContaining(documentXml, text, true);
        Matcher matcher = Pattern.compile("<w:spacing[^>]*w:before=\"(\\d+)\"").matcher(paragraph);
        assertTrue(matcher.find(), paragraph);
        assertTrue(Integer.parseInt(matcher.group(1)) >= minimumTwips, paragraph);
    }

    private static String paragraphContaining(String documentXml, String text, boolean requireBookmark) {
        Matcher matcher = Pattern.compile("<w:p[ >].*?</w:p>", Pattern.DOTALL).matcher(documentXml);
        while (matcher.find()) {
            String paragraph = matcher.group();
            if (paragraph.contains(text) && (!requireBookmark || paragraph.contains("<w:bookmarkStart"))) {
                return paragraph;
            }
        }
        return "";
    }

    private static List<Integer> spacingAfterValues(String documentXml) {
        Matcher matcher = Pattern.compile("<w:spacing[^>]*w:after=\"(\\d+)\"").matcher(documentXml);
        List<Integer> values = new ArrayList<>();
        while (matcher.find()) {
            values.add(Integer.parseInt(matcher.group(1)));
        }
        return values;
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

    private static int tableWidth(String tableXml) {
        Matcher matcher = Pattern.compile("<w:tblW[^>]*w:w=\"(\\d+)\"[^>]*w:type=\"dxa\"").matcher(tableXml);
        return matcher.find() ? Integer.parseInt(matcher.group(1)) : -1;
    }

    private static int countMatches(String text, String pattern) {
        int count = 0;
        int index = 0;
        while ((index = text.indexOf(pattern, index)) >= 0) {
            count++;
            index += pattern.length();
        }
        return count;
    }

    private static List<TableAnchor> tableAnchors(String slideXml) {
        Matcher matcher = Pattern.compile(
                "<p:graphicFrame>.*?<a:off x=\"(\\d+)\" y=\"(\\d+)\"/>\\s*<a:ext cx=\"(\\d+)\" cy=\"(\\d+)\"/>.*?<a:tbl>",
                Pattern.DOTALL
        ).matcher(slideXml);
        List<TableAnchor> anchors = new ArrayList<>();
        while (matcher.find()) {
            anchors.add(new TableAnchor(
                    Long.parseLong(matcher.group(1)),
                    Long.parseLong(matcher.group(2)),
                    Long.parseLong(matcher.group(3)),
                    Long.parseLong(matcher.group(4))
            ));
        }
        return anchors;
    }

    private static boolean overlaps(TableAnchor first, TableAnchor second) {
        return first.x() < second.x() + second.width()
                && first.x() + first.width() > second.x()
                && first.y() < second.y() + second.height()
                && first.y() + first.height() > second.y();
    }

    private record TableAnchor(long x, long y, long width, long height) {
    }
}
