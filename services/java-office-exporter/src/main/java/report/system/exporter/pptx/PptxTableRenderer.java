package report.system.exporter.pptx;

import org.apache.poi.xslf.usermodel.*;
import report.system.exporter.model.ReportColumn;
import report.system.exporter.model.TableDataProperties;
import report.system.exporter.style.ThemeTokens;

import java.awt.*;
import java.util.*;
import java.util.List;

public final class PptxTableRenderer {

    private PptxTableRenderer() {}

    public static int renderTable(XSLFSlide slide, TableDataProperties dataProps, int x, int y, int width, ThemeTokens theme) {
        if (dataProps == null) return y;

        String title = str(dataProps.title);
        List<ReportColumn> columns = dataProps.columns != null ? dataProps.columns : List.of();
        List<Map<String, Object>> data = dataProps.data != null ? dataProps.data : List.of();

        if (columns.isEmpty() && !data.isEmpty()) {
            columns = inferColumns(data.get(0));
        }

        if (columns.isEmpty()) return y;

        int yOffset = y;
        if (!title.isEmpty()) {
            ReportPptxExporter.addTextBox(slide, title, x, yOffset, width, 25, theme.fontPrimary(), theme.bodySizePt(), true, theme.primary(), false);
            yOffset += 28;
        }

        int colCount = columns.size();
        int rowCount = Math.min(data.size() + 1, 20);

        int tableHeight = Math.min(rowCount * 22, 350);

        XSLFTable table = slide.createTable(rowCount, colCount);
        table.setAnchor(new Rectangle(x, yOffset, width, tableHeight));

        for (int c = 0; c < colCount; c++) {
            ReportColumn col = columns.get(c);
            String colTitle = str(col.title);
            if (colTitle.isEmpty()) colTitle = str(col.key);
            XSLFTableCell cell = table.getCell(0, c);
            cell.setText(colTitle);
            cell.setFillColor(ReportPptxExporter.hexToColor(theme.tableHeaderBg()));
            for (XSLFTextParagraph p : cell.getTextParagraphs()) {
                p.setTextAlign(org.apache.poi.sl.usermodel.TextParagraph.TextAlign.CENTER);
                for (XSLFTextRun r : p.getTextRuns()) {
                    r.setFontFamily(theme.fontPrimary());
                    r.setFontSize((double) theme.tableHeaderSizePt());
                    r.setBold(true);
                    r.setFontColor(Color.WHITE);
                }
            }
        }

        for (int r = 1; r < rowCount; r++) {
            Map<String, Object> rowData = data.get(r - 1);
            for (int c = 0; c < colCount; c++) {
                String key = str(columns.get(c).key);
                Object val = rowData.get(key);
                String cellText = val == null ? "" : val.toString();
                XSLFTableCell cell = table.getCell(r, c);
                cell.setText(cellText);
                if (r % 2 == 0) {
                    cell.setFillColor(ReportPptxExporter.hexToColor(theme.tableAltRowBg()));
                }
                for (XSLFTextParagraph p : cell.getTextParagraphs()) {
                    for (XSLFTextRun run : p.getTextRuns()) {
                        run.setFontFamily(theme.fontPrimary());
                        run.setFontSize((double) theme.smallSizePt());
                    }
                }
            }
        }

        return yOffset + tableHeight + 10;
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

    private static String str(Object val) {
        return val == null ? "" : val.toString().trim();
    }
}
