package report.system.exporter.docx;

import org.apache.poi.xwpf.usermodel.*;
import org.apache.poi.xddf.usermodel.chart.*;
import report.system.exporter.chart.ChartSpec;
import report.system.exporter.chart.ChartSpecParser;
import report.system.exporter.model.ChartDataProperties;
import report.system.exporter.model.TableDataProperties;
import report.system.exporter.model.ReportColumn;
import report.system.exporter.style.ThemeTokens;

import java.util.*;

public final class DocxChartRenderer {

    private DocxChartRenderer() {}

    public static void renderChart(XWPFDocument doc, ChartDataProperties dataProps, ThemeTokens theme) {
        if (dataProps == null) return;

        String title = str(dataProps.title);
        ChartSpec spec = ChartSpecParser.parse(dataProps);

        if (!title.isEmpty()) {
            ReportDocxExporter.addParagraph(doc, title, theme.fontPrimary(), theme.bodySizePt(), true, theme.primary());
        }

        ChartSpec.NativeType nativeType = spec.resolveNativeType();

        if (nativeType == ChartSpec.NativeType.FALLBACK_TABLE) {
            renderFallback(doc, spec, dataProps, theme);
            return;
        }

        try {
            renderNativeChart(doc, spec, nativeType, theme);
        } catch (Exception e) {
            renderFallback(doc, spec, dataProps, theme);
        }
    }

    private static void renderNativeChart(XWPFDocument doc, ChartSpec spec, ChartSpec.NativeType nativeType, ThemeTokens theme) throws Exception {
        XWPFChart chart = doc.createChart();
        chart.setTitleText(spec.title() != null ? spec.title() : "");

        XDDFDataSource<String> categories = XDDFDataSources.fromStringArray(
                spec.categories().toArray(new String[0])
        );

        XDDFChartData chartData;
        switch (nativeType) {
            case LINE -> {
                chartData = chart.createData(ChartTypes.LINE, null, null);
                for (ChartSpec.Series s : spec.seriesList()) {
                    XDDFNumericalDataSource<Double> values = XDDFDataSources.fromDoubleArray(
                            s.values().toArray(new Double[0])
                    );
                    chartData.addSeries(categories, values);
                }
                chart.plot(chartData);
            }
            case BAR -> {
                chartData = chart.createData(ChartTypes.BAR, null, null);
                ((XDDFBarChartData) chartData).setBarDirection(BarDirection.COL);
                for (ChartSpec.Series s : spec.seriesList()) {
                    XDDFNumericalDataSource<Double> values = XDDFDataSources.fromDoubleArray(
                            s.values().toArray(new Double[0])
                    );
                    chartData.addSeries(categories, values);
                }
                chart.plot(chartData);
            }
            case PIE -> {
                chartData = chart.createData(ChartTypes.PIE, null, null);
                if (!spec.seriesList().isEmpty()) {
                    ChartSpec.Series first = spec.seriesList().get(0);
                    XDDFNumericalDataSource<Double> values = XDDFDataSources.fromDoubleArray(
                            first.values().toArray(new Double[0])
                    );
                    chartData.addSeries(categories, values);
                }
                chart.plot(chartData);
            }
            default -> {
                return;
            }
        }
    }

    private static void renderFallback(XWPFDocument doc, ChartSpec spec, ChartDataProperties dataProps, ThemeTokens theme) {
        String chartType = spec.chartType() != null ? spec.chartType() : "unknown";
        ReportDocxExporter.addParagraph(doc,
                "[图表: " + chartType + " - " + spec.categories().size() + " 类别, " + spec.seriesList().size() + " 系列]",
                theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary());

        TableDataProperties tableProps = toTableDataProperties(dataProps);
        if (tableProps != null) {
            DocxTableRenderer.renderTable(doc, tableProps, theme);
        }
    }

    private static TableDataProperties toTableDataProperties(ChartDataProperties chartProps) {
        if (chartProps == null || (chartProps.columns == null && chartProps.data == null)) return null;
        TableDataProperties tableProps = new TableDataProperties();
        tableProps.dataType = chartProps.dataType;
        tableProps.title = chartProps.title;
        tableProps.columns = chartProps.columns;
        tableProps.data = chartProps.data;
        return tableProps;
    }

    private static String str(Object val) {
        return val == null ? "" : val.toString().trim();
    }
}
