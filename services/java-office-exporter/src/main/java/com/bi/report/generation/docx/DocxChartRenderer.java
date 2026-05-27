package com.bi.report.generation.docx;

import org.apache.poi.xwpf.usermodel.*;
import org.apache.poi.xddf.usermodel.chart.*;
import org.apache.poi.util.Units;
import com.bi.report.generation.chart.ChartAxisNormalizer;
import com.bi.report.generation.chart.ChartWorkbookBinder;
import com.bi.report.generation.chart.ChartSeriesStyler;
import com.bi.report.generation.chart.ChartSpec;
import com.bi.report.generation.chart.ChartSpecParser;
import com.bi.report.generation.model.ChartDataProperties;
import com.bi.report.generation.model.TableDataProperties;
import com.bi.report.generation.style.ThemeTokens;

import java.util.*;

public final class DocxChartRenderer {
    private static final int CHART_WIDTH_EMU = Units.toEMU(6.4 * 72.0);
    private static final int CHART_HEIGHT_EMU = Units.toEMU(3.6 * 72.0);

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
        XWPFChart chart = doc.createChart(CHART_WIDTH_EMU, CHART_HEIGHT_EMU);
        chart.setTitleText(spec.title() != null ? spec.title() : "");

        XDDFChartLegend legend = chart.getOrAddLegend();
        legend.setPosition(LegendPosition.BOTTOM);

        ChartWorkbookBinder.BoundChartData boundData = ChartWorkbookBinder.bind(
                chart, spec, nativeType == ChartSpec.NativeType.PIE
        );
        XDDFDataSource<String> categories = boundData.categories();

        XDDFChartData chartData;
        switch (nativeType) {
            case LINE -> {
                XDDFCategoryAxis catAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
                XDDFValueAxis valAxis = chart.createValueAxis(AxisPosition.LEFT);
                chartData = chart.createData(ChartTypes.LINE, catAxis, valAxis);
                ((XDDFLineChartData) chartData).setGrouping(Grouping.STANDARD);
                for (ChartWorkbookBinder.BoundSeries s : boundData.seriesList()) {
                    XDDFChartData.Series series = chartData.addSeries(categories, s.values());
                    series.setTitle(s.name(), null);
                }
                chart.plot(chartData);
                styleSeries(chartData, true);
                ChartAxisNormalizer.normalizeCategoryValueAxes(chart);
                chart.saveWorkbook(boundData.workbook());
                DocxChartCompat.normalize(doc, chart);
            }
            case BAR -> {
                XDDFCategoryAxis catAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
                XDDFValueAxis valAxis = chart.createValueAxis(AxisPosition.LEFT);
                chartData = chart.createData(ChartTypes.BAR, catAxis, valAxis);
                ((XDDFBarChartData) chartData).setBarDirection(BarDirection.COL);
                for (ChartWorkbookBinder.BoundSeries s : boundData.seriesList()) {
                    XDDFChartData.Series series = chartData.addSeries(categories, s.values());
                    series.setTitle(s.name(), null);
                }
                chart.plot(chartData);
                styleSeries(chartData, false);
                ChartAxisNormalizer.normalizeCategoryValueAxes(chart);
                chart.saveWorkbook(boundData.workbook());
                DocxChartCompat.normalize(doc, chart);
            }
            case PIE -> {
                chartData = chart.createData(ChartTypes.PIE, null, null);
                if (!boundData.seriesList().isEmpty()) {
                    ChartWorkbookBinder.BoundSeries first = boundData.seriesList().get(0);
                    XDDFChartData.Series series = chartData.addSeries(categories, first.values());
                    series.setTitle(first.name(), null);
                }
                chart.plot(chartData);
                styleSeries(chartData, false);
                chart.saveWorkbook(boundData.workbook());
                DocxChartCompat.normalize(doc, chart);
            }
            default -> {
                renderFallback(doc, spec, null, theme);
            }
        }
    }

    private static void styleSeries(XDDFChartData chartData, boolean lineChart) {
        for (int i = 0; i < chartData.getSeriesCount(); i++) {
            ChartSeriesStyler.apply(chartData.getSeries(i), i, lineChart);
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
