package report.system.exporter.docx;

import org.apache.poi.xwpf.usermodel.*;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.*;
import report.system.exporter.model.ReportColumn;
import report.system.exporter.model.TableDataProperties;
import report.system.exporter.style.ThemeTokens;

import java.math.BigInteger;
import java.util.*;

public final class DocxTableRenderer {

    private DocxTableRenderer() {}

    public static void renderTable(XWPFDocument doc, TableDataProperties dataProps, ThemeTokens theme) {
        if (dataProps == null) return;

        String title = str(dataProps.title);
        if (!title.isEmpty()) {
            ReportDocxExporter.addParagraph(doc, title, theme.fontPrimary(), theme.bodySizePt(), true, theme.primary());
        }

        List<ReportColumn> columns = dataProps.columns != null ? dataProps.columns : List.of();
        List<Map<String, Object>> data = dataProps.data != null ? dataProps.data : List.of();

        if (columns.isEmpty() && !data.isEmpty()) {
            columns = inferColumns(data.get(0));
        }

        if (columns.isEmpty()) {
            ReportDocxExporter.addParagraph(doc, "(无表格数据)", theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary());
            return;
        }

        int colCount = columns.size();
        int rowCount = data.size() + 1;

        XWPFTable table = doc.createTable(rowCount, colCount);
        table.setWidth("100%");

        styleTableHeader(table, 0, theme);

        for (int c = 0; c < colCount; c++) {
            ReportColumn col = columns.get(c);
            String colTitle = str(col.title);
            if (colTitle.isEmpty()) colTitle = str(col.key);
            setCellText(table.getRow(0).getCell(c), colTitle, theme.fontPrimary(), theme.tableHeaderSizePt(), true, "FFFFFF");
        }

        for (int r = 0; r < data.size(); r++) {
            Map<String, Object> row = data.get(r);
            XWPFTableRow tableRow = table.getRow(r + 1);
            for (int c = 0; c < colCount; c++) {
                String key = str(columns.get(c).key);
                Object val = row.get(key);
                String cellText = val == null ? "" : val.toString();
                boolean isAltRow = r % 2 == 1;
                setCellText(tableRow.getCell(c), cellText, theme.fontPrimary(), theme.smallSizePt(), false, null);
                if (isAltRow) {
                    setCellBackground(tableRow.getCell(c), theme.tableAltRowBg());
                }
            }
        }
    }

    private static List<ReportColumn> inferColumns(Map<String, Object> firstRow) {
        List<ReportColumn> cols = new ArrayList<>();
        for (String key : firstRow.keySet()) {
            ReportColumn col = new ReportColumn();
            col.key = key;
            col.title = key;
            cols.add(col);
        }
        return cols;
    }

    private static void styleTableHeader(XWPFTable table, int rowIndex, ThemeTokens theme) {
        XWPFTableRow row = table.getRow(rowIndex);
        for (XWPFTableCell cell : row.getTableCells()) {
            setCellBackground(cell, theme.tableHeaderBg());
        }
    }

    private static void setCellText(XWPFTableCell cell, String text, String fontFamily, int fontSize, boolean bold, String fontColor) {
        if (cell.getParagraphs().isEmpty()) {
            cell.addNewParagraph();
        }
        XWPFParagraph p = cell.getParagraphs().get(0);
        p.setAlignment(ParagraphAlignment.LEFT);
        for (int i = p.getRuns().size() - 1; i >= 0; i--) {
            p.removeRun(i);
        }
        XWPFRun run = p.createRun();
        run.setText(text != null ? text : "");
        run.setFontFamily(fontFamily);
        run.setFontSize(fontSize);
        run.setBold(bold);
        if (fontColor != null) run.setColor(fontColor);
    }

    private static void setCellBackground(XWPFTableCell cell, String hexColor) {
        CTShd shd = cell.getCTTc().addNewTcPr().addNewShd();
        shd.setFill(hexColor);
        shd.setVal(STShd.CLEAR);
    }

    private static String str(Object val) {
        return val == null ? "" : val.toString().trim();
    }
}
