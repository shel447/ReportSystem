package report.system.exporter.docx;

import org.apache.poi.xwpf.usermodel.*;
import report.system.exporter.model.ReportBasicInfo;
import report.system.exporter.model.ReportCover;
import report.system.exporter.model.ReportSignaturePage;
import report.system.exporter.style.ThemeTokens;

public final class DocxCoverRenderer {

    private DocxCoverRenderer() {}

    public static void renderCover(XWPFDocument doc, ReportCover cover, ReportBasicInfo basicInfo, ThemeTokens theme) {
        for (int i = 0; i < 6; i++) {
            doc.createParagraph();
        }

        String title = cover.title;
        if (title == null || title.isBlank()) {
            title = basicInfo != null ? basicInfo.title : null;
        }
        if (title != null && !title.isBlank()) {
            XWPFParagraph p = doc.createParagraph();
            p.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun run = p.createRun();
            run.setText(title);
            run.setFontFamily(theme.fontPrimary());
            run.setFontSize(theme.titleSizePt());
            run.setBold(true);
            run.setColor(theme.primary());
            p.setSpacingAfter(200);
        }

        if (basicInfo != null && basicInfo.subTitle != null && !basicInfo.subTitle.isBlank()) {
            XWPFParagraph p = doc.createParagraph();
            p.setAlignment(ParagraphAlignment.CENTER);
            XWPFRun run = p.createRun();
            run.setText(basicInfo.subTitle);
            run.setFontFamily(theme.fontPrimary());
            run.setFontSize(theme.heading2SizePt());
            run.setColor(theme.secondary());
            p.setSpacingAfter(400);
        }

        if (cover.author != null && !cover.author.isBlank()) {
            addCenteredLine(doc, cover.author, theme);
        }

        if (cover.date != null && !cover.date.isBlank()) {
            addCenteredLine(doc, cover.date, theme);
        }

        if (cover.contents != null) {
            for (ReportCover.ReportCoverContent item : cover.contents) {
                if (item.content != null && !item.content.isBlank()) {
                    addCenteredLine(doc, item.content, theme);
                }
            }
        }
    }

    public static void renderSignaturePage(XWPFDocument doc, ReportSignaturePage sigPage, ThemeTokens theme) {
        if (sigPage.title != null && !sigPage.title.isBlank()) {
            ReportDocxExporter.addHeading(doc, sigPage.title, 1, theme);
        } else {
            ReportDocxExporter.addHeading(doc, "签署页", 1, theme);
        }

        doc.createParagraph();

        if (sigPage.signers != null) {
            for (ReportSignaturePage.Signer signer : sigPage.signers) {
                StringBuilder sb = new StringBuilder();
                sb.append("签署人: ").append(signer.name != null ? signer.name : "");
                if (signer.role != null && !signer.role.isBlank()) {
                    sb.append("  (").append(signer.role).append(")");
                }
                if (signer.date != null && !signer.date.isBlank()) {
                    sb.append("  日期: ").append(signer.date);
                }
                ReportDocxExporter.addParagraph(doc, sb.toString(), theme.fontPrimary(), theme.bodySizePt(), false, null);
                doc.createParagraph();
            }
        }
    }

    private static void addCenteredLine(XWPFDocument doc, String text, ThemeTokens theme) {
        XWPFParagraph p = doc.createParagraph();
        p.setAlignment(ParagraphAlignment.CENTER);
        XWPFRun run = p.createRun();
        run.setText(text);
        run.setFontFamily(theme.fontPrimary());
        run.setFontSize(theme.bodySizePt());
        run.setColor(theme.secondary());
        p.setSpacingAfter(100);
    }
}
