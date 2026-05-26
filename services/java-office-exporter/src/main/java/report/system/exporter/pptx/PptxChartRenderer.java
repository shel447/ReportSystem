package report.system.exporter.pptx;

import org.apache.poi.xslf.usermodel.*;
import report.system.exporter.chart.ChartSpec;
import report.system.exporter.chart.ChartSpecParser;
import report.system.exporter.model.ChartDataProperties;
import report.system.exporter.model.TableDataProperties;
import report.system.exporter.style.ThemeTokens;

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
            renderNativeChart(slide, spec, nativeType, x, yOffset, width, height, theme);
            return yOffset + height + 10;
        } catch (Exception e) {
            String errMsg = "[图表渲染失败: " + e.getMessage() + "]";
            ReportPptxExporter.addTextBox(slide, errMsg, x, yOffset, width, 20, theme.fontSecondary(), theme.smallSizePt(), false, theme.secondary(), false);
            yOffset += 25;
            yOffset = PptxTableRenderer.renderTable(slide, toTableDataProperties(dataProps), x, yOffset, width, theme);
            return yOffset;
        }
    }

    private static void renderNativeChart(XSLFSlide slide, ChartSpec spec, ChartSpec.NativeType nativeType,
                                          int x, int y, int width, int height, ThemeTokens theme) {
        String chartType = spec.chartType() != null ? spec.chartType() : "unknown";
        StringBuilder info = new StringBuilder();
        info.append("图表类型: ").append(chartType).append("\n");
        info.append("类别: ").append(String.join(", ", spec.categories().subList(0, Math.min(5, spec.categories().size()))));
        if (spec.categories().size() > 5) info.append("...");
        info.append("\n");
        for (ChartSpec.Series s : spec.seriesList()) {
            info.append("系列 ").append(s.name()).append(": ");
            for (int i = 0; i < Math.min(5, s.values().size()); i++) {
                if (i > 0) info.append(", ");
                info.append(s.values().get(i));
            }
            if (s.values().size() > 5) info.append("...");
            info.append("\n");
        }
        ReportPptxExporter.addTextBox(slide, info.toString(), x, y, width, height, theme.fontPrimary(), theme.smallSizePt(), false, null, false);
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
