package com.chatbi.exporter.pptx;

import com.chatbi.exporter.chart.ChartSpec;
import com.chatbi.exporter.chart.ChartSpecParser;
import com.chatbi.exporter.chart.ChartRowResolver;
import com.chatbi.exporter.chart.ChartTypeCatalog;
import com.chatbi.exporter.chart.PoiChartRenderer;
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
import org.apache.poi.sl.usermodel.TableCell.BorderEdge;
import org.apache.poi.sl.usermodel.ShapeType;
import org.apache.poi.sl.usermodel.TextParagraph;
import org.apache.poi.sl.usermodel.VerticalAlignment;
import org.apache.poi.util.Units;
import org.apache.poi.xslf.usermodel.XMLSlideShow;
import org.apache.poi.xslf.usermodel.XSLFAutoShape;
import org.apache.poi.xslf.usermodel.XSLFChart;
import org.apache.poi.xslf.usermodel.XSLFSlide;
import org.apache.poi.xslf.usermodel.XSLFTable;
import org.apache.poi.xslf.usermodel.XSLFTableCell;
import org.apache.poi.xslf.usermodel.XSLFTableRow;
import org.apache.poi.xslf.usermodel.XSLFTextBox;
import org.apache.poi.xslf.usermodel.XSLFTextParagraph;
import org.apache.poi.xslf.usermodel.XSLFTextRun;
import org.apache.xmlbeans.XmlObject;
import org.openxmlformats.schemas.drawingml.x2006.main.CTTableCell;
import org.openxmlformats.schemas.drawingml.x2006.main.CTTextBody;

import java.awt.Color;
import java.awt.Dimension;
import java.awt.Rectangle;
import java.awt.geom.Rectangle2D;
import java.io.IOException;
import java.io.OutputStream;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * PPT DSL -> PPTX 导出器。
 * <p>
 * 负责按幻灯片节点树输出可编辑 PPTX：
 * - 文本块
 * - 图表块（优先原生 POI 图表）
 * - 表格块（含多级表头与合并）
 * </p>
 */
public class DeckPptxExporter implements DocumentExporter {
    private final StyleResolver styleResolver;
    private final ChartSpecParser chartSpecParser;
    private final ChartRowResolver chartRowResolver;
    private final PoiChartRenderer poiChartRenderer;
    private final TableSpecParser tableSpecParser;
    private final List<PptxChartFlavorRenderer> chartFlavorRenderers;
    private final RendererRegistry<PptxRenderContext> nodeRenderers;

    /**
     * 默认构造：使用内置样式解析与图表规格解析。
     */
    public DeckPptxExporter() {
        this(new DefaultStyleResolver(), new ChartSpecParser());
    }

    /**
     * 允许注入样式/图表解析器，便于测试与扩展。
     */
    public DeckPptxExporter(StyleResolver styleResolver, ChartSpecParser chartSpecParser) {
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
     * 注册图表风味渲染器（按 fallback 前插入）。
     */
    public DeckPptxExporter registerChartFlavorRenderer(PptxChartFlavorRenderer renderer) {
        PptxChartFlavorRenderer safe = Objects.requireNonNull(renderer, "renderer");
        int fallbackIndex = findFallbackIndex();
        if (fallbackIndex >= 0) {
            chartFlavorRenderers.add(fallbackIndex, safe);
        } else {
            chartFlavorRenderers.add(safe);
        }
        return this;
    }

    /**
     * 查找通用兜底渲染器位置。
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
        return ExportTarget.PPTX;
    }

    @Override
    public boolean supports(VDoc doc) {
        return doc != null && "ppt".equalsIgnoreCase(doc.docType);
    }

    /**
     * 兼容旧调用方式（不传 request）。
     */
    public void export(VDoc doc, Path output) throws IOException {
        export(doc, output, ExportRequest.defaults());
    }

    /**
     * PPTX 导出主流程：
     * 1) 解析主题与画布
     * 2) 渲染 slide 节点
     * 3) 写入输出文件
     */
    @Override
    public void export(VDoc doc, Path output, ExportRequest request) throws IOException {
        if (!supports(doc)) {
            throw new IllegalArgumentException("DeckPptxExporter only accepts ppt docType.");
        }
        if (output.getParent() != null) {
            Files.createDirectories(output.getParent());
        }

        ThemeTokens theme = styleResolver.resolve(doc, request);
        Map<String, Object> rootProps = doc.root == null ? Collections.emptyMap() : doc.root.propsOrEmpty();

        try (XMLSlideShow slideShow = new XMLSlideShow()) {
            slideShow.setPageSize(resolvePageSize(rootProps));
            List<VNode> slides = resolveSlides(doc.root);

            if (slides.isEmpty()) {
                XSLFSlide slide = slideShow.createSlide();
                addSimpleTitle(slide, doc.title == null ? "PPT 导出" : doc.title, theme);
            } else {
                for (int i = 0; i < slides.size(); i++) {
                    VNode slideNode = slides.get(i);
                    XSLFSlide slide = slideShow.createSlide();
                    drawSlide(slideShow, slide, slideNode, doc, theme, rootProps, i + 1, slides.size());
                }
            }

            try (OutputStream out = Files.newOutputStream(output)) {
                slideShow.write(out);
            }
        }
    }

    /**
     * 渲染单页幻灯片。
     */
    private void drawSlide(
            XMLSlideShow slideShow,
            XSLFSlide slide,
            VNode slideNode,
            VDoc doc,
            ThemeTokens theme,
            Map<String, Object> rootProps,
            int slideIndex,
            int slideCount
    ) throws IOException {
        Dimension pageSize = slideShow.getPageSize();
        int pageWidth = pageSize == null ? 960 : pageSize.width;
        int pageHeight = pageSize == null ? 540 : pageSize.height;
        Color bgColor = resolveSlideBg(slideNode, doc, theme);
        XSLFAutoShape bg = slide.createAutoShape();
        bg.setShapeType(ShapeType.RECT);
        bg.setAnchor(new Rectangle(0, 0, pageWidth, pageHeight));
        bg.setFillColor(bgColor);
        bg.setLineColor(bgColor);

        String slideTitle = slideNode.propString("title", "Slide");
        MasterSpec masterSpec = resolveMasterSpec(rootProps, doc, theme);
        MasterLayoutMetrics masterLayout = resolveMasterLayoutMetrics(rootProps, pageWidth, pageHeight);
        addMasterHeader(slide, slideTitle, masterSpec, masterLayout, theme, slideIndex, slideCount, pageWidth, pageHeight);
        addMasterFooter(slide, masterSpec, masterLayout, theme, slideIndex, slideCount, pageWidth, pageHeight);

        PptxRenderContext context = new PptxRenderContext(slideShow, slide, theme, chartSpecParser, rootProps, doc);
        for (VNode child : slideNode.childrenOrEmpty()) {
            nodeRenderers.render(context, child);
        }
    }

    /**
     * 解析幻灯片背景色（slide.props.bg > root.defaultBg > theme.canvas）。
     */
    private Color resolveSlideBg(VNode slideNode, VDoc doc, ThemeTokens theme) {
        String fallback = toHex(theme.canvas());
        String rootBg = doc.root == null ? fallback : doc.root.propString("defaultBg", fallback);
        String bg = VNode.asString(slideNode.propsOrEmpty().getOrDefault("bg", rootBg), fallback);
        try {
            return VisualStyle.color(bg);
        } catch (RuntimeException ignored) {
            return theme.canvas();
        }
    }

    private MasterSpec resolveMasterSpec(Map<String, Object> rootProps, VDoc doc, ThemeTokens theme) {
        boolean showHeader = VNode.asBoolean(rootProps.get("masterShowHeader"), true);
        boolean showFooter = VNode.asBoolean(rootProps.get("masterShowFooter"), true);
        boolean showSlideNo = VNode.asBoolean(rootProps.get("masterShowSlideNumber"), true);
        String headerText = VNode.asString(rootProps.get("masterHeaderText"), doc.title == null ? "" : doc.title);
        String footerText = VNode.asString(rootProps.get("masterFooterText"), "Visual Document OS");
        Color accent = parseStyleColor(rootProps.get("masterAccentColor"), theme.primary());
        return new MasterSpec(showHeader, showFooter, showSlideNo, headerText, footerText, accent);
    }

    private MasterLayoutMetrics resolveMasterLayoutMetrics(Map<String, Object> rootProps, int pageWidth, int pageHeight) {
        int defaultPaddingX = Math.max(16, Math.round(pageWidth * 0.025f));
        int defaultHeaderTop = Math.max(10, Math.round(pageHeight * 0.02f));
        int defaultHeaderHeight = Math.max(26, Math.round(pageHeight * 0.05f));
        int defaultFooterHeight = Math.max(22, Math.round(pageHeight * 0.045f));
        int defaultFooterBottom = Math.max(8, Math.round(pageHeight * 0.018f));

        int paddingX = clampInt(VNode.asDouble(rootProps.get("masterPaddingXPx"), defaultPaddingX), 0, Math.max(0, pageWidth / 2 - 20));
        int headerTop = clampInt(VNode.asDouble(rootProps.get("masterHeaderTopPx"), defaultHeaderTop), 0, Math.max(0, pageHeight - 24));
        int headerHeight = clampInt(VNode.asDouble(rootProps.get("masterHeaderHeightPx"), defaultHeaderHeight), 12, Math.max(12, pageHeight));
        int footerHeight = clampInt(VNode.asDouble(rootProps.get("masterFooterHeightPx"), defaultFooterHeight), 12, Math.max(12, pageHeight));
        int footerBottom = clampInt(VNode.asDouble(rootProps.get("masterFooterBottomPx"), defaultFooterBottom), 0, Math.max(0, pageHeight - 24));
        return new MasterLayoutMetrics(paddingX, headerTop, headerHeight, footerBottom, footerHeight);
    }

    private void addMasterHeader(
            XSLFSlide slide,
            String slideTitle,
            MasterSpec masterSpec,
            MasterLayoutMetrics masterLayout,
            ThemeTokens theme,
            int slideIndex,
            int slideCount,
            int pageWidth,
            int pageHeight
    ) {
        if (!masterSpec.showHeader()) {
            return;
        }
        int horizontalPadding = masterLayout.paddingX();
        int top = masterLayout.headerTop();
        int headerHeight = masterLayout.headerHeight();
        int lineTop = top + headerHeight + 1;

        XSLFAutoShape line = slide.createAutoShape();
        line.setShapeType(ShapeType.RECT);
        line.setAnchor(new Rectangle(horizontalPadding, lineTop, Math.max(10, pageWidth - horizontalPadding * 2), 1));
        line.setFillColor(masterSpec.accentColor());
        line.setLineColor(masterSpec.accentColor());

        XSLFTextBox box = slide.createTextBox();
        box.setAnchor(new Rectangle(horizontalPadding, top, Math.max(100, pageWidth - horizontalPadding * 2), headerHeight));
        box.setFillColor(new Color(255, 255, 255, 0));
        XSLFTextParagraph p = box.addNewTextParagraph();
        p.setTextAlign(TextParagraph.TextAlign.LEFT);
        XSLFTextRun run = p.addNewTextRun();
        String leftText = masterSpec.headerText().isBlank() ? slideTitle : masterSpec.headerText() + " · " + slideTitle;
        run.setText(leftText);
        run.setFontSize(Math.max(11.0, pageHeight / 42.0));
        run.setFontFamily(theme.fontPrimary());
        run.setBold(true);
        run.setFontColor(theme.muted());

        if (masterSpec.showSlideNumber() && !masterSpec.showFooter()) {
            XSLFTextRun rightRun = p.addNewTextRun();
            rightRun.setText("    " + slideIndex + "/" + slideCount);
            rightRun.setFontSize(Math.max(10.0, pageHeight / 48.0));
            rightRun.setFontFamily(theme.fontPrimary());
            rightRun.setBold(false);
            rightRun.setFontColor(theme.muted());
        }
    }

    private void addMasterFooter(
            XSLFSlide slide,
            MasterSpec masterSpec,
            MasterLayoutMetrics masterLayout,
            ThemeTokens theme,
            int slideIndex,
            int slideCount,
            int pageWidth,
            int pageHeight
    ) {
        if (!masterSpec.showFooter()) {
            return;
        }
        int horizontalPadding = masterLayout.paddingX();
        int footerHeight = masterLayout.footerHeight();
        int top = Math.max(0, pageHeight - footerHeight - masterLayout.footerBottom());
        int lineTop = Math.max(0, top - 2);

        XSLFAutoShape line = slide.createAutoShape();
        line.setShapeType(ShapeType.RECT);
        line.setAnchor(new Rectangle(horizontalPadding, lineTop, Math.max(10, pageWidth - horizontalPadding * 2), 1));
        line.setFillColor(masterSpec.accentColor());
        line.setLineColor(masterSpec.accentColor());

        XSLFTextBox box = slide.createTextBox();
        box.setAnchor(new Rectangle(horizontalPadding, top, Math.max(100, pageWidth - horizontalPadding * 2), footerHeight));
        box.setFillColor(new Color(255, 255, 255, 0));
        XSLFTextParagraph p = box.addNewTextParagraph();
        p.setTextAlign(TextParagraph.TextAlign.LEFT);
        XSLFTextRun run = p.addNewTextRun();
        run.setText(masterSpec.footerText());
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(Math.max(10.0, pageHeight / 50.0));
        run.setFontColor(theme.muted());

        if (masterSpec.showSlideNumber()) {
            XSLFTextRun rightRun = p.addNewTextRun();
            rightRun.setText("    #" + slideIndex + "/" + slideCount);
            rightRun.setFontFamily(theme.fontPrimary());
            rightRun.setFontSize(Math.max(9.5, pageHeight / 54.0));
            rightRun.setFontColor(theme.muted());
        }
    }

    /**
     * 渲染文本块。
     */
    private void addTextShape(PptxRenderContext context, VNode textNode) {
        Rectangle rect = resolveRect(textNode, 80, 80, 280, 120);
        XSLFTextBox box = context.slide.createTextBox();
        box.setAnchor(rect);
        Color bg = parseStyleColor(textNode.styleOrEmpty().get("bg"), context.theme.panel());
        box.setFillColor(bg);
        box.setLineColor(context.theme.border());
        box.setLineWidth(1.0);

        String text = textNode.propString("text", "");
        XSLFTextParagraph p = box.addNewTextParagraph();
        p.setTextAlign(TextParagraph.TextAlign.LEFT);
        XSLFTextRun run = p.addNewTextRun();
        run.setText(text);
        run.setFontFamily(context.theme.fontPrimary());
        run.setFontColor(context.theme.text());
        run.setFontSize(resolveFontSize(textNode, 14.0));
        run.setBold(VNode.asBoolean(textNode.styleOrEmpty().get("bold"), false));
    }

    /**
     * 渲染图表卡片：
     * - 优先原生图表
     * - 失败时输出占位卡片
     */
    private void addChartCard(
            PptxRenderContext context,
            ChartSpec spec,
            VNode chartNode,
            List<Map<String, Object>> rows
    ) {
        Rectangle rect = resolveRect(chartNode, 120, 120, 420, 250);
        boolean nativeRendered = renderNativeChartIfNeeded(context, spec, rows, chartNode);
        if (nativeRendered) {
            return;
        }

        // Native chart not available: keep a minimal placeholder instead of verbose debug text.
        XSLFAutoShape card = context.slide.createAutoShape();
        card.setShapeType(ShapeType.ROUND_RECT);
        card.setAnchor(rect);
        card.setFillColor(context.theme.panelAlt());
        card.setLineColor(context.theme.border());
        card.setLineWidth(1.2);

        addCardLine(card, context.theme, "图表: " + spec.title(), 16.0, context.theme.text(), true);
        if (rows == null || rows.isEmpty()) {
            addCardLine(card, context.theme, "暂无可用数据，未生成原生图表。", 11.0, context.theme.muted(), false);
        } else {
            addCardLine(card, context.theme, "当前图表类型在此环境下未生成原生图表，已使用占位卡片。", 11.0, context.theme.muted(), false);
        }
    }

    /**
     * 渲染表格块（含合并单元格）。
     */
    private void addTableShape(PptxRenderContext context, VNode tableNode, List<Map<String, Object>> rows) {
        TableModel table = tableSpecParser.parse(tableNode, rows);
        if (table.columnCount() <= 0) {
            addUnsupportedShape(context, tableNode);
            return;
        }

        Rectangle rect = resolveRect(tableNode, 100, 100, 520, 260);
        XSLFTable xslfTable = context.slide().createTable();
        xslfTable.setAnchor(rect);

        int totalRows = Math.max(1, table.totalRowCount());
        int rowHeight = Math.max(18, rect.height / totalRows);
        for (int r = 0; r < totalRows; r++) {
            XSLFTableRow row = xslfTable.addRow();
            row.setHeight(rowHeight);
            for (int c = 0; c < table.columnCount(); c++) {
                row.addCell();
            }
        }

        applyColumnWidths(xslfTable, table, rect.width);
        fillHeaderCells(context, xslfTable, table);
        fillBodyCells(context, xslfTable, table);
        applyTableMerges(xslfTable, table);
        normalizeTableCellTextBodies(xslfTable);
        xslfTable.updateCellAnchor();
    }

    /**
     * 按列权重分配 PPT 表格列宽。
     */
    private void applyColumnWidths(XSLFTable table, TableModel model, int totalWidth) {
        double sum = model.columns().stream().mapToDouble(col -> Math.max(1.0, col.width())).sum();
        if (sum <= 0.0) {
            sum = model.columnCount();
        }
        for (int c = 0; c < model.columnCount(); c++) {
            double weight = Math.max(1.0, model.columns().get(c).width());
            double width = Math.max(36.0, (weight / sum) * totalWidth);
            table.setColumnWidth(c, width);
        }
    }

    /**
     * 写入表头单元格。
     */
    private void fillHeaderCells(PptxRenderContext context, XSLFTable table, TableModel model) {
        for (int r = 0; r < model.headerRowCount(); r++) {
            List<TableCell> row = model.headerRows().get(r);
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                XSLFTableCell tableCell = table.getCell(r, c);
                if (cell.hidden()) {
                    clearTableCell(tableCell);
                    continue;
                }
                styleTableCell(tableCell, context.theme().primarySoft());
                writeTableCellText(tableCell, cell.text(), context.theme(), true, 11);
                setTableCellAlign(tableCell, cell.align());
            }
        }
    }

    /**
     * 写入数据区单元格。
     */
    private void fillBodyCells(PptxRenderContext context, XSLFTable table, TableModel model) {
        for (int r = 0; r < model.bodyRowCount(); r++) {
            List<TableCell> row = model.bodyRows().get(r);
            int tableRow = model.headerRowCount() + r;
            Color rowBg = model.zebra() && (r % 2 == 1) ? context.theme().panelAlt() : context.theme().panel();
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                XSLFTableCell tableCell = table.getCell(tableRow, c);
                if (cell.hidden()) {
                    clearTableCell(tableCell);
                    continue;
                }
                styleTableCell(tableCell, rowBg);
                writeTableCellText(tableCell, cell.text(), context.theme(), false, 10);
                setTableCellAlign(tableCell, cell.align());
            }
        }
    }

    private void styleTableCell(XSLFTableCell cell, Color background) {
        cell.setFillColor(background);
        cell.setVerticalAlignment(VerticalAlignment.MIDDLE);
        cell.setBorderColor(BorderEdge.top, new Color(0xD7, 0xE3, 0xF7));
        cell.setBorderColor(BorderEdge.bottom, new Color(0xD7, 0xE3, 0xF7));
        cell.setBorderColor(BorderEdge.left, new Color(0xD7, 0xE3, 0xF7));
        cell.setBorderColor(BorderEdge.right, new Color(0xD7, 0xE3, 0xF7));
        cell.setBorderWidth(BorderEdge.top, 0.75);
        cell.setBorderWidth(BorderEdge.bottom, 0.75);
        cell.setBorderWidth(BorderEdge.left, 0.75);
        cell.setBorderWidth(BorderEdge.right, 0.75);
    }

    private void setTableCellAlign(XSLFTableCell cell, String align) {
        TextParagraph.TextAlign textAlign = switch (align) {
            case "center" -> TextParagraph.TextAlign.CENTER;
            case "right" -> TextParagraph.TextAlign.RIGHT;
            default -> TextParagraph.TextAlign.LEFT;
        };
        for (XSLFTextParagraph paragraph : cell.getTextParagraphs()) {
            paragraph.setTextAlign(textAlign);
        }
    }

    private void clearTableCell(XSLFTableCell cell) {
        cell.clearText();
        cell.setFillColor(new Color(255, 255, 255, 0));
    }

    private void writeTableCellText(
            XSLFTableCell cell,
            String text,
            ThemeTokens theme,
            boolean bold,
            double fontSize
    ) {
        cell.clearText();
        XSLFTextParagraph paragraph = cell.addNewTextParagraph();
        XSLFTextRun run = paragraph.addNewTextRun();
        run.setText(text == null ? "" : text);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(fontSize);
        run.setBold(bold);
        run.setFontColor(theme.text());
    }

    /**
     * 应用 PPT 原生合并单元格。
     */
    private void applyTableMerges(XSLFTable table, TableModel model) {
        for (int r = 0; r < model.headerRowCount(); r++) {
            List<TableCell> row = model.headerRows().get(r);
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                if (!cell.hidden() && (cell.rowSpan() > 1 || cell.colSpan() > 1)) {
                    table.mergeCells(r, r + cell.rowSpan() - 1, c, c + cell.colSpan() - 1);
                }
            }
        }
        for (int r = 0; r < model.bodyRowCount(); r++) {
            List<TableCell> row = model.bodyRows().get(r);
            int baseRow = model.headerRowCount() + r;
            for (int c = 0; c < model.columnCount(); c++) {
                TableCell cell = row.get(c);
                if (!cell.hidden() && (cell.rowSpan() > 1 || cell.colSpan() > 1)) {
                    table.mergeCells(baseRow, baseRow + cell.rowSpan() - 1, c, c + cell.colSpan() - 1);
                }
            }
        }
    }

    /**
     * 归一化单元格文本 XML，规避部分 Office 版本打开修复提示。
     */
    private void normalizeTableCellTextBodies(XSLFTable table) {
        int rowCount = table.getNumberOfRows();
        if (rowCount <= 0) {
            return;
        }
        int colCount = table.getNumberOfColumns();
        for (int r = 0; r < rowCount; r++) {
            for (int c = 0; c < colCount; c++) {
                XSLFTableCell cell = table.getCell(r, c);
                if (cell == null) {
                    continue;
                }
                XmlObject xml = cell.getXmlObject();
                if (!(xml instanceof CTTableCell ctCell)) {
                    continue;
                }
                CTTextBody txBody = ctCell.isSetTxBody() ? ctCell.getTxBody() : ctCell.addNewTxBody();
                if (txBody.getBodyPr() == null) {
                    txBody.addNewBodyPr();
                }
                if (!txBody.isSetLstStyle()) {
                    txBody.addNewLstStyle();
                }
                if (txBody.sizeOfPArray() <= 0) {
                    txBody.addNewP();
                }
            }
        }
    }

    /**
     * 尝试绘制原生图表；异常时静默回退。
     */
    private boolean renderNativeChartIfNeeded(
            PptxRenderContext context,
            ChartSpec spec,
            List<Map<String, Object>> rows,
            VNode chartNode
    ) {
        boolean nativeChartEnabled = VNode.asBoolean(context.rootProps().get("nativeChartEnabled"), true);
        if (!nativeChartEnabled || rows == null || rows.isEmpty()) {
            return false;
        }
        try {
            Rectangle anchor = resolveRect(chartNode, 120, 120, 420, 250);
            XSLFChart chart = createAnchoredChart(context, anchor);
            if (chart == null) {
                return false;
            }
            return poiChartRenderer.render(chart, spec, rows);
        } catch (Exception ignored) {
            return false;
        }
    }

    /**
     * 兼容不同 POI 版本的 chart 创建 API。
     */
    private XSLFChart createAnchoredChart(PptxRenderContext context, Rectangle anchor) {
        Rectangle2D emuAnchor = toEmuAnchor(anchor);
        try {
            Method createChartNoArg = XMLSlideShow.class.getMethod("createChart");
            XSLFChart chart = (XSLFChart) createChartNoArg.invoke(context.slideShow());
            Method addChart = XSLFSlide.class.getMethod("addChart", XSLFChart.class, Rectangle2D.class);
            // POI XSLF chart frame expects EMU coordinates in this API branch.
            addChart.invoke(context.slide(), chart, emuAnchor);
            return chart;
        } catch (Exception ignored) {
            // fallback to older API branch
        }

        try {
            Method createChartWithSlide = XMLSlideShow.class.getMethod("createChart", XSLFSlide.class);
            Object created = createChartWithSlide.invoke(context.slideShow(), context.slide());
            if (!(created instanceof XSLFChart chart)) {
                return null;
            }
            tryAnchorGraphicFrame(chart, emuAnchor);
            return chart;
        } catch (Exception ignored) {
            return null;
        }
    }

    /**
     * 坐标单位转换：像素 -> EMU。
     */
    private Rectangle2D toEmuAnchor(Rectangle anchor) {
        return new Rectangle2D.Double(
                Units.toEMU(anchor.getX()),
                Units.toEMU(anchor.getY()),
                Units.toEMU(anchor.getWidth()),
                Units.toEMU(anchor.getHeight())
        );
    }

    /**
     * 尝试在旧 API 分支上设置图表锚点（best-effort）。
     */
    private void tryAnchorGraphicFrame(XSLFChart chart, Rectangle2D emuAnchor) {
        try {
            Method getGraphicFrame = XSLFChart.class.getMethod("getGraphicFrame");
            Object frame = getGraphicFrame.invoke(chart);
            if (frame == null) {
                return;
            }
            Method setAnchor = frame.getClass().getMethod("setAnchor", Rectangle2D.class);
            setAnchor.invoke(frame, emuAnchor);
        } catch (Exception ignored) {
            // best-effort anchor
        }
    }

    private String chartDetails(ChartSpec spec) {
        List<String> parts = new ArrayList<>();
        if (!spec.dimensionField().isBlank()) {
            parts.add("维度: " + spec.dimensionField());
        }
        if (!spec.measureFields().isEmpty()) {
            parts.add("指标: " + String.join(", ", spec.measureFields()));
        }
        if (!spec.seriesField().isBlank()) {
            parts.add("分组: " + spec.seriesField());
        }
        if (spec.dualAxis()) {
            parts.add("第二轴: " + spec.secondAxisField());
        }
        if (spec.filtersCount() > 0) {
            parts.add("过滤器: " + spec.filtersCount());
        }
        if (spec.computedFieldsCount() > 0) {
            parts.add("计算字段: " + spec.computedFieldsCount());
        }
        return String.join(" | ", parts);
    }

    private void renderPaletteStrip(PptxRenderContext context, Rectangle rect, List<String> palette) {
        int dots = Math.min(8, palette.size());
        int startX = rect.x + 12;
        int y = rect.y + rect.height - 16;
        for (int i = 0; i < dots; i++) {
            XSLFAutoShape dot = context.slide.createAutoShape();
            dot.setShapeType(ShapeType.ELLIPSE);
            dot.setAnchor(new Rectangle(startX + i * 14, y, 9, 9));
            Color color = parseStyleColor(palette.get(i), context.theme.primary());
            dot.setFillColor(color);
            dot.setLineColor(color);
        }
    }

    private void addCardLine(
            XSLFAutoShape card,
            ThemeTokens theme,
            String text,
            double fontSize,
            Color color,
            boolean bold
    ) {
        appendLine(card, theme, text, fontSize, color, bold);
    }

    private static void appendLine(
            XSLFAutoShape card,
            ThemeTokens theme,
            String text,
            double fontSize,
            Color color,
            boolean bold
    ) {
        XSLFTextParagraph paragraph = card.addNewTextParagraph();
        paragraph.setTextAlign(TextParagraph.TextAlign.LEFT);
        XSLFTextRun run = paragraph.addNewTextRun();
        run.setText(text);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(fontSize);
        run.setFontColor(color);
        run.setBold(bold);
    }

    /**
     * 解析 chartType 对应风味渲染器。
     */
    private PptxChartFlavorRenderer resolveFlavor(String chartType) {
        for (PptxChartFlavorRenderer renderer : chartFlavorRenderers) {
            if (renderer.supports(chartType)) {
                return renderer;
            }
        }
        return chartFlavorRenderers.get(chartFlavorRenderers.size() - 1);
    }

    /**
     * 未支持节点占位渲染。
     */
    private void addUnsupportedShape(PptxRenderContext context, VNode node) {
        Rectangle rect = resolveRect(node, 80, 80, 220, 90);
        XSLFAutoShape box = context.slide.createAutoShape();
        box.setShapeType(ShapeType.RECT);
        box.setAnchor(rect);
        box.setFillColor(context.theme.panelAlt());
        box.setLineColor(context.theme.border());

        XSLFTextParagraph p = box.addNewTextParagraph();
        XSLFTextRun run = p.addNewTextRun();
        run.setText("未支持块: " + VNode.asString(node.kind, "-"));
        run.setFontFamily(context.theme.fontPrimary());
        run.setFontSize(12.0);
        run.setFontColor(context.theme.muted());
    }

    /**
     * 无 slide 时输出简版封面页。
     */
    private void addSimpleTitle(XSLFSlide slide, String title, ThemeTokens theme) {
        XSLFTextBox box = slide.createTextBox();
        box.setAnchor(new Rectangle(80, 120, 760, 120));
        XSLFTextParagraph p = box.addNewTextParagraph();
        p.setTextAlign(TextParagraph.TextAlign.CENTER);
        XSLFTextRun run = p.addNewTextRun();
        run.setText(title);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(30.0);
        run.setBold(true);
        run.setFontColor(theme.text());
    }

    /**
     * 过滤根节点下 kind=slide 的子节点。
     */
    private List<VNode> resolveSlides(VNode root) {
        if (root == null) {
            return Collections.emptyList();
        }
        return root.childrenOrEmpty().stream()
                .filter(node -> "slide".equalsIgnoreCase(node.kind))
                .toList();
    }

    /**
     * 解析页面比例（16:9/4:3）。
     */
    private Dimension resolvePageSize(Map<String, Object> rootProps) {
        String size = VNode.asString(rootProps.get("size"), "16:9");
        if ("4:3".equalsIgnoreCase(size)) {
            return new Dimension(960, 720);
        }
        return new Dimension(960, 540);
    }

    /**
     * 从 layout 读取矩形区域并加下限保护。
     */
    private Rectangle resolveRect(VNode node, int x, int y, int w, int h) {
        int rx = (int) Math.round(node.layoutDouble("x", x));
        int ry = (int) Math.round(node.layoutDouble("y", y));
        int rw = (int) Math.round(node.layoutDouble("w", w));
        int rh = (int) Math.round(node.layoutDouble("h", h));
        return new Rectangle(rx, ry, Math.max(60, rw), Math.max(40, rh));
    }

    private double resolveFontSize(VNode node, double fallback) {
        return Math.max(10.0, node.styleDouble("fontSize", fallback));
    }

    private int clampInt(double value, int min, int max) {
        int rounded = (int) Math.round(value);
        return Math.max(min, Math.min(max, rounded));
    }

    private Color parseStyleColor(Object raw, Color fallback) {
        if (raw == null) {
            return fallback;
        }
        try {
            return VisualStyle.color(String.valueOf(raw));
        } catch (RuntimeException ignored) {
            return fallback;
        }
    }

    private String toHex(Color color) {
        return "#" + VisualStyle.toHexNoHash(color);
    }

    private record MasterSpec(
            boolean showHeader,
            boolean showFooter,
            boolean showSlideNumber,
            String headerText,
            String footerText,
            Color accentColor
    ) {
    }

    private record MasterLayoutMetrics(
            int paddingX,
            int headerTop,
            int headerHeight,
            int footerBottom,
            int footerHeight
    ) {
    }

    /**
     * PPT 渲染上下文。
     */
    public static final class PptxRenderContext {
        private final XMLSlideShow slideShow;
        private final XSLFSlide slide;
        private final ThemeTokens theme;
        private final ChartSpecParser chartSpecParser;
        private final Map<String, Object> rootProps;
        private final VDoc doc;

        private PptxRenderContext(
                XMLSlideShow slideShow,
                XSLFSlide slide,
                ThemeTokens theme,
                ChartSpecParser chartSpecParser,
                Map<String, Object> rootProps,
                VDoc doc
        ) {
            this.slideShow = slideShow;
            this.slide = slide;
            this.theme = theme;
            this.chartSpecParser = chartSpecParser;
            this.rootProps = rootProps;
            this.doc = doc;
        }

        public XMLSlideShow slideShow() {
            return slideShow;
        }

        public XSLFSlide slide() {
            return slide;
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
    public static final class PptxChartFlavorContext {
        private final XSLFAutoShape card;
        private final ThemeTokens theme;

        private PptxChartFlavorContext(XSLFAutoShape card, ThemeTokens theme) {
            this.card = card;
            this.theme = theme;
        }

        public ThemeTokens theme() {
            return theme;
        }

        public void appendInfoLine(String text) {
            DeckPptxExporter.appendLine(card, theme, text, 10.0, theme.text(), false);
        }

        public void appendLine(String text, double fontSize, Color color, boolean bold) {
            DeckPptxExporter.appendLine(card, theme, text, fontSize, color, bold);
        }
    }

    /**
     * 节点 kind=text 渲染器。
     */
    private final class TextNodeRenderer implements NodeRenderer<PptxRenderContext> {
        @Override
        public String kind() {
            return "text";
        }

        @Override
        public void render(PptxRenderContext context, VNode node) {
            addTextShape(context, node);
        }
    }

    /**
     * 节点 kind=chart 渲染器。
     */
    private final class ChartNodeRenderer implements NodeRenderer<PptxRenderContext> {
        @Override
        public String kind() {
            return "chart";
        }

        @Override
        public void render(PptxRenderContext context, VNode node) {
            ChartSpec spec = context.chartSpecParser.parse(node);
            List<Map<String, Object>> rows = chartRowResolver.resolve(context.doc(), node, spec);
            addChartCard(context, spec, node, rows);
        }
    }

    /**
     * 节点 kind=table 渲染器。
     */
    private final class TableNodeRenderer implements NodeRenderer<PptxRenderContext> {
        @Override
        public String kind() {
            return "table";
        }

        @Override
        public void render(PptxRenderContext context, VNode node) {
            List<Map<String, Object>> rows = chartRowResolver.resolve(context.doc(), node, null);
            addTableShape(context, node, rows);
        }
    }

    /**
     * 未支持节点兜底渲染器。
     */
    private final class UnsupportedNodeRenderer implements NodeRenderer<PptxRenderContext> {
        @Override
        public String kind() {
            return "__fallback__";
        }

        @Override
        public void render(PptxRenderContext context, VNode node) {
            addUnsupportedShape(context, node);
        }
    }

    /**
     * 图表风味渲染接口（占位卡片策略）。
     */
    public interface PptxChartFlavorRenderer {
        boolean supports(String chartType);

        void render(PptxChartFlavorContext context, ChartSpec spec);
    }

    private final class TrendFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("line")
                    || normalized.equals("scatter")
                    || normalized.equals("combo")
                    || normalized.equals("parallel");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("趋势策略: 适合时序分析，可扩展真实折线图元渲染器。");
        }
    }

    private final class ComparisonFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("bar")
                    || normalized.equals("radar")
                    || normalized.equals("boxplot");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("对比策略: 适合分类对比，可扩展分组/堆叠条形图策略。");
        }
    }

    private final class CompositionFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("pie");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("构成策略: 适合份额表达，可扩展扇区标签与排序策略。");
        }
    }

    private final class TableFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("heatmap");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("明细策略: 适合复杂分析，可扩展分页虚拟化数据渲染。");
        }
    }

    private final class RelationFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("sankey") || normalized.equals("graph");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("关系策略: 支持链路/关系表达，建议补充 node/link 字段绑定。");
        }
    }

    private final class MatrixFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("treemap")
                    || normalized.equals("sunburst")
                    || normalized.equals("funnel")
                    || normalized.equals("gauge");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("层次策略: 适合结构分层表达，可聚焦核心分支与占比路径。");
        }
    }

    private final class TimeWindowFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            String normalized = normalize(chartType);
            return normalized.equals("calendar")
                    || normalized.equals("kline");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("时窗策略: 适合日期/交易序列分析，建议按 day/week 粒度渲染。");
        }
    }

    private final class CustomFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            return normalize(chartType).equals("custom");
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("自定义策略: 已生成可商用基础图形，可进一步接入专用渲染插件。");
        }
    }

    private final class GenericFlavorRenderer implements PptxChartFlavorRenderer {
        @Override
        public boolean supports(String chartType) {
            return true;
        }

        @Override
        public void render(PptxChartFlavorContext context, ChartSpec spec) {
            context.appendInfoLine("通用策略: 未命中专用类型，已走默认图卡策略。");
        }
    }

    private String normalize(String chartType) {
        return ChartTypeCatalog.normalize(chartType);
    }
}
