package report.system.exporter.docx;

import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import report.system.exporter.model.MarkdownDataProperties;
import report.system.exporter.model.TextDataProperties;
import report.system.exporter.style.ThemeTokens;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class DocxTextRenderer {
    private static final Pattern BOLD_PATTERN = Pattern.compile("\\*\\*(.+?)\\*\\*");
    private static final Pattern ITALIC_PATTERN = Pattern.compile("\\*(.+?)\\*");

    private DocxTextRenderer() {}

    public static void renderText(XWPFDocument doc, TextDataProperties dataProps, ThemeTokens theme) {
        if (dataProps == null) return;
        String content = str(dataProps.content);
        String title = str(dataProps.title);

        if (!title.isEmpty()) {
            ReportDocxExporter.addParagraph(doc, title, theme.fontPrimary(), theme.bodySizePt(), true, theme.primary());
        }

        if (!content.isEmpty()) {
            ReportDocxExporter.addParagraph(doc, content, theme.fontPrimary(), theme.bodySizePt(), false, null);
        }
    }

    public static void renderMarkdown(XWPFDocument doc, MarkdownDataProperties dataProps, ThemeTokens theme) {
        if (dataProps == null) return;
        String content = str(dataProps.content);
        if (content.isEmpty()) return;

        String[] lines = content.split("\n");
        for (String line : lines) {
            String trimmed = line.trim();
            if (trimmed.isEmpty()) continue;

            if (trimmed.startsWith("# ")) {
                ReportDocxExporter.addHeading(doc, trimmed.substring(2), 1, theme);
            } else if (trimmed.startsWith("## ")) {
                ReportDocxExporter.addHeading(doc, trimmed.substring(3), 2, theme);
            } else if (trimmed.startsWith("### ")) {
                ReportDocxExporter.addHeading(doc, trimmed.substring(4), 3, theme);
            } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
                renderListItem(doc, trimmed.substring(2), theme);
            } else {
                renderRichLine(doc, trimmed, theme);
            }
        }
    }

    private static void renderListItem(XWPFDocument doc, String text, ThemeTokens theme) {
        XWPFParagraph p = doc.createParagraph();
        p.setIndentationLeft(480);
        XWPFRun bullet = p.createRun();
        bullet.setText("\u2022 ");
        bullet.setFontFamily(theme.fontPrimary());
        bullet.setFontSize(theme.bodySizePt());
        appendRichText(p, text, theme);
        p.setSpacingAfter(40);
    }

    private static void renderRichLine(XWPFDocument doc, String line, ThemeTokens theme) {
        XWPFParagraph p = doc.createParagraph();
        appendRichText(p, line, theme);
        p.setSpacingAfter(60);
    }

    private static void appendRichText(XWPFParagraph p, String text, ThemeTokens theme) {
        String remaining = text;

        Matcher boldMatcher = BOLD_PATTERN.matcher(remaining);
        if (boldMatcher.find()) {
            int lastEnd = 0;
            boldMatcher.reset();
            while (boldMatcher.find()) {
                if (boldMatcher.start() > lastEnd) {
                    addRun(p, remaining.substring(lastEnd, boldMatcher.start()), theme, false, false);
                }
                addRun(p, boldMatcher.group(1), theme, true, false);
                lastEnd = boldMatcher.end();
            }
            if (lastEnd < remaining.length()) {
                addRun(p, remaining.substring(lastEnd), theme, false, false);
            }
            return;
        }

        Matcher italicMatcher = ITALIC_PATTERN.matcher(remaining);
        if (italicMatcher.find()) {
            int lastEnd = 0;
            italicMatcher.reset();
            while (italicMatcher.find()) {
                if (italicMatcher.start() > lastEnd) {
                    addRun(p, remaining.substring(lastEnd, italicMatcher.start()), theme, false, false);
                }
                addRun(p, italicMatcher.group(1), theme, false, true);
                lastEnd = italicMatcher.end();
            }
            if (lastEnd < remaining.length()) {
                addRun(p, remaining.substring(lastEnd), theme, false, false);
            }
            return;
        }

        addRun(p, text, theme, false, false);
    }

    private static void addRun(XWPFParagraph p, String text, ThemeTokens theme, boolean bold, boolean italic) {
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(theme.bodySizePt());
        run.setBold(bold);
        run.setItalic(italic);
    }

    private static String str(Object val) {
        return val == null ? "" : val.toString();
    }
}
