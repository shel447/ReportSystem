package report.system.exporter.pptx;

import org.apache.poi.xslf.usermodel.*;
import report.system.exporter.core.DocumentExporter;
import report.system.exporter.core.ExportRequest;
import report.system.exporter.core.ExportTarget;
import report.system.exporter.model.*;
import report.system.exporter.style.StyleResolver;
import report.system.exporter.style.ThemeTokens;

import java.awt.*;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;

public final class ReportPptxExporter implements DocumentExporter {

    private static final int SLIDE_WIDTH_EMU = 9144000;
    private static final int SLIDE_HEIGHT_EMU = 5143500;

    @Override
    public ExportTarget target() {
        return ExportTarget.PPTX;
    }

    @Override
    public boolean supports(ReportDslModel dsl) {
        return true;
    }

    @Override
    public void export(ReportDslModel dsl, Path output, ExportRequest request) throws IOException {
        StyleResolver style = new StyleResolver(request.theme());
        ThemeTokens theme = style.tokens();

        try (XMLSlideShow pptx = new XMLSlideShow()) {
            pptx.setPageSize(new Dimension(SLIDE_WIDTH_EMU / 9525, SLIDE_HEIGHT_EMU / 9525));

            renderCoverSlide(pptx, dsl, theme);

            renderTocSlide(pptx, dsl, theme);

            if ("paged".equals(dsl.structureType)) {
                renderPagedContent(pptx, dsl, theme);
            } else {
                renderFlowContent(pptx, dsl, theme);
            }

            if (dsl.summary != null && dsl.summary.overview != null && !dsl.summary.overview.isBlank()) {
                renderSummarySlide(pptx, dsl.summary, theme);
            }

            if (dsl.backCover != null) {
                renderBackCoverSlide(pptx, dsl.backCover, theme);
            }

            try (FileOutputStream fos = new FileOutputStream(output.toFile())) {
                pptx.write(fos);
            }
        }
    }

    private void renderCoverSlide(XMLSlideShow pptx, ReportDslModel dsl, ThemeTokens theme) {
        XSLFSlide slide = pptx.createSlide();

        String title = "";
        if (dsl.cover != null && dsl.cover.title != null && !dsl.cover.title.isBlank()) {
            title = dsl.cover.title;
        } else if (dsl.basicInfo != null && dsl.basicInfo.title != null) {
            title = dsl.basicInfo.title;
        }

        addTextBox(slide, title, 50, 150, 860, 100, theme.fontPrimary(), theme.titleSizePt(), true, theme.primary(), true);

        if (dsl.basicInfo != null && dsl.basicInfo.subTitle != null && !dsl.basicInfo.subTitle.isBlank()) {
            addTextBox(slide, dsl.basicInfo.subTitle, 50, 260, 860, 50, theme.fontPrimary(), theme.heading2SizePt(), false, theme.secondary(), true);
        }

        StringBuilder info = new StringBuilder();
        if (dsl.cover != null) {
            if (dsl.cover.author != null) info.append(dsl.cover.author).append("  ");
            if (dsl.cover.date != null) info.append(dsl.cover.date);
        }
        if (!info.isEmpty()) {
            addTextBox(slide, info.toString(), 50, 340, 860, 40, theme.fontSecondary(), theme.bodySizePt(), false, theme.secondary(), true);
        }
    }

    private void renderTocSlide(XMLSlideShow pptx, ReportDslModel dsl, ThemeTokens theme) {
        List<ReportCatalog> catalogs = dsl.catalogs != null ? dsl.catalogs : List.of();
        if (catalogs.isEmpty()) return;

        XSLFSlide slide = pptx.createSlide();
        addTextBox(slide, "目录", 40, 20, 880, 40, theme.fontPrimary(), theme.heading1SizePt(), true, theme.primary(), false);

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < catalogs.size(); i++) {
            sb.append(i + 1).append(". ").append(catalogs.get(i).resolvedTitle()).append("\n");
        }
        addTextBox(slide, sb.toString(), 60, 70, 840, 400, theme.fontPrimary(), theme.bodySizePt(), false, null, false);
    }

    private void renderFlowContent(XMLSlideShow pptx, ReportDslModel dsl, ThemeTokens theme) {
        List<ReportCatalog> catalogs = dsl.catalogs != null ? dsl.catalogs : List.of();
        for (ReportCatalog catalog : catalogs) {
            renderCatalogSlides(pptx, catalog, theme);
        }
    }

    private void renderCatalogSlides(XMLSlideShow pptx, ReportCatalog catalog, ThemeTokens theme) {
        XSLFSlide sectionSlide = pptx.createSlide();
        addTextBox(sectionSlide, catalog.resolvedTitle(), 50, 180, 860, 80, theme.fontPrimary(), theme.heading1SizePt(), true, theme.primary(), true);

        if (catalog.sections != null) {
            for (ReportSection section : catalog.sections) {
                renderSectionSlide(pptx, section, catalog.resolvedTitle(), theme);
            }
        }

        if (catalog.subCatalogs != null) {
            for (ReportCatalog sub : catalog.subCatalogs) {
                renderCatalogSlides(pptx, sub, theme);
            }
        }
    }

    private void renderSectionSlide(XMLSlideShow pptx, ReportSection section, String parentTitle, ThemeTokens theme) {
        XSLFSlide slide = pptx.createSlide();

        String sectionTitle = section.title != null ? section.title : "";
        addTextBox(slide, sectionTitle, 40, 15, 880, 35, theme.fontPrimary(), theme.heading2SizePt(), true, theme.primary(), false);

        addHeaderLine(slide, parentTitle, theme);

        int yOffset = 60;

        if (section.components != null) {
            for (ReportComponent component : section.components) {
                yOffset = renderComponent(slide, component, yOffset, theme);
            }
        }

        if (section.summary != null && section.summary.overview != null && !section.summary.overview.isBlank()) {
            addTextBox(slide, section.summary.overview, 40, yOffset + 10, 880, 60, theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary(), false);
        }
    }

    private int renderComponent(XSLFSlide slide, ReportComponent component, int yOffset, ThemeTokens theme) {
        switch (component) {
            case TextComponent text -> {
                if (text.dataProperties != null) {
                    String content = str(text.dataProperties.content);
                    if (!content.isEmpty()) {
                        yOffset = addTextBox(slide, content, 40, yOffset, 880, 380, theme.fontPrimary(), theme.bodySizePt(), false, null, false);
                    }
                }
            }
            case MarkdownComponent md -> {
                if (md.dataProperties != null) {
                    String content = str(md.dataProperties.content);
                    if (!content.isEmpty()) {
                        yOffset = addTextBox(slide, content, 40, yOffset, 880, 380, theme.fontPrimary(), theme.bodySizePt(), false, null, false);
                    }
                }
            }
            case TableComponent table -> {
                yOffset = PptxTableRenderer.renderTable(slide, table.dataProperties, 40, yOffset, 880, theme);
            }
            case ChartComponent chart -> {
                yOffset = PptxChartRenderer.renderChart(slide, chart.dataProperties, 40, yOffset, 880, 300, theme);
            }
            case CompositeTableComponent composite -> {
                if (composite.tables != null) {
                    for (TableComponent subTable : composite.tables) {
                        yOffset = PptxTableRenderer.renderTable(slide, subTable.dataProperties, 40, yOffset, 880, theme);
                    }
                }
            }
            default -> { }
        }
        return yOffset;
    }

    private void renderPagedContent(XMLSlideShow pptx, ReportDslModel dsl, ThemeTokens theme) {
        if (dsl.content == null) return;
        for (ReportPagedContentItem item : dsl.content) {
            if (item instanceof ReportSlideSection section) {
                if (section.slides != null) {
                    for (ReportSlide slideData : section.slides) {
                        renderPagedSlide(pptx, slideData, theme);
                    }
                }
            } else if (item instanceof ReportSlide slideData) {
                renderPagedSlide(pptx, slideData, theme);
            }
        }
    }

    private void renderPagedSlide(XMLSlideShow pptx, ReportSlide slideData, ThemeTokens theme) {
        XSLFSlide slide = pptx.createSlide();
        String title = str(slideData.title);
        if (!title.isEmpty()) {
            addTextBox(slide, title, 40, 15, 880, 35, theme.fontPrimary(), theme.heading2SizePt(), true, theme.primary(), false);
        }

        int yOffset = 60;
        if (slideData.components != null) {
            for (ReportComponent component : slideData.components) {
                yOffset = renderComponent(slide, component, yOffset, theme);
            }
        }
    }

    private void renderSummarySlide(XMLSlideShow pptx, ReportSummary summary, ThemeTokens theme) {
        XSLFSlide slide = pptx.createSlide();
        addTextBox(slide, "报告摘要", 40, 20, 880, 40, theme.fontPrimary(), theme.heading1SizePt(), true, theme.primary(), false);
        addTextBox(slide, summary.overview, 50, 80, 860, 380, theme.fontPrimary(), theme.bodySizePt(), false, null, false);
    }

    private void renderBackCoverSlide(XMLSlideShow pptx, BackCoverConfig backCover, ThemeTokens theme) {
        XSLFSlide slide = pptx.createSlide();
        String text = backCover.text != null ? backCover.text : "谢谢";
        addTextBox(slide, text, 50, 200, 860, 80, theme.fontPrimary(), theme.titleSizePt(), true, theme.primary(), true);
    }

    static int addTextBox(XSLFSlide slide, String text, int x, int y, int w, int h,
                          String fontFamily, int fontSize, boolean bold, String color, boolean centered) {
        XSLFTextBox textBox = slide.createTextBox();
        textBox.setAnchor(new java.awt.Rectangle(x, y, w, h));
        textBox.clearText();

        XSLFTextParagraph paragraph = textBox.addNewTextParagraph();
        if (centered) {
            paragraph.setTextAlign(org.apache.poi.sl.usermodel.TextAlign.CENTER);
        }

        String[] lines = text.split("\n");
        for (int i = 0; i < lines.length; i++) {
            if (i > 0) {
                paragraph = textBox.addNewTextParagraph();
                if (centered) {
                    paragraph.setTextAlign(org.apache.poi.sl.usermodel.TextAlign.CENTER);
                }
            }
            XSLFTextRun run = paragraph.addNewTextRun();
            run.setText(lines[i]);
            run.setFontFamily(fontFamily);
            run.setFontSize((double) fontSize);
            run.setBold(bold);
            if (color != null) {
                run.setFontColor(hexToColor(color));
            }
        }

        return y + h;
    }

    private static void addHeaderLine(XSLFSlide slide, String text, ThemeTokens theme) {
        XSLFTextBox tb = slide.createTextBox();
        tb.setAnchor(new java.awt.Rectangle(40, 0, 880, 14));
        tb.clearText();
        XSLFTextParagraph p = tb.addNewTextParagraph();
        XSLFTextRun run = p.addNewTextRun();
        run.setText(text);
        run.setFontFamily(theme.fontSecondary());
        run.setFontSize(8.0);
        run.setFontColor(hexToColor(theme.secondary()));
    }

    static Color hexToColor(String hex) {
        if (hex == null) return Color.BLACK;
        String clean = hex.replace("#", "").trim();
        if (clean.length() != 6) return Color.BLACK;
        return new Color(
                Integer.parseInt(clean.substring(0, 2), 16),
                Integer.parseInt(clean.substring(2, 4), 16),
                Integer.parseInt(clean.substring(4, 6), 16)
        );
    }

    private static String str(Object val) {
        return val == null ? "" : val.toString().trim();
    }
}
