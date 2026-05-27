package com.bi.report.generation.pptx;

import org.apache.poi.xslf.usermodel.*;
import org.apache.poi.xddf.usermodel.chart.*;
import com.bi.report.generation.chart.ChartAxisNormalizer;
import com.bi.report.generation.chart.ChartWorkbookBinder;
import com.bi.report.generation.chart.ChartSeriesStyler;
import com.bi.report.generation.chart.ChartSpec;
import com.bi.report.generation.chart.ChartSpecParser;
import com.bi.report.generation.model.ChartDataProperties;
import com.bi.report.generation.model.TableDataProperties;
import com.bi.report.generation.style.ThemeTokens;

import java.awt.geom.Rectangle2D;

public final class PptxChartRenderer {
    private static final int EMU_PER_POINT = 12700;

    private PptxChartRenderer() {}

    public static int renderChart(XSLFSlide slide, ChartDataProperties dataProps, int x, int y, int width, int height, ThemeTokens theme) {
        if (dataProps == null) return y;

        String title = str(dataProps.title);
        ChartSpec spec = ChartSpecParser.parse(dataProps);

        int yOffset = y;
        if (!title.isEmpty()) {
            ReportPptxExporter.addTextBox(slide, title, x, yOffset, width, 25, theme.fontPrimary(), theme.bodySizePt(), true, theme.primary(), false);
            yOffset += 28;
        }

        ChartSpec.NativeType nativeType = spec.resolveNativeType();

        if (nativeType == ChartSpec.NativeType.FALLBACK_TABLE) {
            String chartType = spec.chartType() != null ? spec.chartType() : "unknown";
            String info = "[图表: " + chartType + " - " + spec.categories().size() + " 类别, " + spec.seriesList().size() + " 系列]";
            ReportPptxExporter.addTextBox(slide, info, x, yOffset, width, 20, theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary(), false);
            yOffset += 25;
            yOffset = PptxTableRenderer.renderTable(slide, toTableDataProperties(dataProps), x, yOffset, width, theme);
            return yOffset;
        }

        try {
            XMLSlideShow pptx = slide.getSlideShow();
            renderNativeChart(pptx, slide, spec, nativeType, x, yOffset, width, height, theme);
            return yOffset + height + 10;
        } catch (Exception e) {
            String errMsg = "[图表渲染失败: " + e.getMessage() + "]";
            ReportPptxExporter.addTextBox(slide, errMsg, x, yOffset, width, 20, theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary(), false);
            yOffset += 25;
            yOffset = PptxTableRenderer.renderTable(slide, toTableDataProperties(dataProps), x, yOffset, width, theme);
            return yOffset;
        }
    }

    private static void renderNativeChart(XMLSlideShow pptx, XSLFSlide slide, ChartSpec spec, ChartSpec.NativeType nativeType,
                                          int x, int y, int width, int height, ThemeTokens theme) throws Exception {
        XSLFChart chart = pptx.createChart();
        slide.addChart(chart, new Rectangle2D.Double(
                (double) x * EMU_PER_POINT,
                (double) y * EMU_PER_POINT,
                (double) width * EMU_PER_POINT,
                (double) height * EMU_PER_POINT
        ));
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
            }
            default -> {
                // fallback already handled above
            }
        }
    }

    private static void styleSeries(XDDFChartData chartData, boolean lineChart) {
        for (int i = 0; i < chartData.getSeriesCount(); i++) {
            ChartSeriesStyler.apply(chartData.getSeries(i), i, lineChart);
        }
    }

    private static TableDataProperties toTableDataProperties(ChartDataProperties chartProps) {
        if (chartProps == null) return null;
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
