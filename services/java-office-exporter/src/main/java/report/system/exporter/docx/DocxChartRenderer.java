package report.system.exporter.docx;

import org.apache.poi.xwpf.usermodel.*;
import org.apache.poi.xddf.usermodel.chart.*;
import report.system.exporter.chart.ChartSpec;
import report.system.exporter.chart.ChartSpecParser;
import report.system.exporter.model.ChartDataProperties;
import report.system.exporter.model.TableDataProperties;
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

        XDDFChartLegend legend = chart.getOrAddLegend();
        legend.setPosition(LegendPosition.BOTTOM);

        String[] categoryArray = spec.categories().toArray(new String[0]);
        XDDFDataSource<String> categories = XDDFDataSourcesFactory.fromArray(categoryArray);

        XDDFChartData chartData;
        switch (nativeType) {
            case LINE -> {
                XDDFCategoryAxis catAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
                XDDFValueAxis valAxis = chart.createValueAxis(AxisPosition.LEFT);
                chartData = chart.createData(ChartTypes.LINE, catAxis, valAxis);
                ((XDDFLineChartData) chartData).setGrouping(Grouping.STANDARD);
                for (ChartSpec.Series s : spec.seriesList()) {
                    Double[] valueArray = s.values().toArray(new Double[0]);
                    XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(valueArray);
                    XDDFChartData.Series series = chartData.addSeries(categories, values);
                    series.setTitle(s.name(), null);
                }
                chart.plot(chartData);
            }
            case BAR -> {
                XDDFCategoryAxis catAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
                XDDFValueAxis valAxis = chart.createValueAxis(AxisPosition.LEFT);
                chartData = chart.createData(ChartTypes.BAR, catAxis, valAxis);
                ((XDDFBarChartData) chartData).setBarDirection(BarDirection.COL);
                for (ChartSpec.Series s : spec.seriesList()) {
                    Double[] valueArray = s.values().toArray(new Double[0]);
                    XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(valueArray);
                    XDDFChartData.Series series = chartData.addSeries(categories, values);
                    series.setTitle(s.name(), null);
                }
                chart.plot(chartData);
            }
            case PIE -> {
                chartData = chart.createData(ChartTypes.PIE, null, null);
                if (!spec.seriesList().isEmpty()) {
                    ChartSpec.Series first = spec.seriesList().get(0);
                    Double[] valueArray = first.values().toArray(new Double[0]);
                    XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(valueArray);
                    XDDFChartData.Series series = chartData.addSeries(categories, values);
                    series.setTitle(first.name(), null);
                }
                chart.plot(chartData);
            }
            default -> {
                renderFallback(doc, spec, null, theme);
            }
        }
    }

    private static void renderFallback(XWPFDocument doc, ChartSpec spec, ChartDataProperties dataProps, ThemeTokens theme) {
        String chartType = spec.chartType() != null ? spec.chartType() : "unknown";
        ReportDocxExporter.addParagraph(doc,
                "[图表: " + chartType + " - " + spec.categories().size() + " 类别, " + spec.seriesList().size() + " 系列]",
                theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary());

        if (dataProps != null) {
            TableDataProperties tableProps = toTableDataProperties(dataProps);
            if (tableProps != null) {
                DocxTableRenderer.renderTable(doc, tableProps, theme);
            }
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
