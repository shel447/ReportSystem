package report.system.exporter.chart;

import org.apache.poi.openxml4j.exceptions.InvalidFormatException;
import org.apache.poi.ss.util.CellRangeAddress;
import org.apache.poi.xddf.usermodel.chart.XDDFDataSource;
import org.apache.poi.xddf.usermodel.chart.XDDFDataSourcesFactory;
import org.apache.poi.xddf.usermodel.chart.XDDFNumericalDataSource;
import org.apache.poi.xddf.usermodel.chart.XDDFChart;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public final class ChartWorkbookBinder {

    private ChartWorkbookBinder() {}

    public static BoundChartData bind(XDDFChart chart, ChartSpec spec, boolean firstSeriesOnly)
            throws IOException, InvalidFormatException {
        XSSFWorkbook workbook = chart.getWorkbook();
        XSSFSheet sheet = workbook.getNumberOfSheets() == 0 ? workbook.createSheet("ChartData") : workbook.getSheetAt(0);
        clearSheet(sheet);
        workbook.setSheetName(workbook.getSheetIndex(sheet), "ChartData");

        XSSFRow header = row(sheet, 0);
        cell(header, 0).setCellValue("Category");
        for (int i = 0; i < spec.categories().size(); i++) {
            cell(row(sheet, i + 1), 0).setCellValue(spec.categories().get(i));
        }

        List<ChartSpec.Series> sourceSeries = firstSeriesOnly && !spec.seriesList().isEmpty()
                ? List.of(spec.seriesList().get(0))
                : spec.seriesList();

        List<BoundSeries> boundSeries = new ArrayList<>();
        for (int seriesIndex = 0; seriesIndex < sourceSeries.size(); seriesIndex++) {
            ChartSpec.Series series = sourceSeries.get(seriesIndex);
            int col = seriesIndex + 1;
            cell(header, col).setCellValue(series.name());
            for (int rowIndex = 0; rowIndex < spec.categories().size(); rowIndex++) {
                double value = rowIndex < series.values().size() ? series.values().get(rowIndex) : 0.0;
                cell(row(sheet, rowIndex + 1), col).setCellValue(value);
            }

            CellRangeAddress valueRange = new CellRangeAddress(1, spec.categories().size(), col, col);
            XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromNumericCellRange(sheet, valueRange);
            boundSeries.add(new BoundSeries(series.name(), values));
        }

        CellRangeAddress categoryRange = new CellRangeAddress(1, spec.categories().size(), 0, 0);
        XDDFDataSource<String> categories = XDDFDataSourcesFactory.fromStringCellRange(sheet, categoryRange);
        return new BoundChartData(workbook, categories, boundSeries);
    }

    private static void clearSheet(XSSFSheet sheet) {
        for (int i = sheet.getLastRowNum(); i >= 0; i--) {
            XSSFRow row = sheet.getRow(i);
            if (row != null) {
                sheet.removeRow(row);
            }
        }
    }

    private static XSSFRow row(XSSFSheet sheet, int index) {
        XSSFRow row = sheet.getRow(index);
        return row != null ? row : sheet.createRow(index);
    }

    private static XSSFCell cell(XSSFRow row, int index) {
        XSSFCell cell = row.getCell(index);
        return cell != null ? cell : row.createCell(index);
    }

    public record BoundChartData(
            XSSFWorkbook workbook,
            XDDFDataSource<String> categories,
            List<BoundSeries> seriesList
    ) {}

    public record BoundSeries(String name, XDDFNumericalDataSource<Double> values) {}
}
