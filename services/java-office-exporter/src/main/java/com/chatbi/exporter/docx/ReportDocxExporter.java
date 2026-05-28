package com.chatbi.exporter.docx;

import com.chatbi.exporter.chart.ChartSpec;
import com.chatbi.exporter.chart.ChartSpecParser;
import com.chatbi.exporter.chart.PoiChartRenderer;
import com.chatbi.exporter.chart.ChartRowResolver;
import com.chatbi.exporter.chart.ChartTypeCatalog;
import com.chatbi.exporter.core.DocumentExporter;
import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.core.ExportTarget;
import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;
import com.chatbi.exporter.render.NodeRenderer;
import com.chatbi.exporter.render.RendererRegistry;
import com.chatbi.exporter.style.DefaultStyleResolver;
import com.chatbi.exporter.style.StyleResolver;
import com.chatbi.exporter.style.ThemeTokens;
import com.chatbi.exporter.style.VisualStyle;
import com.chatbi.exporter.table.TableCell;
import com.chatbi.exporter.table.TableModel;
import com.chatbi.exporter.table.TableSpecParser;
import org.apache.poi.xwpf.model.XWPFHeaderFooterPolicy;
import org.apache.poi.xwpf.usermodel.ParagraphAlignment;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFFooter;
import org.apache.poi.xwpf.usermodel.XWPFHeader;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.apache.poi.xwpf.usermodel.XWPFChart;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageMar;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageSz;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSectPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTcPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTrPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSimpleField;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STMerge;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STHdrFtr;

import java.awt.Color;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * Report -> DOCX 导出器。
 * 负责把报告 DSL 渲染为可商用的 Word 文档结构：封面、目录、正文、总结、页眉页脚、图表与表格。
 */
public class ReportDocxExporter implements DocumentExporter {
    private final StyleResolver styleResolver;
    private final ChartSpecParser chartSpecParser;
    private final ChartRowResolver chartRowResolver;
    private final PoiChartRenderer poiChartRenderer;
    private final TableSpecParser tableSpecParser;
    private final List<DocxChartFlavorRenderer> chartFlavorRenderers;
    private final RendererRegistry<DocxRenderContext> nodeRenderers;

    /**
     * 默认构造：使用内置样式解析与图表规格解析。
     */
    public ReportDocxExporter() {
        this(new DefaultStyleResolver(), new ChartSpecParser());
    }

    /**
     * 允许注入样式/图表解析器，便于测试与扩展。
     */
    public ReportDocxExporter(StyleResolver styleResolver, ChartSpecParser chartSpecParser) {
        this.styleResolver = styleResolver;
        this.chartSpecParser = chartSpecParser;
        this.chartRowResolver = new ChartRowResolver();
        this.poiChartRenderer = new PoiChartRenderer();
        this.tableSpecParser = new TableSpecParser();
        this.chartFlavorRenderers = new ArrayList<>();
        registerChartFlavorRenderer(new TrendFlavorRenderer());
        registerChartFlavorRenderer(new ComparisonFlavorRenderer());
        registerChartFlavorRenderer(new CompositionFlavorRenderer());
        registerChartFlavorRenderer(new RelationFlavorRenderer());
        registerChartFlavorRenderer(new MatrixFlavorRenderer());
        registerChartFlavorRenderer(new TimeWindowFlavorRenderer());
        registerChartFlavorRenderer(new CustomFlavorRenderer());
        registerChartFlavorRenderer(new TableFlavorRenderer());
        registerChartFlavorRenderer(new GenericFlavorRenderer());
        this.nodeRenderers = new RendererRegistry<>(new UnsupportedNodeRenderer())
                .register(new TextNodeRenderer())
                .register(new ChartNodeRenderer())
                .register(new TableNodeRenderer());
    }

    /**
     * 注册图表风味渲染器（按 fallback 之前插入）。
     */
    public ReportDocxExporter registerChartFlavorRenderer(DocxChartFlavorRenderer renderer) {
        DocxChartFlavorRenderer safe = Objects.requireNonNull(renderer, "renderer");
        int fallbackIndex = findFallbackIndex();
        if (fallbackIndex >= 0) {
            chartFlavorRenderers.add(fallbackIndex, safe);
        } else {
            chartFlavorRenderers.add(safe);
        }
        return this;
    }

    /**
     * 定位通用兜底渲染器下标，保证后续注册可插入在其前面。
     */
    private int findFallbackIndex() {
        for (int i = 0; i < chartFlavorRenderers.size(); i++) {
            if (chartFlavorRenderers.get(i) instanceof GenericFlavorRenderer) {
                return i;
            }
        }
        return -1;
    }

    @Override
    public ExportTarget target() {
        return ExportTarget.DOCX;
    }

    @Override
    public boolean supports(VDoc doc) {
        return doc != null && "report".equalsIgnoreCase(doc.docType);
    }

    /**
     * 兼容旧调用方式（不传 request）。
     */
    public void export(VDoc doc, Path output) throws IOException {
        export(doc, output, ExportRequest.defaults());
    }

    /**
     * DOCX 导出主流程：
     * 1) 解析主题与页面参数
     * 2) 生成封面/目录/正文/总结页
     * 3) 写入输出文件
     */
    @Override
    public void export(VDoc doc, Path output, ExportRequest request) throws IOException {
        if (!supports(doc)) {
            throw new IllegalArgumentException("ReportDocxExporter only accepts report docType.");
        }
        if (output.getParent() != null) {
            Files.createDirectories(output.getParent());
        }

        try (XWPFDocument document = new XWPFDocument()) {
            Map<String, Object> props = doc.root == null ? Collections.emptyMap() : doc.root.propsOrEmpty();
            ThemeTokens theme = styleResolver.resolve(doc, request);
            DocxRenderContext context = new DocxRenderContext(document, theme, chartSpecParser, props, doc);

            configurePage(document, props);
            setupHeaderFooter(document, props, str(props.get("reportTitle"), defaultReportTitle(doc)), theme);

            boolean coverEnabled = bool(props.get("coverEnabled"), true);
            boolean tocShow = bool(props.get("tocShow"), true);
            boolean summaryEnabled = bool(props.get("summaryEnabled"), true);
            List<VNode> sections = sectionNodes(doc.root);

            if (coverEnabled) {
                addCoverPage(context, props, doc);
            }
            if (tocShow) {
                addTocPage(context, sections);
            }
            addContentPages(context, sections, props);
            if (summaryEnabled) {
                addSummaryPage(context, props, sections);
            }
            if (bool(props.get("signatureEnabled"), false)) {
                addSignaturePage(context, props);
            }

            try (OutputStream out = Files.newOutputStream(output)) {
                document.write(out);
            }
        }
    }

    /**
     * 配置纸张尺寸与页边距（A4/Letter）。
     */
    private void configurePage(XWPFDocument document, Map<String, Object> props) {
        String pageSize = str(props.get("pageSize"), "A4");
        CTSectPr sectPr = document.getDocument().getBody().isSetSectPr()
                ? document.getDocument().getBody().getSectPr()
                : document.getDocument().getBody().addNewSectPr();
        CTPageSz sz = sectPr.isSetPgSz() ? sectPr.getPgSz() : sectPr.addNewPgSz();
        CTPageMar mar = sectPr.isSetPgMar() ? sectPr.getPgMar() : sectPr.addNewPgMar();

        if ("Letter".equalsIgnoreCase(pageSize)) {
            sz.setW(BigInteger.valueOf(12240));
            sz.setH(BigInteger.valueOf(15840));
        } else {
            sz.setW(BigInteger.valueOf(11906));
            sz.setH(BigInteger.valueOf(16838));
        }

        PageMargins margins = resolvePageMargins(props);
        mar.setTop(BigInteger.valueOf(margins.topTwips()));
        mar.setBottom(BigInteger.valueOf(margins.bottomTwips()));
        mar.setLeft(BigInteger.valueOf(margins.leftTwips()));
        mar.setRight(BigInteger.valueOf(margins.rightTwips()));
    }

    /**
     * 配置页眉页脚与页码。
     */
    private void setupHeaderFooter(XWPFDocument document, Map<String, Object> props, String reportTitle, ThemeTokens theme) {
        boolean headerShow = bool(props.get("headerShow"), true);
        boolean footerShow = bool(props.get("footerShow"), true);
        boolean showPageNumber = bool(props.get("showPageNumber"), true);
        String headerText = str(props.get("headerText"), reportTitle);
        String footerText = str(props.get("footerText"), "Visual Document OS");

        XWPFHeaderFooterPolicy policy = document.createHeaderFooterPolicy();
        if (headerShow) {
            XWPFHeader header = policy.createHeader(STHdrFtr.DEFAULT);
            XWPFParagraph p = header.createParagraph();
            p.setAlignment(ParagraphAlignment.LEFT);
            XWPFRun run = p.createRun();
            run.setText(headerText);
            run.setFontFamily(theme.fontPrimary());
            run.setFontSize(10);
            run.setColor(VisualStyle.toHexNoHash(theme.muted()));
        }

        if (footerShow) {
            XWPFFooter footer = policy.createFooter(STHdrFtr.DEFAULT);
            XWPFParagraph p = footer.createParagraph();
            p.setAlignment(ParagraphAlignment.LEFT);
            XWPFRun run = p.createRun();
            run.setText(footerText);
            run.setFontFamily(theme.fontPrimary());
            run.setFontSize(10);
            run.setColor(VisualStyle.toHexNoHash(theme.muted()));

            if (showPageNumber) {
                XWPFRun sep = p.createRun();
                sep.setText(" | Page ");
                sep.setFontFamily(theme.fontPrimary());
                sep.setFontSize(10);
                sep.setColor(VisualStyle.toHexNoHash(theme.muted()));
                CTSimpleField field = p.getCTP().addNewFldSimple();
                field.setInstr("PAGE");
            }
        }
    }

    /**
     * 生成封面页。
     */
    private void addCoverPage(DocxRenderContext context, Map<String, Object> props, VDoc doc) {
        String reportTitle = str(props.get("reportTitle"), defaultReportTitle(doc));
        String coverTitle = str(props.get("coverTitle"), reportTitle);
        String coverSubtitle = str(props.get("coverSubtitle"), "Report");
        String coverNote = str(props.get("coverNote"), "");

        XWPFParagraph title = context.document.createParagraph();
        title.setAlignment(ParagraphAlignment.CENTER);
        title.setSpacingBefore(2400);
        XWPFRun t = title.createRun();
        t.setText(coverTitle);
        t.setBold(true);
        t.setFontFamily(context.theme.fontPrimary());
        t.setColor(VisualStyle.toHexNoHash(context.theme.text()));
        t.setFontSize(30);

        XWPFParagraph sub = context.document.createParagraph();
        sub.setAlignment(ParagraphAlignment.CENTER);
        XWPFRun s = sub.createRun();
        s.setText(coverSubtitle);
        s.setFontFamily(context.theme.fontPrimary());
        s.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
        s.setFontSize(14);

        addCenteredImageIfPresent(context, str(props.get("coverImage"), ""), "cover-image", 3_800_000, 2_100_000);

        if (!coverNote.isBlank()) {
            XWPFParagraph note = context.document.createParagraph();
            note.setAlignment(ParagraphAlignment.CENTER);
            note.setSpacingBefore(480);
            XWPFRun n = note.createRun();
            n.setText(coverNote);
            n.setFontFamily(context.theme.fontPrimary());
            n.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
            n.setFontSize(11);
        }
        for (String item : stringList(props.get("coverContents"))) {
            XWPFParagraph extra = context.document.createParagraph();
            extra.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun run = extra.createRun();
            run.setText(item);
            run.setFontFamily(context.theme.fontPrimary());
            run.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
            run.setFontSize(10);
        }
        pageBreak(context.document);
    }

    /**
     * 生成目录页（当前为静态文本目录）。
     */
    private void addTocPage(DocxRenderContext context, List<VNode> sections) {
        addHeading(context, "目录", 1);
        for (int i = 0; i < sections.size(); i++) {
            VNode section = sections.get(i);
            String title = section.propString("title", "章节 " + (i + 1));
            XWPFParagraph p = context.document.createParagraph();
            XWPFRun run = p.createRun();
            run.setText(tocLabel(i + 1, title));
            run.setFontFamily(context.theme.fontPrimary());
            run.setFontSize(11);
            run.setColor(VisualStyle.toHexNoHash(context.theme.text()));
        }
        pageBreak(context.document);
    }

    /**
     * 渲染正文章节与其子块。
     */
    private void addContentPages(DocxRenderContext context, List<VNode> sections, Map<String, Object> props) throws IOException {
        String paginationStrategy = str(props.get("paginationStrategy"), "section");
        boolean sectionBreak = !"continuous".equalsIgnoreCase(paginationStrategy);
        int blockGapTwips = resolveBlockGapTwips(props);
        for (int i = 0; i < sections.size(); i++) {
            VNode section = sections.get(i);
            String title = section.propString("title", "章节 " + (i + 1));
            addHeading(context, title, 1);
            List<VNode> blocks = section.childrenOrEmpty();
            for (int blockIndex = 0; blockIndex < blocks.size(); blockIndex++) {
                VNode block = blocks.get(blockIndex);
                nodeRenderers.render(context, block);
                if (blockIndex < blocks.size() - 1) {
                    appendGapParagraph(context.document, blockGapTwips);
                }
            }
            if (sectionBreak && i < sections.size() - 1) {
                pageBreak(context.document);
            }
        }
    }

    private PageMargins resolvePageMargins(Map<String, Object> props) {
        String preset = str(props.get("marginPreset"), "normal").toLowerCase();
        double presetMm = switch (preset) {
            case "narrow" -> 10.0;
            case "wide" -> 20.0;
            default -> 14.0;
        };
        boolean custom = "custom".equals(preset);
        double topMm = custom ? VNode.asDouble(props.get("marginTopMm"), presetMm) : presetMm;
        double rightMm = custom ? VNode.asDouble(props.get("marginRightMm"), presetMm) : presetMm;
        double bottomMm = custom ? VNode.asDouble(props.get("marginBottomMm"), presetMm) : presetMm;
        double leftMm = custom ? VNode.asDouble(props.get("marginLeftMm"), presetMm) : presetMm;

        return new PageMargins(mmToTwips(topMm), mmToTwips(rightMm), mmToTwips(bottomMm), mmToTwips(leftMm));
    }

    private long mmToTwips(double mm) {
        double safeMm = Math.max(6.0, mm);
        return Math.round(safeMm * 56.6929133858);
    }

    private int resolveBodyPaddingTwips(Map<String, Object> props) {
        int px = clampInt(VNode.asDouble(props.get("bodyPaddingPx"), 12.0), 0, 120);
        return pxToTwips(px);
    }

    private int resolveSectionGapTwips(Map<String, Object> props) {
        int px = clampInt(VNode.asDouble(props.get("sectionGapPx"), 12.0), 0, 160);
        return pxToTwips(px);
    }

    private int resolveBlockGapTwips(Map<String, Object> props) {
        int px = clampInt(VNode.asDouble(props.get("blockGapPx"), 8.0), 0, 160);
        return pxToTwips(px);
    }

    private int pxToTwips(int px) {
        return Math.max(0, px) * 15;
    }

    private int clampInt(double value, int min, int max) {
        int rounded = (int) Math.round(value);
        return Math.max(min, Math.min(max, rounded));
    }

    private void appendGapParagraph(XWPFDocument document, int gapTwips) {
        XWPFParagraph gap = document.createParagraph();
        gap.setSpacingAfter(Math.max(0, gapTwips));
    }

    /**
     * 生成总结页。
     */
    private void addSummaryPage(DocxRenderContext context, Map<String, Object> props, List<VNode> sections) {
        pageBreak(context.document);
        String summaryTitle = str(props.get("summaryTitle"), "执行摘要");
        String summaryText = str(props.get("summaryText"), buildDefaultSummary(sections));
        addHeading(context, summaryTitle, 1);
        addBodyTextParagraph(context, summaryText);
    }

    /**
     * 生成签字页。
     */
    private void addSignaturePage(DocxRenderContext context, Map<String, Object> props) {
        pageBreak(context.document);
        addHeading(context, str(props.get("signatureTitle"), "签字确认"), 1);
        List<Map<String, Object>> signers = mapList(props.get("signers"));
        if (signers.isEmpty()) {
            addBodyTextParagraph(context, "暂无签字人配置。");
            return;
        }

        XWPFTable table = context.document.createTable(signers.size() + 1, 4);
        table.setWidth("100%");
        String[] headers = {"姓名", "角色", "签字", "日期"};
        XWPFTableRow header = table.getRow(0);
        for (int i = 0; i < headers.length; i++) {
            XWPFTableCell cell = header.getCell(i);
            styleCell(cell, context.theme.primarySoft());
            writeCellText(cell, headers[i], context.theme, true, 10, context.theme.text());
        }

        for (int i = 0; i < signers.size(); i++) {
            Map<String, Object> signer = signers.get(i);
            XWPFTableRow row = table.getRow(i + 1);
            writeSignatureCell(context, row.getCell(0), str(signer.get("name"), ""));
            writeSignatureCell(context, row.getCell(1), str(signer.get("role"), ""));
            writeSignatureCell(context, row.getCell(2), "", str(signer.get("signature"), ""));
            writeSignatureCell(context, row.getCell(3), str(signer.get("date"), ""));
        }
    }

    private void writeSignatureCell(DocxRenderContext context, XWPFTableCell cell, String text) {
        styleCell(cell, context.theme.panel());
        writeCellText(cell, text, context.theme, false, 10, context.theme.text());
    }

    private void writeSignatureCell(DocxRenderContext context, XWPFTableCell cell, String text, String signatureImage) {
        styleCell(cell, context.theme.panel());
        if (addCellImageIfPresent(cell, signatureImage, "signature-image", 1_000_000, 320_000)) {
            return;
        }
        writeCellText(cell, text.isBlank() ? "________________" : text, context.theme, false, 10, context.theme.text());
    }

    /**
     * 输出标准标题段落（章节标题/小节标题）。
     */
    private void addHeading(DocxRenderContext context, String text, int level) {
        int sectionGapTwips = resolveSectionGapTwips(context.rootProps());
        int bodyPaddingTwips = resolveBodyPaddingTwips(context.rootProps());
        XWPFParagraph p = context.document.createParagraph();
        p.setAlignment(ParagraphAlignment.LEFT);
        p.setSpacingBefore(level <= 1 ? Math.max(100, bodyPaddingTwips / 2) : Math.max(60, bodyPaddingTwips / 3));
        p.setSpacingAfter(Math.max(80, sectionGapTwips));
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setBold(true);
        run.setFontFamily(context.theme.fontPrimary());
        run.setColor(VisualStyle.toHexNoHash(context.theme.text()));
        run.setFontSize(level <= 1 ? 18 : 14);
    }

    /**
     * 输出正文文本块。
     */
    private void addBodyTextParagraph(DocxRenderContext context, String text) {
        XWPFParagraph p = context.document.createParagraph();
        p.setSpacingBefore(0);
        p.setSpacingAfter(120);
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setFontFamily(context.theme.fontPrimary());
        run.setColor(VisualStyle.toHexNoHash(context.theme.text()));
        run.setFontSize(11);
    }

    /**
     * 渲染图表卡片：
     * - 优先原生图表
     * - 失败时输出占位卡片与样本预览
     */
    private void addChartCard(DocxRenderContext context, ChartSpec spec, List<Map<String, Object>> rows) {
        boolean nativeRendered = renderNativeChartIfNeeded(context, spec, rows);
        if (nativeRendered) {
            return;
        }

        XWPFTable table = context.document.createTable(2, 1);
        table.setWidth("100%");
        styleCell(table.getRow(0).getCell(0), context.theme.primarySoft());
        styleCell(table.getRow(1).getCell(0), context.theme.panelAlt());
        writeCellText(table.getRow(0).getCell(0), "图表: " + spec.title(), context.theme, true, 11, context.theme.text());
        if (rows == null || rows.isEmpty()) {
            writeCellText(table.getRow(1).getCell(0), "暂无可用数据，未生成原生图表。", context.theme, false, 10, context.theme.muted());
        } else {
            writeCellText(table.getRow(1).getCell(0), "当前图表未生成原生图表，已输出占位信息。", context.theme, false, 10, context.theme.muted());
        }
        addSampleRowPreview(context, rows);
    }

    /**
     * 输出最多 8 行 * 6 列样本预览，便于运行态排障。
     */
    private void addSampleRowPreview(DocxRenderContext context, List<Map<String, Object>> rows) {
        if (rows == null || rows.isEmpty()) {
            return;
        }
        List<String> columns = collectColumns(rows);
        if (columns.isEmpty()) {
            return;
        }
        int columnCount = Math.min(columns.size(), 6);
        XWPFTable table = context.document.createTable(1, columnCount);
        table.setWidth("100%");
        XWPFTableRow head = table.getRow(0);
        for (int i = 0; i < columnCount; i++) {
            XWPFTableCell cell = head.getCell(i);
            styleCell(cell, context.theme.primarySoft());
            writeCellText(cell, columns.get(i), context.theme, true, 10, context.theme.text());
        }

        int maxRows = Math.min(rows.size(), 8);
        for (int rowIdx = 0; rowIdx < maxRows; rowIdx++) {
            XWPFTableRow row = table.createRow();
            Map<String, Object> rowData = rows.get(rowIdx);
            for (int col = 0; col < columnCount; col++) {
                XWPFTableCell cell = row.getCell(col);
                if (cell == null) {
                    cell = row.addNewTableCell();
                }
                styleCell(cell, context.theme.panel());
                String value = str(rowData.get(columns.get(col)), "-");
                writeCellText(cell, value, context.theme, false, 10, context.theme.text());
            }
        }
    }

    /**
     * 渲染表格块（含多级表头/合并/重复表头）。
     */
    private void addTableBlock(DocxRenderContext context, VNode tableNode, List<Map<String, Object>> rows) {
        TableModel model = tableSpecParser.parse(tableNode, rows);
        if (model.columnCount() <= 0) {
            XWPFParagraph p = context.document.createParagraph();
            XWPFRun run = p.createRun();
            run.setText("未能解析有效表格列定义。");
            run.setFontFamily(context.theme.fontPrimary());
            run.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
            run.setFontSize(10);
            return;
        }

        int totalRows = Math.max(1, model.totalRowCount());
        XWPFTable table = context.document.createTable(totalRows, model.columnCount());
        table.setWidth("100%");

        fillDocxHeaderRows(context, table, model);
        fillDocxBodyRows(context, table, model);
        applyDocxMerges(table, model);
        if (model.repeatHeader()) {
            markHeaderRowsRepeat(table, model.headerRowCount());
        }
    }

    /**
     * 写入 DOCX 表头矩阵。
     */
    private void fillDocxHeaderRows(DocxRenderContext context, XWPFTable table, TableModel model) {
        for (int r = 0; r < model.headerRowCount(); r++) {
            XWPFTableRow row = table.getRow(r);
            List<TableCell> header = model.headerRows().get(r);
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = header.get(c);
                XWPFTableCell tableCell = row.getCell(c);
                styleCell(tableCell, context.theme.primarySoft());
                if (cell.hidden()) {
                    writeCellText(tableCell, "", context.theme, true, 10, context.theme.text());
                    continue;
                }
                writeCellText(tableCell, cell.text(), context.theme, true, 10, context.theme.text());
                setParagraphAlign(tableCell, cell.align());
            }
        }
    }

    /**
     * 写入 DOCX 数据区矩阵。
     */
    private void fillDocxBodyRows(DocxRenderContext context, XWPFTable table, TableModel model) {
        for (int r = 0; r < model.bodyRowCount(); r++) {
            int tableRowIndex = model.headerRowCount() + r;
            XWPFTableRow row = table.getRow(tableRowIndex);
            List<TableCell> body = model.bodyRows().get(r);
            Color bg = model.zebra() && (r % 2 == 1) ? context.theme.panelAlt() : context.theme.panel();
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = body.get(c);
                XWPFTableCell tableCell = row.getCell(c);
                styleCell(tableCell, bg);
                if (cell.hidden()) {
                    writeCellText(tableCell, "", context.theme, false, 10, context.theme.text());
                    continue;
                }
                writeCellText(tableCell, cell.text(), context.theme, false, 10, context.theme.text());
                setParagraphAlign(tableCell, cell.align());
            }
        }
    }

    /**
     * 将 TableModel 的合并语义映射到 DOCX merge 标记。
     */
    private void applyDocxMerges(XWPFTable table, TableModel model) {
        for (int r = 0; r < model.headerRowCount(); r++) {
            List<TableCell> row = model.headerRows().get(r);
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                if (!cell.hidden() && (cell.rowSpan() > 1 || cell.colSpan() > 1)) {
                    applyDocxMerge(table, r, c, cell.rowSpan(), cell.colSpan());
                }
            }
        }
        for (int r = 0; r < model.bodyRowCount(); r++) {
            List<TableCell> row = model.bodyRows().get(r);
            int baseRow = model.headerRowCount() + r;
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                if (!cell.hidden() && (cell.rowSpan() > 1 || cell.colSpan() > 1)) {
                    applyDocxMerge(table, baseRow, c, cell.rowSpan(), cell.colSpan());
                }
            }
        }
    }

    /**
     * 在 DOCX 表格中执行一次合并（hMerge/vMerge + gridSpan）。
     */
    private void applyDocxMerge(XWPFTable table, int row, int col, int rowSpan, int colSpan) {
        int rowCount = table.getNumberOfRows();
        int colCount = table.getRow(row).getTableCells().size();
        int rs = Math.max(1, Math.min(rowSpan, rowCount - row));
        int cs = Math.max(1, Math.min(colSpan, colCount - col));
        if (rs <= 1 && cs <= 1) {
            return;
        }

        XWPFTableCell anchor = table.getRow(row).getCell(col);
        CTTcPr anchorTcPr = ensureTcPr(anchor);
        if (cs > 1) {
            if (anchorTcPr.isSetGridSpan()) {
                anchorTcPr.getGridSpan().setVal(BigInteger.valueOf(cs));
            } else {
                anchorTcPr.addNewGridSpan().setVal(BigInteger.valueOf(cs));
            }
            if (anchorTcPr.isSetHMerge()) {
                anchorTcPr.getHMerge().setVal(STMerge.RESTART);
            } else {
                anchorTcPr.addNewHMerge().setVal(STMerge.RESTART);
            }
        }
        if (rs > 1) {
            if (anchorTcPr.isSetVMerge()) {
                anchorTcPr.getVMerge().setVal(STMerge.RESTART);
            } else {
                anchorTcPr.addNewVMerge().setVal(STMerge.RESTART);
            }
        }

        for (int r = row; r < row + rs; r++) {
            for (int c = col; c < col + cs; c++) {
                if (r == row && c == col) {
                    continue;
                }
                XWPFTableCell follower = table.getRow(r).getCell(c);
                CTTcPr tcPr = ensureTcPr(follower);
                if (cs > 1) {
                    if (tcPr.isSetHMerge()) {
                        tcPr.getHMerge().setVal(STMerge.CONTINUE);
                    } else {
                        tcPr.addNewHMerge().setVal(STMerge.CONTINUE);
                    }
                }
                if (rs > 1) {
                    if (tcPr.isSetVMerge()) {
                        tcPr.getVMerge().setVal(STMerge.CONTINUE);
                    } else {
                        tcPr.addNewVMerge().setVal(STMerge.CONTINUE);
                    }
                }
                clearCellText(follower);
            }
        }
    }

    private CTTcPr ensureTcPr(XWPFTableCell cell) {
        return cell.getCTTc().isSetTcPr() ? cell.getCTTc().getTcPr() : cell.getCTTc().addNewTcPr();
    }

    /**
     * 标记表头行为“跨页重复”。
     */
    private void markHeaderRowsRepeat(XWPFTable table, int headerRows) {
        for (int r = 0; r < headerRows && r < table.getNumberOfRows(); r++) {
            XWPFTableRow row = table.getRow(r);
            CTTrPr trPr = row.getCtRow().isSetTrPr() ? row.getCtRow().getTrPr() : row.getCtRow().addNewTrPr();
            trPr.addNewTblHeader();
        }
    }

    private void setParagraphAlign(XWPFTableCell cell, String align) {
        XWPFParagraph p = cell.getParagraphArray(0);
        if (p == null) {
            return;
        }
        p.setAlignment(switch (align) {
            case "center" -> ParagraphAlignment.CENTER;
            case "right" -> ParagraphAlignment.RIGHT;
            default -> ParagraphAlignment.LEFT;
        });
    }

    private void clearCellText(XWPFTableCell cell) {
        XWPFParagraph p = cell.getParagraphArray(0);
        if (p == null) {
            p = cell.addParagraph();
        }
        while (p.getRuns().size() > 0) {
            p.removeRun(0);
        }
    }

    /**
     * 尝试绘制原生图表；异常时静默回退到占位卡片。
     */
    private boolean renderNativeChartIfNeeded(DocxRenderContext context, ChartSpec spec, List<Map<String, Object>> rows) {
        boolean nativeChartEnabled = VNode.asBoolean(context.rootProps().get("nativeChartEnabled"), true);
        if (!nativeChartEnabled || rows == null || rows.isEmpty()) {
            return false;
        }
        try {
            XWPFParagraph paragraph = context.document.createParagraph();
            paragraph.setSpacingBefore(120);
            paragraph.setSpacingAfter(120);
            XWPFRun run = paragraph.createRun();

            int width = (int) VNode.asDouble(context.rootProps().get("nativeChartWidthEmu"), 6_000_000);
            int height = (int) VNode.asDouble(context.rootProps().get("nativeChartHeightEmu"), 3_200_000);
            XWPFChart chart = context.document.createChart(run, width, height);
            return poiChartRenderer.render(chart, spec, rows);
        } catch (Exception ignored) {
            return false;
        }
    }

    /**
     * 在样本预览中按遇到顺序收集列，最多 6 列。
     */
    private List<String> collectColumns(List<Map<String, Object>> rows) {
        List<String> columns = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            for (String key : row.keySet()) {
                if (!columns.contains(key)) {
                    columns.add(key);
                }
            }
            if (columns.size() >= 6) {
                return columns;
            }
        }
        return columns;
    }

    /**
     * 解析 chartType 对应的风味渲染器。
     */
    private DocxChartFlavorRenderer resolveFlavor(String chartType) {
        for (DocxChartFlavorRenderer renderer : chartFlavorRenderers) {
            if (renderer.supports(chartType)) {
                return renderer;
            }
        }
        return chartFlavorRenderers.get(chartFlavorRenderers.size() - 1);
    }

    private void styleCell(XWPFTableCell cell, Color background) {
        cell.setColor(VisualStyle.toHexNoHash(background));
    }

    private void writeCellText(
            XWPFTableCell cell,
            String text,
            ThemeTokens theme,
            boolean bold,
            int fontSize,
            Color color
    ) {
        XWPFParagraph p = cell.getParagraphArray(0);
        p.setSpacingAfter(0);
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setBold(bold);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(fontSize);
        run.setColor(VisualStyle.toHexNoHash(color));
    }

    private static void appendFlavorRow(XWPFTable table, ThemeTokens theme, String text, Color bg, Color fg) {
        XWPFTableRow row = table.createRow();
        XWPFTableCell cell = row.getCell(0);
        cell.setColor(VisualStyle.toHexNoHash(bg));
        XWPFParagraph p = cell.getParagraphArray(0);
        p.setSpacingAfter(0);
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setBold(false);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(10);
        run.setColor(VisualStyle.toHexNoHash(fg));
    }

    /**
     * 默认报告标题。
     */
    private String defaultReportTitle(VDoc doc) {
        return doc.title == null || doc.title.isBlank() ? "报告" : doc.title;
    }

    /**
     * 自动构建总结文本（章节数/图表数/复杂图表数）。
     */
    private String buildDefaultSummary(List<VNode> sections) {
        int chartCount = 0;
        int textCount = 0;
        int advancedCharts = 0;
        for (VNode section : sections) {
            for (VNode block : section.childrenOrEmpty()) {
                if ("chart".equalsIgnoreCase(block.kind)) {
                    chartCount++;
                    ChartSpec spec = chartSpecParser.parse(block);
                    if ("advanced".equals(spec.complexityLevel()) || "enterprise".equals(spec.complexityLevel())) {
                        advancedCharts++;
                    }
                } else if ("text".equalsIgnoreCase(block.kind)) {
                    textCount++;
                }
            }
        }
        return "本报告共 " + sections.size() + " 个章节，包含 " + chartCount + " 张图表与 " + textCount
                + " 段文本。复杂图表数量: " + advancedCharts + "。";
    }

    /**
     * 提取 section 子节点。
     */
    private List<VNode> sectionNodes(VNode root) {
        if (root == null) {
            return Collections.emptyList();
        }
        List<VNode> sections = new ArrayList<>();
        for (VNode child : root.childrenOrEmpty()) {
            if ("section".equalsIgnoreCase(child.kind)) {
                sections.add(child);
            }
        }
        return sections;
    }

    private boolean bool(Object value, boolean fallback) {
        return VNode.asBoolean(value, fallback);
    }

    private String str(Object value, String fallback) {
        String s = VNode.asString(value, fallback);
        return s == null ? fallback : s;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> mapList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        ArrayList<Map<String, Object>> result = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                result.add((Map<String, Object>) map);
            }
        }
        return result;
    }

    private List<String> stringList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return Collections.emptyList();
        }
        ArrayList<String> result = new ArrayList<>();
        for (Object item : list) {
            String text = str(item, "");
            if (!text.isBlank()) {
                result.add(text);
            }
        }
        return result;
    }

    private void addCenteredImageIfPresent(
            DocxRenderContext context,
            String rawImage,
            String fileName,
            int widthEmu,
            int heightEmu
    ) {
        DecodedImage image = decodeImage(rawImage);
        if (image == null) {
            return;
        }
        try (ByteArrayInputStream in = new ByteArrayInputStream(image.bytes())) {
            XWPFParagraph p = context.document.createParagraph();
            p.setAlignment(ParagraphAlignment.CENTER);
            p.setSpacingBefore(240);
            p.setSpacingAfter(120);
            XWPFRun run = p.createRun();
            run.addPicture(in, image.pictureType(), fileName + image.extension(), widthEmu, heightEmu);
        } catch (Exception ignored) {
            // 图片字段是可选增强，失败时继续输出文本报告。
        }
    }

    private boolean addCellImageIfPresent(
            XWPFTableCell cell,
            String rawImage,
            String fileName,
            int widthEmu,
            int heightEmu
    ) {
        DecodedImage image = decodeImage(rawImage);
        if (image == null) {
            return false;
        }
        try (ByteArrayInputStream in = new ByteArrayInputStream(image.bytes())) {
            XWPFParagraph p = cell.getParagraphArray(0);
            if (p == null) {
                p = cell.addParagraph();
            }
            XWPFRun run = p.createRun();
            run.addPicture(in, image.pictureType(), fileName + image.extension(), widthEmu, heightEmu);
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    private DecodedImage decodeImage(String rawImage) {
        if (rawImage == null || rawImage.isBlank()) {
            return null;
        }
        String text = rawImage.trim();
        String mime = "";
        int comma = text.indexOf(',');
        if (text.startsWith("data:") && comma > 0) {
            mime = text.substring(5, comma).toLowerCase();
            text = text.substring(comma + 1);
        }
        try {
            byte[] bytes = Base64.getDecoder().decode(text);
            int pictureType = mime.contains("jpeg") || mime.contains("jpg")
                    ? org.apache.poi.xwpf.usermodel.Document.PICTURE_TYPE_JPEG
                    : org.apache.poi.xwpf.usermodel.Document.PICTURE_TYPE_PNG;
            String extension = pictureType == org.apache.poi.xwpf.usermodel.Document.PICTURE_TYPE_JPEG ? ".jpg" : ".png";
            return new DecodedImage(bytes, pictureType, extension);
        } catch (IllegalArgumentException ex) {
            return null;
        }
    }

    private record DecodedImage(byte[] bytes, int pictureType, String extension) {
    }

    /**
     * 快速插入分页符。
     */
    private static void pageBreak(XWPFDocument document) {
        XWPFParagraph p = document.createParagraph();
        p.setPageBreak(true);
    }

    /**
     * 目录编号格式化。
     */
    private String tocLabel(int index, String title) {
        if (title == null) {
            return index + ". 章节 " + index;
        }
        String trimmed = title.trim();
        if (trimmed.matches("^\\d+[\\.、]\\s*.*")) {
            return trimmed;
        }
        return index + ". " + trimmed;
    }

    /**
     * DOCX 渲染上下文。
     */
    public static final class DocxRenderContext {
        private final XWPFDocument document;
        private final ThemeTokens theme;
        private final ChartSpecParser chartSpecParser;
        private final Map<String, Object> rootProps;
        private final VDoc doc;

        private DocxRenderContext(
                XWPFDocument document,
                ThemeTokens theme,
                ChartSpecParser chartSpecParser,
                Map<String, Object> rootProps,
                VDoc doc
        ) {
            this.document = document;
            this.theme = theme;
            this.chartSpecParser = chartSpecParser;
            this.rootProps = rootProps;
            this.doc = doc;
        }

        public XWPFDocument document() {
            return document;
        }

        public ThemeTokens theme() {
            return theme;
        }

        public ChartSpecParser chartSpecParser() {
            return chartSpecParser;
        }

        public Map<String, Object> rootProps() {
            return rootProps;
        }

        public VDoc doc() {
            return doc;
        }
    }

    /**
     * 图表风味渲染上下文（占位卡片模式）。
     */
    public static final class DocxChartFlavorContext {
        private final XWPFTable table;
        private final ThemeTokens theme;

        private DocxChartFlavorContext(XWPFTable table, ThemeTokens theme) {
            this.table = table;
            this.theme = theme;
        }

        public ThemeTokens theme() {
            return theme;
        }

        public void appendInfoRow(String text) {
            appendFlavorRow(table, theme, text, theme.panelAlt(), theme.text());
        }

        public void appendRow(String text, Color bg, Color fg) {
            appendFlavorRow(table, theme, text, bg, fg);
        }
    }

    /**
     * 节点 kind=text 渲染器。
     */
    private final class TextNodeRenderer implements NodeRenderer<DocxRenderContext> {
        @Override
        public String kind() {
            return "text";
        }

        @Override
        public void render(DocxRenderContext context, VNode node) {
            addBodyTextParagraph(context, node.propString("text", ""));
        }
    }

    /**
     * 节点 kind=chart 渲染器。
     */
    private final class ChartNodeRenderer implements NodeRenderer<DocxRenderContext> {
        @Override
        public String kind() {
            return "chart";
        }

        @Override
        public void render(DocxRenderContext context, VNode node) {
            ChartSpec spec = context.chartSpecParser.parse(node);
            List<Map<String, Object>> rows = chartRowResolver.resolve(context.doc(), node, spec);
            addChartCard(context, spec, rows);
        }
    }

    private record PageMargins(long topTwips, long rightTwips, long bottomTwips, long leftTwips) {
    }

    /**
     * 节点 kind=table 渲染器。
     */
    private final class TableNodeRenderer implements NodeRenderer<DocxRenderContext> {
        @Override
        public String kind() {
            return "table";
        }

        @Override
        public void render(DocxRenderContext context, VNode node) {
            List<Map<String, Object>> rows = chartRowResolver.resolve(context.doc(), node, null);
            addTableBlock(context, node, rows);
        }
    }

    /**
     * 未支持节点兜底渲染器。
     */
    private final class UnsupportedNodeRenderer implements NodeRenderer<DocxRenderContext> {
        @Override
        public String kind() {
            return "__fallback__";
        }

        @Override
        public void render(DocxRenderContext context, VNode node) {
            XWPFParagraph p = context.document.createParagraph();
            XWPFRun run = p.createRun();
            run.setText("未支持块类型: " + (node == null ? "-" : str(node.kind, "-")));
            run.setFontFamily(context.theme.fontPrimary());
            run.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
            run.setFontSize(10);
        }
    }

    /**
     * 图表风味渲染接口（用于占位卡片策略说明）。
     */
    public interface DocxChartFlavorRenderer {
        boolean supports(String chartType);

        void render(DocxChartFlavorContext context, ChartSpec spec);
    }

    private final class TrendFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("line")
                    || normalized.equals("scatter")
                    || normalized.equals("combo")
                    || normalized.equals("parallel");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("趋势策略: 适合时间序列与连续变化，建议维度字段使用日期/时间，保持指标不超过 8 个。");
        }
    }

    private final class ComparisonFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("bar")
                    || normalized.equals("radar")
                    || normalized.equals("boxplot");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("对比策略: 适合分类对比，支持分组/堆叠；若类目超过 20，建议先做 TopN 或分页筛选。");
        }
    }

    private final class CompositionFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("pie");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("构成策略: 适合份额分布，建议维度类别不超过 10，其他项可归并为“其他”。");
        }
    }

    private final class TableFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("heatmap");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("明细策略: 适合高复杂度明细分析，支持样本预览。建议配合过滤器和计算字段控制输出规模。");
        }
    }

    private final class RelationFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("sankey") || normalized.equals("graph");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("关系策略: 支持链路/关系表达，建议补充 node/link 绑定并控制节点规模。");
        }
    }

    private final class MatrixFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("treemap")
                    || normalized.equals("sunburst")
                    || normalized.equals("funnel")
                    || normalized.equals("gauge");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("层次策略: 适合结构化占比表达，可按层级分组输出核心路径。");
        }
    }

    private final class TimeWindowFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("calendar")
                    || normalized.equals("kline");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("时窗策略: 适合日期/交易序列，建议使用 day/week/month 粒度字段。");
        }
    }

    private final class CustomFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            return normalize(chartType).equals("custom");
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("自定义策略: 已输出可商用基础渲染，可通过 optionPatch/插件策略扩展。");
        }
    }

    private final class GenericFlavorRenderer implements DocxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            return true;
        }

        @Override
        public void render(DocxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoRow("通用策略: 当前图表类型未命中专用渲染器，已走通用图卡渲染，可按 chartType 扩展专用策略。");
        }
    }

    private String normalize(String chartType) {
        return ChartTypeCatalog.normalize(chartType);
    }
}
