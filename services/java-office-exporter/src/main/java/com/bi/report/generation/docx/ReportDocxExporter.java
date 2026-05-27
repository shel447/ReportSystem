package com.bi.report.generation.docx;

import org.apache.poi.xwpf.usermodel.*;
import org.apache.poi.wp.usermodel.HeaderFooterType;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.*;
import com.bi.report.generation.core.DocumentExporter;
import com.bi.report.generation.core.ExportRequest;
import com.bi.report.generation.core.ExportTarget;
import com.bi.report.generation.model.*;
import com.bi.report.generation.style.StyleResolver;
import com.bi.report.generation.style.ThemeTokens;

import java.io.FileOutputStream;
import java.io.IOException;
import java.math.BigInteger;
import java.nio.file.Path;
import java.util.List;

public final class ReportDocxExporter implements DocumentExporter {

    @Override
    public ExportTarget target() {
        return ExportTarget.DOCX;
    }

    @Override
    public boolean supports(ReportDslModel dsl) {
        return true;
    }

    @Override
    public void export(ReportDslModel dsl, Path output, ExportRequest request) throws IOException {
        StyleResolver style = new StyleResolver(request.theme());
        ThemeTokens theme = style.tokens();

        try (XWPFDocument doc = new XWPFDocument()) {
            setupPageMargins(doc);

            if (dsl.cover != null) {
                DocxCoverRenderer.renderCover(doc, dsl.cover, dsl.basicInfo, theme);
                addPageBreak(doc);
            }

            renderTableOfContents(doc, dsl, theme);
            addPageBreak(doc);

            List<ReportCatalog> catalogs = dsl.catalogs != null ? dsl.catalogs : List.of();
            for (ReportCatalog catalog : catalogs) {
                renderCatalog(doc, catalog, 1, theme);
            }

            if (dsl.summary != null && dsl.summary.overview != null && !dsl.summary.overview.isBlank()) {
                addPageBreak(doc);
                addHeading(doc, "报告摘要", 1, theme);
                addParagraph(doc, dsl.summary.overview, theme.fontPrimary(), theme.bodySizePt(), false, null);
            }

            if (dsl.signaturePage != null) {
                addPageBreak(doc);
                DocxCoverRenderer.renderSignaturePage(doc, dsl.signaturePage, theme);
            }

            setupHeaderFooter(doc, dsl.basicInfo);

            try (FileOutputStream fos = new FileOutputStream(output.toFile())) {
                doc.write(fos);
            }
        }
    }

    private void renderCatalog(XWPFDocument doc, ReportCatalog catalog, int depth, ThemeTokens theme) {
        String title = catalog.resolvedTitle();
        int headingLevel = Math.min(depth, 3);
        addHeading(doc, title, headingLevel, theme);

        if (catalog.sections != null) {
            for (ReportSection section : catalog.sections) {
                renderSection(doc, section, depth + 1, theme);
            }
        }

        if (catalog.subCatalogs != null) {
            for (ReportCatalog sub : catalog.subCatalogs) {
                renderCatalog(doc, sub, depth + 1, theme);
            }
        }
    }

    private void renderSection(XWPFDocument doc, ReportSection section, int depth, ThemeTokens theme) {
        if (section.title != null && !section.title.isBlank()) {
            int headingLevel = Math.min(depth + 1, 3);
            addHeading(doc, section.title, headingLevel, theme);
        }

        if (section.summary != null && section.summary.overview != null && !section.summary.overview.isBlank()) {
            XWPFParagraph p = doc.createParagraph();
            XWPFRun run = p.createRun();
            run.setText(section.summary.overview);
            run.setFontFamily(theme.fontPrimary());
            run.setFontSize(theme.smallSizePt());
            run.setItalic(true);
            run.setColor(theme.secondary());
        }

        if (section.components != null) {
            for (ReportComponent component : section.components) {
                renderComponent(doc, component, theme);
            }
        }
    }

    private void renderComponent(XWPFDocument doc, ReportComponent component, ThemeTokens theme) {
        switch (component) {
            case TextComponent text -> DocxTextRenderer.renderText(doc, text.dataProperties, theme);
            case MarkdownComponent md -> DocxTextRenderer.renderMarkdown(doc, md.dataProperties, theme);
            case TableComponent table -> DocxTableRenderer.renderTable(doc, table.dataProperties, theme);
            case ChartComponent chart -> DocxChartRenderer.renderChart(doc, chart.dataProperties, theme);
            case CompositeTableComponent composite -> {
                if (composite.tables != null) {
                    for (TableComponent subTable : composite.tables) {
                        DocxTableRenderer.renderTable(doc, subTable.dataProperties, theme);
                    }
                }
            }
            default -> { }
        }
    }

    private void renderTableOfContents(XWPFDocument doc, ReportDslModel dsl, ThemeTokens theme) {
        addHeading(doc, "目录", 1, theme);
        List<ReportCatalog> catalogs = dsl.catalogs != null ? dsl.catalogs : List.of();
        renderTocEntries(doc, catalogs, 0, theme);
    }

    private void renderTocEntries(XWPFDocument doc, List<ReportCatalog> catalogs, int indent, ThemeTokens theme) {
        if (catalogs == null) return;
        for (ReportCatalog catalog : catalogs) {
            String prefix = "    ".repeat(indent);
            String text = prefix + catalog.resolvedTitle();
            addParagraph(doc, text, theme.fontPrimary(), theme.bodySizePt(), false, null);

            if (catalog.sections != null) {
                for (ReportSection section : catalog.sections) {
                    if (section.title != null && !section.title.isBlank()) {
                        String secText = "    ".repeat(indent + 1) + section.title;
                        addParagraph(doc, secText, theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary());
                    }
                }
            }
            renderTocEntries(doc, catalog.subCatalogs, indent + 1, theme);
        }
    }

    static void addHeading(XWPFDocument doc, String text, int level, ThemeTokens theme) {
        XWPFParagraph p = doc.createParagraph();
        p.setStyle("Heading" + level);
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setFontFamily(theme.fontPrimary());
        run.setBold(true);
        int size = switch (level) {
            case 1 -> theme.heading1SizePt();
            case 2 -> theme.heading2SizePt();
            default -> theme.heading3SizePt();
        };
        run.setFontSize(size);
        run.setColor(theme.primary());
        p.setSpacingAfter(120);
        p.setSpacingBefore(240);
    }

    static void addParagraph(XWPFDocument doc, String text, String fontFamily, int fontSize, boolean bold, String color) {
        if (text == null || text.isEmpty()) return;
        String[] lines = text.split("\n");
        for (String line : lines) {
            XWPFParagraph p = doc.createParagraph();
            XWPFRun run = p.createRun();
            run.setText(line);
            run.setFontFamily(fontFamily);
            run.setFontSize(fontSize);
            run.setBold(bold);
            if (color != null) run.setColor(color);
            p.setSpacingAfter(60);
        }
    }

    static void addPageBreak(XWPFDocument doc) {
        XWPFParagraph p = doc.createParagraph();
        XWPFRun run = p.createRun();
        run.addBreak(BreakType.PAGE);
    }

    private void setupPageMargins(XWPFDocument doc) {
        CTDocument1 document = doc.getDocument();
        CTBody body = document.getBody();
        if (body == null) {
            body = document.addNewBody();
        }
        CTSectPr sectPr = body.isSetSectPr() ? body.getSectPr() : body.addNewSectPr();
        CTPageMar pageMar = sectPr.isSetPgMar() ? sectPr.getPgMar() : sectPr.addNewPgMar();
        long marginTwips = 794;
        pageMar.setTop(BigInteger.valueOf(marginTwips));
        pageMar.setBottom(BigInteger.valueOf(marginTwips));
        pageMar.setLeft(BigInteger.valueOf(marginTwips));
        pageMar.setRight(BigInteger.valueOf(marginTwips));
    }

    private void setupHeaderFooter(XWPFDocument doc, ReportBasicInfo basicInfo) {
        if (basicInfo == null) return;
        String headerText = basicInfo.header;
        String footerText = basicInfo.footer;

        if (headerText != null && !headerText.isBlank()) {
            XWPFHeader header = doc.createHeader(HeaderFooterType.DEFAULT);
            XWPFParagraph p = header.createParagraph();
            p.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun run = p.createRun();
            run.setText(headerText);
            run.setFontSize(9);
            run.setColor("999999");
        }

        if (footerText != null && !footerText.isBlank()) {
            XWPFFooter footer = doc.createFooter(HeaderFooterType.DEFAULT);
            XWPFParagraph p = footer.createParagraph();
            p.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun run = p.createRun();
            run.setText(footerText);
            run.setFontSize(9);
            run.setColor("999999");
        }
    }
}
