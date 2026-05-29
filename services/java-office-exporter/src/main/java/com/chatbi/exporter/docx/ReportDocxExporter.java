package com.chatbi.exporter.docx;

import com.chatbi.exporter.chart.ChartSpec;
import com.chatbi.exporter.chart.ChartSpecParser;
import com.chatbi.exporter.chart.PoiChartRenderer;
import com.chatbi.exporter.chart.ChartRowResolver;
import com.chatbi.exporter.chart.ChartTypeCatalog;
import com.chatbi.exporter.conf.CoverMetaPosition;
import com.chatbi.exporter.conf.DocumentExportConfiguration;
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
import org.apache.poi.xwpf.usermodel.XWPFStyle;
import org.apache.poi.xwpf.usermodel.XWPFStyles;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableCell;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.apache.poi.xwpf.usermodel.XWPFChart;
import org.apache.poi.xwpf.usermodel.TableRowHeightRule;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageMar;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTPageSz;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTBookmark;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTHyperlink;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTMarkupRange;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTStyle;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTR;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTRPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSectPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblGrid;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblGridCol;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblLayoutType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTblWidth;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTcPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTTrPr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTSimpleField;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STMerge;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STHdrFtr;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STStyleType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STTblLayoutType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STTblWidth;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.STUnderline;
import org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.CTAnchor;
import org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.CTInline;
import org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.STRelFromH;
import org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.STRelFromV;

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
    private final DocumentExportConfiguration configuration;
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
        this(styleResolver, chartSpecParser, DocumentExportConfiguration.defaults());
    }

    public ReportDocxExporter(
            StyleResolver styleResolver,
            ChartSpecParser chartSpecParser,
            DocumentExportConfiguration configuration
    ) {
        this.styleResolver = styleResolver;
        this.chartSpecParser = chartSpecParser;
        this.configuration = configuration == null ? DocumentExportConfiguration.defaults() : configuration;
        this.chartRowResolver = new ChartRowResolver();
        this.poiChartRenderer = new PoiChartRenderer();
        this.tableSpecParser = new TableSpecParser(this.configuration.word().table().repeatHeaderOnPageBreak());
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
                .register(new TableNodeRenderer())
                .register(new CompositeTableNodeRenderer());
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
            ensureHeadingStyles(document, theme);
            setupHeaderFooter(document, props, str(props.get("reportTitle"), defaultReportTitle(doc)), theme);

            boolean coverEnabled = bool(props.get("coverEnabled"), true);
            boolean tocShow = bool(props.get("tocShow"), configuration.word().toc().enabled());
            boolean summaryEnabled = bool(props.get("summaryEnabled"), true);
            List<VNode> contentNodes = contentNodes(doc.root);

            if (coverEnabled) {
                addCoverPage(context, props, doc);
            }
            if (tocShow) {
                addTocPage(context, contentNodes);
            }
            addContentPages(context, contentNodes, props);
            if (summaryEnabled) {
                addSummaryPage(context, props, sectionNodes(doc.root));
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
        String footerText = str(props.get("footerText"), "ChatBI");

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

    private void ensureHeadingStyles(XWPFDocument document, ThemeTokens theme) {
        XWPFStyles styles = document.getStyles();
        if (styles == null) {
            styles = document.createStyles();
        }
        for (int level = 1; level <= 6; level++) {
            String styleId = headingStyleId(level);
            if (!styles.styleExist(styleId)) {
                styles.addStyle(new XWPFStyle(createHeadingStyle(styleId, level, theme), styles));
            }
        }
    }

    private CTStyle createHeadingStyle(String styleId, int level, ThemeTokens theme) {
        CTStyle style = CTStyle.Factory.newInstance();
        style.setStyleId(styleId);
        style.setType(STStyleType.PARAGRAPH);
        style.addNewName().setVal("heading " + level);
        style.addNewBasedOn().setVal("Normal");
        style.addNewNext().setVal("Normal");
        style.addNewUiPriority().setVal(BigInteger.valueOf(level <= 3 ? 9L + level : 20L + level));
        style.addNewQFormat();

        var pPr = style.addNewPPr();
        pPr.addNewOutlineLvl().setVal(BigInteger.valueOf(level - 1L));
        var spacing = pPr.addNewSpacing();
        spacing.setBefore(BigInteger.valueOf(headingSpacingBeforeTwips(level)));
        spacing.setAfter(BigInteger.valueOf(level <= 1 ? 160L : 120L));

        var rPr = style.addNewRPr();
        rPr.addNewB();
        rPr.addNewColor().setVal(VisualStyle.toHexNoHash(theme.text()));
        var fonts = rPr.addNewRFonts();
        fonts.setAscii(theme.fontPrimary());
        fonts.setEastAsia(theme.fontPrimary());
        rPr.addNewSz().setVal(BigInteger.valueOf((level <= 1 ? 18L : level == 2 ? 16L : 14L) * 2L));
        return style;
    }

    /**
     * 生成封面页。
     */
    private void addCoverPage(DocxRenderContext context, Map<String, Object> props, VDoc doc) {
        String reportTitle = str(props.get("reportTitle"), defaultReportTitle(doc));
        String coverTitle = str(props.get("coverTitle"), reportTitle);
        String coverSubtitle = str(props.get("coverSubtitle"), "Report");
        String coverAuthor = str(props.get("coverAuthor"), "");
        String coverDate = str(props.get("coverDate"), "");
        String coverNote = str(props.get("coverNote"), "");
        String coverImage = str(props.get("coverImage"), "");
        boolean hasCoverImage = !coverImage.isBlank();

        XWPFTable cover = context.document.createTable(4, 1);
        cover.removeBorders();
        int coverWidth = resolveWritablePageWidthTwips(props);
        setFixedTableWidth(cover, coverWidth, new int[]{coverWidth});
        applyCellWidths(cover, new int[]{coverWidth});
        int coverHeight = Math.max(
                7200,
                resolveWritablePageHeightTwips(props) - (configuration.word().cover().keepMetaOnFirstPage() ? 520 : 0)
        );
        int topHeight = (int) Math.round(coverHeight * 0.22);
        int titleHeight = (int) Math.round(coverHeight * 0.20);
        int noteHeight = (int) Math.round(coverHeight * 0.24);
        int metaHeight = Math.max(1800, coverHeight - topHeight - titleHeight - noteHeight);
        setCoverRow(cover.getRow(0), topHeight, hasCoverImage ? null : context.theme.panel());
        setCoverRow(cover.getRow(1), titleHeight, hasCoverImage ? null : context.theme.panel());
        setCoverRow(cover.getRow(2), noteHeight, hasCoverImage ? null : context.theme.panel());
        setCoverRow(cover.getRow(3), metaHeight, hasCoverImage ? null : context.theme.panel());
        addCoverBackgroundIfPresent(context, cover.getRow(0).getCell(0), coverImage);

        XWPFTableCell titleCell = cover.getRow(1).getCell(0);
        titleCell.setVerticalAlignment(XWPFTableCell.XWPFVertAlign.CENTER);
        writeCoverParagraph(titleCell, coverTitle, context.theme, true, 32, context.theme.text(), ParagraphAlignment.CENTER, 0, 80);
        if (!coverSubtitle.isBlank()) {
            writeCoverParagraph(titleCell, coverSubtitle, context.theme, false, 16, context.theme.muted(), ParagraphAlignment.CENTER, 0, 0);
        }

        XWPFTableCell noteCell = cover.getRow(2).getCell(0);
        noteCell.setVerticalAlignment(XWPFTableCell.XWPFVertAlign.CENTER);
        if (!coverNote.isBlank()) {
            writeCoverParagraph(noteCell, coverNote, context.theme, false, 11, context.theme.muted(), ParagraphAlignment.CENTER, 0, 40);
        }
        for (String item : stringList(props.get("coverContents"))) {
            writeCoverParagraph(noteCell, item, context.theme, false, 11, context.theme.muted(), ParagraphAlignment.CENTER, 0, 0);
        }

        XWPFTableCell metaCell = cover.getRow(3).getCell(0);
        metaCell.setVerticalAlignment(XWPFTableCell.XWPFVertAlign.BOTTOM);
        int metaIndentation = coverMetaIndentationLeft(props);
        if (!coverAuthor.isBlank()) {
            writeCoverParagraph(metaCell, "报告人：" + coverAuthor, context.theme, false, 12, context.theme.text(), ParagraphAlignment.RIGHT, metaIndentation, 60);
        }
        if (!coverDate.isBlank()) {
            writeCoverParagraph(metaCell, "时间：" + coverDate, context.theme, false, 12, context.theme.text(), ParagraphAlignment.RIGHT, metaIndentation, 0);
        }

        pageBreak(context.document);
    }

    private int coverMetaIndentationLeft(Map<String, Object> props) {
        if (configuration.word().cover().metaPosition() == CoverMetaPosition.BOTTOM_RIGHT) {
            return (int) Math.round(resolveWritablePageWidthTwips(props) * 0.58);
        }
        return 0;
    }

    private void addCoverBackgroundIfPresent(DocxRenderContext context, XWPFTableCell cell, String rawImage) {
        DecodedImage image = decodeImage(rawImage);
        if (image == null) {
            return;
        }
        Map<String, Object> props = context.rootProps();
        String pageSize = str(props.get("pageSize"), "A4");
        long widthEmu = ("Letter".equalsIgnoreCase(pageSize) ? 12240L : 11906L) * 635L;
        long heightEmu = ("Letter".equalsIgnoreCase(pageSize) ? 15840L : 16838L) * 635L;
        try (ByteArrayInputStream in = new ByteArrayInputStream(image.bytes())) {
            XWPFParagraph paragraph = cell.getParagraphArray(0);
            if (paragraph == null) {
                paragraph = cell.addParagraph();
            }
            paragraph.setSpacingBefore(0);
            paragraph.setSpacingAfter(0);
            XWPFRun run = paragraph.createRun();
            run.addPicture(in, image.pictureType(), "cover-background" + image.extension(), (int) widthEmu, (int) heightEmu);
            convertLastInlinePictureToPageBackground(run, widthEmu, heightEmu);
        } catch (Exception ignored) {
            // 封面背景是视觉增强，失败时保留文字封面。
        }
    }

    private void convertLastInlinePictureToPageBackground(XWPFRun run, long widthEmu, long heightEmu) {
        if (run.getCTR().sizeOfDrawingArray() == 0) {
            return;
        }
        org.openxmlformats.schemas.wordprocessingml.x2006.main.CTDrawing drawing =
                run.getCTR().getDrawingArray(run.getCTR().sizeOfDrawingArray() - 1);
        if (drawing.sizeOfInlineArray() == 0) {
            return;
        }
        CTInline inline = drawing.getInlineArray(drawing.sizeOfInlineArray() - 1);
        CTAnchor anchor = drawing.addNewAnchor();
        anchor.setSimplePos2(false);
        anchor.setRelativeHeight(0);
        anchor.setBehindDoc(true);
        anchor.setLocked(false);
        anchor.setLayoutInCell(false);
        anchor.setAllowOverlap(true);
        anchor.setDistT(0);
        anchor.setDistB(0);
        anchor.setDistL(0);
        anchor.setDistR(0);
        anchor.addNewSimplePos().setX(BigInteger.ZERO);
        anchor.getSimplePos().setY(BigInteger.ZERO);
        anchor.addNewPositionH().setRelativeFrom(STRelFromH.PAGE);
        anchor.getPositionH().setPosOffset(0);
        anchor.addNewPositionV().setRelativeFrom(STRelFromV.PAGE);
        anchor.getPositionV().setPosOffset(0);
        anchor.setExtent((org.openxmlformats.schemas.drawingml.x2006.main.CTPositiveSize2D) inline.getExtent().copy());
        anchor.getExtent().setCx(widthEmu);
        anchor.getExtent().setCy(heightEmu);
        if (inline.isSetEffectExtent()) {
            anchor.setEffectExtent((org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.CTEffectExtent) inline.getEffectExtent().copy());
        }
        anchor.addNewWrapNone();
        anchor.setDocPr((org.openxmlformats.schemas.drawingml.x2006.main.CTNonVisualDrawingProps) inline.getDocPr().copy());
        if (inline.isSetCNvGraphicFramePr()) {
            anchor.setCNvGraphicFramePr((org.openxmlformats.schemas.drawingml.x2006.main.CTNonVisualGraphicFrameProperties) inline.getCNvGraphicFramePr().copy());
        }
        anchor.setGraphic((org.openxmlformats.schemas.drawingml.x2006.main.CTGraphicalObject) inline.getGraphic().copy());
        drawing.removeInline(drawing.sizeOfInlineArray() - 1);
    }

    private void setCoverRow(XWPFTableRow row, int heightTwips, Color background) {
        row.setHeight(heightTwips);
        row.setHeightRule(TableRowHeightRule.EXACT);
        CTTrPr trPr = row.getCtRow().isSetTrPr() ? row.getCtRow().getTrPr() : row.getCtRow().addNewTrPr();
        trPr.addNewCantSplit();
        XWPFTableCell cell = row.getCell(0);
        if (background != null) {
            cell.setColor(VisualStyle.toHexNoHash(background));
        }
        clearCellText(cell);
    }

    private void writeCoverParagraph(
            XWPFTableCell cell,
            String text,
            ThemeTokens theme,
            boolean bold,
            int fontSize,
            Color color,
            ParagraphAlignment alignment,
            int indentationLeft,
            int spacingAfter
    ) {
        XWPFParagraph paragraph = cell.addParagraph();
        paragraph.setAlignment(alignment);
        paragraph.setIndentationLeft(Math.max(0, indentationLeft));
        paragraph.setSpacingAfter(Math.max(0, spacingAfter));
        XWPFRun run = paragraph.createRun();
        run.setText(text);
        run.setBold(bold);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(fontSize);
        run.setColor(VisualStyle.toHexNoHash(color));
    }

    /**
     * 生成目录页（当前为静态文本目录）。
     */
    private void addTocPage(DocxRenderContext context, List<VNode> contentNodes) {
        addTocTopSpacer(context);
        addHeading(context, "目录", 1);
        if (hasCatalogNodes(contentNodes)) {
            for (VNode node : contentNodes) {
                addCatalogTocEntry(context, node);
            }
        } else {
            for (int i = 0; i < contentNodes.size(); i++) {
                VNode section = contentNodes.get(i);
                String title = section.propString("title", "章节 " + (i + 1));
                XWPFParagraph p = context.document.createParagraph();
                addTocEntryText(p, bookmarkNameFor(section, "section_" + (i + 1)), tocLabel(i + 1, title), context.theme, 11);
            }
        }
        pageBreak(context.document);
    }

    private void addTocTopSpacer(DocxRenderContext context) {
        XWPFParagraph spacer = context.document.createParagraph();
        spacer.setSpacingBefore(0);
        spacer.setSpacingAfter(Math.max(
                360,
                (int) Math.round(resolveWritablePageHeightTwips(context.rootProps()) * configuration.word().toc().topOffsetRatio())
        ));
    }

    private void addCatalogTocEntry(DocxRenderContext context, VNode node) {
        if (!"catalog".equalsIgnoreCase(node.kind)) {
            return;
        }
        int level = outlineLevel(node);
        XWPFParagraph p = context.document.createParagraph();
        p.setIndentationLeft(Math.max(0, level - 1) * 360);
        p.setSpacingAfter(80);
        addTocEntryText(p, bookmarkNameFor(node, "catalog"), numberedTitle(node, "目录"), context.theme, 11);
        for (VNode child : node.childrenOrEmpty()) {
            addCatalogTocEntry(context, child);
        }
    }

    /**
     * 渲染正文章节与其子块。
     */
    private void addContentPages(DocxRenderContext context, List<VNode> contentNodes, Map<String, Object> props) throws IOException {
        String paginationStrategy = str(props.get("paginationStrategy"), "section");
        boolean sectionBreak = !"continuous".equalsIgnoreCase(paginationStrategy);
        int blockGapTwips = resolveBlockGapTwips(props);
        for (int i = 0; i < contentNodes.size(); i++) {
            VNode node = contentNodes.get(i);
            if ("catalog".equalsIgnoreCase(node.kind)) {
                addCatalogContent(context, node, blockGapTwips);
            } else {
                addFlatSectionContent(context, node, i, blockGapTwips);
            }
            if (sectionBreak && i < contentNodes.size() - 1) {
                pageBreak(context.document);
            }
        }
    }

    private void addCatalogContent(DocxRenderContext context, VNode catalog, int blockGapTwips) throws IOException {
        addHeading(context, numberedTitle(catalog, "目录"), Math.min(outlineLevel(catalog), 4), bookmarkNameFor(catalog, "catalog"));
        List<VNode> children = catalog.childrenOrEmpty();
        for (int i = 0; i < children.size(); i++) {
            VNode child = children.get(i);
            if ("catalog".equalsIgnoreCase(child.kind)) {
                addCatalogContent(context, child, blockGapTwips);
            } else if ("section".equalsIgnoreCase(child.kind)) {
                renderSectionBlocks(context, child, blockGapTwips);
            } else {
                nodeRenderers.render(context, child);
            }
            if (i < children.size() - 1) {
                appendGapParagraph(context.document, Math.max(0, blockGapTwips / 2));
            }
        }
    }

    private void addFlatSectionContent(DocxRenderContext context, VNode section, int index, int blockGapTwips) throws IOException {
        String title = section.propString("title", "章节 " + (index + 1));
        addHeading(context, title, 1, bookmarkNameFor(section, "section_" + (index + 1)));
        renderSectionBlocks(context, section, blockGapTwips);
    }

    private void renderSectionBlocks(DocxRenderContext context, VNode section, int blockGapTwips) throws IOException {
        List<VNode> blocks = section.childrenOrEmpty();
        for (int blockIndex = 0; blockIndex < blocks.size(); blockIndex++) {
            VNode block = blocks.get(blockIndex);
            nodeRenderers.render(context, block);
            if (blockIndex < blocks.size() - 1) {
                appendGapParagraph(context.document, blockGapTwips);
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
        addHeading(context, text, level, null);
    }

    private void addHeading(DocxRenderContext context, String text, int level, String bookmarkName) {
        int sectionGapTwips = resolveSectionGapTwips(context.rootProps());
        int bodyPaddingTwips = resolveBodyPaddingTwips(context.rootProps());
        XWPFParagraph p = context.document.createParagraph();
        setHeadingParagraphStyle(p, level);
        p.setAlignment(ParagraphAlignment.LEFT);
        p.setSpacingBefore(Math.max(headingSpacingBeforeTwips(level), level <= 1 ? bodyPaddingTwips / 2 : bodyPaddingTwips / 3));
        p.setSpacingAfter(Math.max(80, sectionGapTwips));
        BigInteger bookmarkId = null;
        if (bookmarkName != null && !bookmarkName.isBlank()) {
            bookmarkId = context.nextBookmarkId();
            CTBookmark bookmarkStart = p.getCTP().insertNewBookmarkStart(0);
            bookmarkStart.setName(bookmarkName);
            bookmarkStart.setId(bookmarkId);
        }
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setBold(true);
        run.setFontFamily(context.theme.fontPrimary());
        run.setColor(VisualStyle.toHexNoHash(context.theme.text()));
        run.setFontSize(level <= 1 ? 18 : 14);
        if (bookmarkId != null) {
            CTMarkupRange bookmarkEnd = p.getCTP().addNewBookmarkEnd();
            bookmarkEnd.setId(bookmarkId);
        }
    }

    private void setHeadingParagraphStyle(XWPFParagraph paragraph, int level) {
        int safeLevel = clampInt(level, 1, 6);
        String styleId = headingStyleId(safeLevel);
        paragraph.setStyle(styleId);
        var pPr = paragraph.getCTP().isSetPPr() ? paragraph.getCTP().getPPr() : paragraph.getCTP().addNewPPr();
        var pStyle = pPr.isSetPStyle() ? pPr.getPStyle() : pPr.addNewPStyle();
        pStyle.setVal(styleId);
        var outline = pPr.isSetOutlineLvl() ? pPr.getOutlineLvl() : pPr.addNewOutlineLvl();
        outline.setVal(BigInteger.valueOf(safeLevel - 1L));
    }

    private String headingStyleId(int level) {
        return "Heading" + clampInt(level, 1, 6);
    }

    private static int headingSpacingBeforeTwips(int level) {
        return level <= 1 ? 360 : 240;
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
     * 渲染表格块（含多级表头/合并/空数据行）。
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

        boolean hasDataRows = model.bodyRowCount() > 0;
        int totalRows = model.headerRowCount() + Math.max(1, model.bodyRowCount());
        XWPFTable table = context.document.createTable(totalRows, model.columnCount());
        int[] columnWidths = fitTableToPage(table, model, context.rootProps());
        int fontSize = tableFontSize(model.columnCount());

        fillDocxHeaderRows(context, table, model, fontSize);
        if (hasDataRows) {
            fillDocxBodyRows(context, table, model, fontSize);
        } else {
            fillNoDataRow(context, table.getRow(model.headerRowCount()), model.columnCount(), columnWidths, fontSize);
        }
        applyDocxMerges(table, model);
        if (configuration.word().table().repeatHeaderOnPageBreak() && model.repeatHeader()) {
            markHeaderRowsRepeat(table, model.headerRowCount());
        }
    }

    /**
     * 渲染复合表：多个子表纵向贴合输出，各子表保持自身列结构但共享同一页面宽度。
     */
    private void addCompositeTableBlock(DocxRenderContext context, VNode compositeNode) {
        List<TableModel> models = new ArrayList<>();
        for (VNode tableNode : compositeNode.childrenOrEmpty()) {
            if (!"table".equalsIgnoreCase(tableNode.kind)) {
                continue;
            }
            List<Map<String, Object>> rows = chartRowResolver.resolve(context.doc(), tableNode, null);
            TableModel model = tableSpecParser.parse(tableNode, rows);
            if (model.columnCount() > 0) {
                models.add(model);
            }
        }
        if (models.isEmpty()) {
            XWPFParagraph p = context.document.createParagraph();
            XWPFRun run = p.createRun();
            run.setText("未能解析有效复合表。");
            run.setFontFamily(context.theme.fontPrimary());
            run.setColor(VisualStyle.toHexNoHash(context.theme.muted()));
            run.setFontSize(10);
            return;
        }

        int baseColumns = compositeBaseColumnCount(models);
        int totalRows = models.stream().mapToInt(this::renderedRowCount).sum();
        XWPFTable table = context.document.createTable(Math.max(1, totalRows), baseColumns);
        int tableWidth = resolveWritablePageWidthTwips(context.rootProps());
        int[] columnWidths = equalColumnWidths(baseColumns, tableWidth);
        setFixedTableWidth(table, tableWidth, columnWidths);
        applyCellWidths(table, columnWidths);

        int rowOffset = 0;
        int fontSize = tableFontSize(models.stream().mapToInt(TableModel::columnCount).max().orElse(baseColumns));
        for (TableModel model : models) {
            fillCompositeRows(context, table, model, rowOffset, true, fontSize, baseColumns, columnWidths);
            if (model.bodyRowCount() > 0) {
                fillCompositeRows(context, table, model, rowOffset + model.headerRowCount(), false, fontSize, baseColumns, columnWidths);
            } else {
                fillCompositeNoDataRow(context, table.getRow(rowOffset + model.headerRowCount()), baseColumns, columnWidths, fontSize);
            }
            rowOffset += renderedRowCount(model);
        }
    }

    private int renderedRowCount(TableModel model) {
        return model.headerRowCount() + Math.max(1, model.bodyRowCount());
    }

    private void fillCompositeRows(
            DocxRenderContext context,
            XWPFTable table,
            TableModel model,
            int rowOffset,
            boolean header,
            int fontSize,
            int baseColumns,
            int[] columnWidths
    ) {
        List<List<TableCell>> rows = header ? model.headerRows() : model.bodyRows();
        for (int r = 0; r < rows.size(); r++) {
            XWPFTableRow tableRow = table.getRow(rowOffset + r);
            List<TableCell> cells = rows.get(r);
            List<CompositeCellSpan> spans = new ArrayList<>();
            Color bg = header || !model.zebra() || (r % 2 == 0) ? context.theme.panel() : context.theme.panelAlt();
            if (header) {
                bg = tableHeaderBackground(context);
            }
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = cells.get(c);
                if (cell.hidden()) {
                    continue;
                }
                int start = compositeGridPosition(c, model.columnCount(), baseColumns);
                int end = compositeGridPosition(Math.min(model.columnCount(), c + cell.colSpan()), model.columnCount(), baseColumns);
                int span = Math.max(1, end - start);
                XWPFTableCell tableCell = tableRow.getCell(start);
                styleCell(tableCell, bg);
                writeCellText(tableCell, cell.text(), context.theme, header, fontSize, context.theme.text());
                setParagraphAlign(tableCell, cell.align());
                for (int physical = start + 1; physical < start + span; physical++) {
                    XWPFTableCell follower = tableRow.getCell(physical);
                    styleCell(follower, bg);
                    writeCellText(follower, "", context.theme, header, fontSize, context.theme.text());
                }
                if (span > 1) {
                    spans.add(new CompositeCellSpan(start, span, sumWidths(columnWidths, start, span)));
                }
                if (cell.rowSpan() > 1) {
                    applyDocxMerge(table, rowOffset + r, start, cell.rowSpan(), 1);
                }
            }
            applyCompositeCellSpans(tableRow, spans);
            if (header && configuration.word().table().repeatHeaderOnPageBreak() && model.repeatHeader()) {
                markTableRowRepeat(table.getRow(rowOffset + r));
            }
        }
    }

    private void fillNoDataRow(
            DocxRenderContext context,
            XWPFTableRow row,
            int columnCount,
            int[] columnWidths,
            int fontSize
    ) {
        int safeColumnCount = Math.max(1, columnCount);
        for (int c = 0; c < safeColumnCount; c++) {
            XWPFTableCell cell = row.getCell(c);
            styleCell(cell, context.theme.panel());
            writeCellText(cell, c == 0 ? configuration.word().table().emptyText() : "", context.theme, false, fontSize, context.theme.muted());
            setParagraphAlign(cell, "center");
        }
        if (safeColumnCount > 1) {
            applyCompositeCellSpans(row, List.of(new CompositeCellSpan(0, safeColumnCount, sumWidths(columnWidths, 0, safeColumnCount))));
        }
    }

    private void fillCompositeNoDataRow(
            DocxRenderContext context,
            XWPFTableRow row,
            int baseColumns,
            int[] columnWidths,
            int fontSize
    ) {
        fillNoDataRow(context, row, baseColumns, columnWidths, fontSize);
    }

    private void applyCompositeCellSpans(XWPFTableRow row, List<CompositeCellSpan> spans) {
        for (int i = spans.size() - 1; i >= 0; i--) {
            CompositeCellSpan span = spans.get(i);
            XWPFTableCell anchor = row.getCell(span.start());
            CTTcPr tcPr = ensureTcPr(anchor);
            if (tcPr.isSetGridSpan()) {
                tcPr.getGridSpan().setVal(BigInteger.valueOf(span.span()));
            } else {
                tcPr.addNewGridSpan().setVal(BigInteger.valueOf(span.span()));
            }
            CTTblWidth tcW = tcPr.isSetTcW() ? tcPr.getTcW() : tcPr.addNewTcW();
            tcW.setType(STTblWidth.DXA);
            tcW.setW(BigInteger.valueOf(Math.max(1, span.widthTwips())));
            for (int physical = span.start() + span.span() - 1; physical > span.start(); physical--) {
                row.removeCell(physical);
            }
        }
    }

    private int compositeBaseColumnCount(List<TableModel> models) {
        int result = 1;
        for (TableModel model : models) {
            result = lcm(result, Math.max(1, model.columnCount()));
            if (result > 36) {
                return models.stream().mapToInt(TableModel::columnCount).max().orElse(1);
            }
        }
        return Math.max(1, result);
    }

    private int compositeGridPosition(int logicalColumn, int logicalColumnCount, int baseColumns) {
        int count = Math.max(1, logicalColumnCount);
        return Math.min(baseColumns, (int) Math.floor((logicalColumn / (double) count) * baseColumns));
    }

    private int sumWidths(int[] columnWidths, int start, int span) {
        int total = 0;
        for (int i = start; i < start + span && i < columnWidths.length; i++) {
            total += columnWidths[i];
        }
        return total;
    }

    private int lcm(int a, int b) {
        return Math.abs(a / gcd(a, b) * b);
    }

    private int gcd(int a, int b) {
        int x = Math.abs(a);
        int y = Math.abs(b);
        while (y != 0) {
            int next = x % y;
            x = y;
            y = next;
        }
        return Math.max(1, x);
    }

    /**
     * 写入 DOCX 表头矩阵。
     */
    private void fillDocxHeaderRows(DocxRenderContext context, XWPFTable table, TableModel model, int fontSize) {
        for (int r = 0; r < model.headerRowCount(); r++) {
            XWPFTableRow row = table.getRow(r);
            List<TableCell> header = model.headerRows().get(r);
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = header.get(c);
                XWPFTableCell tableCell = row.getCell(c);
                styleCell(tableCell, tableHeaderBackground(context));
                if (cell.hidden()) {
                    writeCellText(tableCell, "", context.theme, true, fontSize, context.theme.text());
                    continue;
                }
                writeCellText(tableCell, cell.text(), context.theme, true, fontSize, context.theme.text());
                setParagraphAlign(tableCell, cell.align());
            }
        }
    }

    /**
     * 写入 DOCX 数据区矩阵。
     */
    private void fillDocxBodyRows(DocxRenderContext context, XWPFTable table, TableModel model, int fontSize) {
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
                    writeCellText(tableCell, "", context.theme, false, fontSize, context.theme.text());
                    continue;
                }
                writeCellText(tableCell, cell.text(), context.theme, false, fontSize, context.theme.text());
                setParagraphAlign(tableCell, cell.align());
            }
        }
    }

    private int[] fitTableToPage(XWPFTable table, TableModel model, Map<String, Object> props) {
        int availableWidth = resolveWritablePageWidthTwips(props);
        int[] widths = scaledColumnWidths(model, availableWidth);
        setFixedTableWidth(table, availableWidth, widths);
        applyCellWidths(table, widths);
        return widths;
    }

    private int resolveWritablePageWidthTwips(Map<String, Object> props) {
        String pageSize = str(props.get("pageSize"), "A4");
        int pageWidth = "Letter".equalsIgnoreCase(pageSize) ? 12240 : 11906;
        PageMargins margins = resolvePageMargins(props);
        long writable = pageWidth - margins.leftTwips() - margins.rightTwips();
        return (int) Math.max(3600, writable);
    }

    private int resolveWritablePageHeightTwips(Map<String, Object> props) {
        String pageSize = str(props.get("pageSize"), "A4");
        int pageHeight = "Letter".equalsIgnoreCase(pageSize) ? 15840 : 16838;
        PageMargins margins = resolvePageMargins(props);
        long writable = pageHeight - margins.topTwips() - margins.bottomTwips();
        return (int) Math.max(9000, writable);
    }

    private int[] scaledColumnWidths(TableModel model, int availableWidth) {
        int columnCount = model.columnCount();
        int[] widths = new int[columnCount];
        if (columnCount <= 0) {
            return widths;
        }
        double totalDeclared = 0;
        for (int i = 0; i < columnCount; i++) {
            totalDeclared += Math.max(48.0, model.columns().get(i).width());
        }
        if (totalDeclared <= 0) {
            totalDeclared = columnCount;
        }
        int assigned = 0;
        for (int i = 0; i < columnCount; i++) {
            double declared = Math.max(48.0, model.columns().get(i).width());
            int width = (int) Math.round((declared / totalDeclared) * availableWidth);
            widths[i] = Math.max(1, width);
            assigned += widths[i];
        }
        if (assigned != availableWidth && columnCount > 0) {
            widths[columnCount - 1] = Math.max(1, widths[columnCount - 1] + availableWidth - assigned);
        }
        return widths;
    }

    private int[] equalColumnWidths(int columnCount, int availableWidth) {
        int safeColumnCount = Math.max(1, columnCount);
        int[] widths = new int[safeColumnCount];
        int baseWidth = Math.max(1, availableWidth / safeColumnCount);
        int assigned = 0;
        for (int i = 0; i < safeColumnCount; i++) {
            widths[i] = baseWidth;
            assigned += baseWidth;
        }
        widths[safeColumnCount - 1] = Math.max(1, widths[safeColumnCount - 1] + availableWidth - assigned);
        return widths;
    }

    private void setFixedTableWidth(XWPFTable table, int tableWidthTwips, int[] columnWidths) {
        CTTblPr tblPr = table.getCTTbl().getTblPr() == null
                ? table.getCTTbl().addNewTblPr()
                : table.getCTTbl().getTblPr();
        CTTblWidth tblW = tblPr.isSetTblW() ? tblPr.getTblW() : tblPr.addNewTblW();
        tblW.setType(STTblWidth.DXA);
        tblW.setW(BigInteger.valueOf(tableWidthTwips));

        CTTblLayoutType layout = tblPr.isSetTblLayout() ? tblPr.getTblLayout() : tblPr.addNewTblLayout();
        layout.setType(STTblLayoutType.FIXED);

        CTTblGrid grid = table.getCTTbl().getTblGrid() == null
                ? table.getCTTbl().addNewTblGrid()
                : table.getCTTbl().getTblGrid();
        while (grid.sizeOfGridColArray() > 0) {
            grid.removeGridCol(0);
        }
        for (int width : columnWidths) {
            CTTblGridCol gridCol = grid.addNewGridCol();
            gridCol.setW(BigInteger.valueOf(Math.max(1, width)));
        }
    }

    private void applyCellWidths(XWPFTable table, int[] columnWidths) {
        if (columnWidths == null || columnWidths.length == 0) {
            return;
        }
        for (XWPFTableRow row : table.getRows()) {
            List<XWPFTableCell> cells = row.getTableCells();
            for (int i = 0; i < cells.size() && i < columnWidths.length; i++) {
                CTTcPr tcPr = ensureTcPr(cells.get(i));
                CTTblWidth tcW = tcPr.isSetTcW() ? tcPr.getTcW() : tcPr.addNewTcW();
                tcW.setType(STTblWidth.DXA);
                tcW.setW(BigInteger.valueOf(Math.max(1, columnWidths[i])));
            }
        }
    }

    private int tableFontSize(int columnCount) {
        if (columnCount >= 12) {
            return 8;
        }
        if (columnCount >= 9) {
            return 9;
        }
        return 10;
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
            markTableRowRepeat(table.getRow(r));
        }
    }

    private void markTableRowRepeat(XWPFTableRow row) {
        CTTrPr trPr = row.getCtRow().isSetTrPr() ? row.getCtRow().getTrPr() : row.getCtRow().addNewTrPr();
        trPr.addNewTblHeader();
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

    private Color tableHeaderBackground(DocxRenderContext context) {
        return switch (configuration.word().table().headerBackground()) {
            case THEME_PRIMARY_SOFT -> context.theme.primarySoft();
        };
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
     * 提取正文入口节点。新 DSL 使用 catalog 树，旧 VDoc 仍可能直接给 section 列表。
     */
    private List<VNode> contentNodes(VNode root) {
        if (root == null) {
            return Collections.emptyList();
        }
        List<VNode> nodes = new ArrayList<>();
        for (VNode child : root.childrenOrEmpty()) {
            if ("catalog".equalsIgnoreCase(child.kind) || "section".equalsIgnoreCase(child.kind)) {
                nodes.add(child);
            }
        }
        return nodes;
    }

    /**
     * 递归提取 section 子节点，用于摘要统计。
     */
    private List<VNode> sectionNodes(VNode root) {
        if (root == null) {
            return Collections.emptyList();
        }
        List<VNode> sections = new ArrayList<>();
        collectSections(root, sections);
        return sections;
    }

    private void collectSections(VNode node, List<VNode> sections) {
        for (VNode child : node.childrenOrEmpty()) {
            if ("section".equalsIgnoreCase(child.kind)) {
                sections.add(child);
            } else if ("catalog".equalsIgnoreCase(child.kind) || "container".equalsIgnoreCase(child.kind)) {
                collectSections(child, sections);
            }
        }
    }

    private boolean hasCatalogNodes(List<VNode> nodes) {
        for (VNode node : nodes) {
            if ("catalog".equalsIgnoreCase(node.kind)) {
                return true;
            }
        }
        return false;
    }

    private String numberedTitle(VNode node, String fallback) {
        String title = node.propString("title", fallback);
        String number = node.propString("outlineNumber", "");
        if (number.isBlank()) {
            return title;
        }
        return number + " " + title;
    }

    private int outlineLevel(VNode node) {
        return clampInt(VNode.asDouble(node.propsOrEmpty().get("outlineLevel"), 1.0), 1, 6);
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
        p.setSpacingBefore(0);
        p.setSpacingAfter(0);
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

    private void addTocEntryText(XWPFParagraph paragraph, String anchor, String text, ThemeTokens theme, int fontSize) {
        if (configuration.word().toc().linkEnabled()) {
            addInternalHyperlink(paragraph, anchor, text, theme, fontSize);
            return;
        }
        XWPFRun run = paragraph.createRun();
        run.setText(text);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(fontSize);
        run.setColor(VisualStyle.toHexNoHash(theme.text()));
    }

    private void addInternalHyperlink(XWPFParagraph paragraph, String anchor, String text, ThemeTokens theme, int fontSize) {
        CTHyperlink hyperlink = paragraph.getCTP().addNewHyperlink();
        hyperlink.setAnchor(anchor);
        CTR ctr = hyperlink.addNewR();
        CTRPr rPr = ctr.addNewRPr();
        rPr.addNewColor().setVal(VisualStyle.toHexNoHash(theme.text()));
        rPr.addNewU().setVal(STUnderline.NONE);
        var fonts = rPr.addNewRFonts();
        fonts.setAscii(theme.fontPrimary());
        fonts.setEastAsia(theme.fontPrimary());
        rPr.addNewSz().setVal(BigInteger.valueOf(fontSize * 2L));
        ctr.addNewT().setStringValue(text);
    }

    private String bookmarkNameFor(VNode node, String fallback) {
        String raw = node == null ? fallback : VNode.asString(node.id, "");
        if (raw.isBlank() && node != null) {
            raw = node.propString("title", fallback);
        }
        if (raw.isBlank()) {
            raw = fallback;
        }
        String cleaned = raw.replaceAll("[^A-Za-z0-9_]", "_").replaceAll("_+", "_");
        if (cleaned.isBlank() || "_".equals(cleaned)) {
            cleaned = "node";
        }
        if (cleaned.length() > 36) {
            cleaned = cleaned.substring(0, 36);
        }
        String hash = Integer.toHexString(raw.hashCode()).replace('-', 'n');
        return "rs_" + cleaned + "_" + hash;
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
        private int bookmarkSequence = 0;

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

        private BigInteger nextBookmarkId() {
            bookmarkSequence += 1;
            return BigInteger.valueOf(bookmarkSequence);
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

    private record CompositeCellSpan(int start, int span, int widthTwips) {
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
     * 节点 kind=compositeTable 渲染器。
     */
    private final class CompositeTableNodeRenderer implements NodeRenderer<DocxRenderContext> {
        @Override
        public String kind() {
            return "compositeTable";
        }

        @Override
        public void render(DocxRenderContext context, VNode node) {
            addCompositeTableBlock(context, node);
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
