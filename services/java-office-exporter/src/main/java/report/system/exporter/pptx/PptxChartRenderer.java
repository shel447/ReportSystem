package report.system.exporter.pptx;

import org.apache.poi.xslf.usermodel.*;
import org.apache.poi.xddf.usermodel.chart.*;
import report.system.exporter.chart.ChartSpec;
import report.system.exporter.chart.ChartSpecParser;
import report.system.exporter.model.ChartDataProperties;
import report.system.exporter.model.TableDataProperties;
import report.system.exporter.style.ThemeTokens;

import java.awt.geom.Rectangle2D;

public final class PptxChartRenderer {

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
        XSLFChart chart = pptx.createChart(slide);
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
                // fallback already handled above
            }
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
