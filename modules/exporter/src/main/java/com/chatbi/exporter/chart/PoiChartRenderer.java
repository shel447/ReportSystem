package com.chatbi.exporter.chart;

import org.apache.poi.xddf.usermodel.chart.AxisPosition;
import org.apache.poi.xddf.usermodel.chart.ChartTypes;
import org.apache.poi.xddf.usermodel.chart.LegendPosition;
import org.apache.poi.xddf.usermodel.chart.XDDFCategoryAxis;
import org.apache.poi.xddf.usermodel.chart.XDDFCategoryDataSource;
import org.apache.poi.xddf.usermodel.chart.XDDFChart;
import org.apache.poi.xddf.usermodel.chart.XDDFChartData;
import org.apache.poi.xddf.usermodel.chart.XDDFChartLegend;
import org.apache.poi.xddf.usermodel.chart.XDDFDataSourcesFactory;
import org.apache.poi.xddf.usermodel.chart.XDDFNumericalDataSource;
import org.apache.poi.xddf.usermodel.chart.XDDFValueAxis;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTCatAx;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTRadarChart;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTValAx;
import org.openxmlformats.schemas.drawingml.x2006.chart.STRadarStyle;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * POI 原生图表渲染器。
 * <p>
 * 目标：
 * - 优先使用 POI 原生图元输出可编辑图表
 * - 对 Web chartType 做可预期映射
 * - 在超大数据量场景做采样，控制文档体积和稳定性
 * </p>
 */
public final class PoiChartRenderer {
    private static final int MAX_CATEGORIES = 80;
    private static final int MAX_SERIES = 12;

    private final ChartDatasetBuilder datasetBuilder;
    private final ChartOptionPatchAdapter optionPatchAdapter;

    /**
     * 默认构造：使用内置数据构建器与 optionPatch 适配器。
     */
    public PoiChartRenderer() {
        this(new ChartDatasetBuilder(), new ChartOptionPatchAdapter());
    }

    /**
     * 仅替换数据构建器（便于测试/注入）。
     */
    public PoiChartRenderer(ChartDatasetBuilder datasetBuilder) {
        this(datasetBuilder, new ChartOptionPatchAdapter());
    }

    /**
     * 完整依赖注入构造。
     */
    public PoiChartRenderer(ChartDatasetBuilder datasetBuilder, ChartOptionPatchAdapter optionPatchAdapter) {
        this.datasetBuilder = datasetBuilder;
        this.optionPatchAdapter = optionPatchAdapter;
    }

    /**
     * 使用 spec.sampleRows 渲染。
     */
    public boolean render(XDDFChart chart, ChartSpec spec) {
        return render(chart, spec, spec == null ? List.of() : spec.sampleRows());
    }

    /**
     * 渲染主入口：
     * 1) 构建并归一化数据集
     * 2) 处理标题/图例
     * 3) 按 chartType 分派到具体渲染分支
     */
    public boolean render(XDDFChart chart, ChartSpec spec, List<Map<String, Object>> rows) {
        ChartDataset dataset = normalizeDataset(datasetBuilder.build(spec, rows));
        if (!dataset.isRenderable()) {
            return false;
        }

        setupHeader(chart, spec);
        String type = resolveType(spec);
        return switch (type) {
            case "line" -> renderLine(chart, spec, dataset);
            case "bar" -> renderBar(chart, spec, dataset);
            case "pie" -> renderPie(chart, spec, dataset);
            case "combo" -> renderCombo(chart, spec, dataset);
            case "scatter" -> renderScatter(chart, spec, dataset);
            case "radar" -> renderRadar(chart, spec, dataset);
            case "heatmap" -> renderHeatmap(chart, spec, dataset);
            case "kline" -> renderKline(chart, spec, dataset);
            case "boxplot" -> renderBoxplot(chart, spec, dataset);
            case "sankey" -> renderSankey(chart, spec, dataset);
            case "graph" -> renderGraph(chart, spec, dataset);
            case "treemap" -> renderTreemap(chart, spec, dataset);
            case "sunburst" -> renderSunburst(chart, spec, dataset);
            case "parallel" -> renderParallel(chart, spec, dataset);
            case "funnel" -> renderFunnel(chart, spec, dataset);
            case "gauge" -> renderGauge(chart, spec, dataset);
            case "calendar" -> renderCalendar(chart, spec, dataset);
            case "custom" -> renderCustom(chart, spec, dataset);
            default -> renderLine(chart, spec, dataset);
        };
    }

    /**
     * 统一设置图表标题与图例位置。
     */
    private void setupHeader(XDDFChart chart, ChartSpec spec) {
        String title = spec == null ? "图表" : optionPatchAdapter.resolveTitle(spec);
        chart.setTitleText(title);
        chart.setTitleOverlay(false);
        if (spec == null || optionPatchAdapter.resolveLegendShow(spec)) {
            XDDFChartLegend legend = chart.getOrAddLegend();
            legend.setPosition(spec == null ? LegendPosition.RIGHT : optionPatchAdapter.resolveLegendPosition(spec));
        }
    }

    /**
     * 对过大数据做采样，降低导出失败率和打开卡顿风险。
     */
    private ChartDataset normalizeDataset(ChartDataset dataset) {
        if (!dataset.isRenderable()) {
            return dataset;
        }
        List<String> categories = dataset.categories();
        List<Map.Entry<String, List<Double>>> seriesEntries = List.copyOf(dataset.series().entrySet());
        if (categories.size() <= MAX_CATEGORIES && seriesEntries.size() <= MAX_SERIES) {
            return dataset;
        }

        List<Integer> categoryIndexes = sampleIndexes(categories.size(), MAX_CATEGORIES);
        List<String> sampledCategories = new ArrayList<>(categoryIndexes.size());
        for (int index : categoryIndexes) {
            sampledCategories.add(categories.get(index));
        }

        LinkedHashMap<String, List<Double>> sampledSeries = new LinkedHashMap<>();
        int seriesCount = Math.min(MAX_SERIES, seriesEntries.size());
        for (int s = 0; s < seriesCount; s++) {
            Map.Entry<String, List<Double>> entry = seriesEntries.get(s);
            List<Double> values = entry.getValue();
            ArrayList<Double> sampledValues = new ArrayList<>(categoryIndexes.size());
            for (int index : categoryIndexes) {
                sampledValues.add(index < values.size() ? values.get(index) : 0.0);
            }
            sampledSeries.put(entry.getKey(), sampledValues);
        }
        return new ChartDataset(dataset.categoryLabel(), sampledCategories, sampledSeries);
    }

    /**
     * 在 [0, total-1] 上按等距采样返回下标。
     */
    private List<Integer> sampleIndexes(int total, int limit) {
        if (total <= limit) {
            List<Integer> all = new ArrayList<>(total);
            for (int i = 0; i < total; i++) {
                all.add(i);
            }
            return all;
        }
        List<Integer> indexes = new ArrayList<>(limit);
        double step = (double) (total - 1) / (double) (limit - 1);
        for (int i = 0; i < limit; i++) {
            int index = (int) Math.round(i * step);
            if (index >= total) {
                index = total - 1;
            }
            indexes.add(index);
        }
        return indexes;
    }

    /**
     * 折线图渲染。
     */
    private boolean renderLine(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        XDDFCategoryAxis xAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
        XDDFValueAxis yAxis = chart.createValueAxis(AxisPosition.LEFT);
        if (spec == null) {
            xAxis.setTitle(dataset.categoryLabel());
            yAxis.setTitle("Value");
        } else {
            xAxis.setTitle(optionPatchAdapter.resolveXAxisTitle(spec));
            yAxis.setTitle(optionPatchAdapter.resolveYAxisTitle(spec));
        }

        XDDFCategoryDataSource categories = XDDFDataSourcesFactory.fromArray(dataset.categoryArray());
        XDDFChartData data = chart.createData(ChartTypes.LINE, xAxis, yAxis);
        addSeries(data, categories, dataset.seriesArrays());
        chart.plot(data);
        return true;
    }

    /**
     * 柱状图渲染。
     */
    private boolean renderBar(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        XDDFCategoryAxis xAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
        XDDFValueAxis yAxis = chart.createValueAxis(AxisPosition.LEFT);
        if (spec == null) {
            xAxis.setTitle(dataset.categoryLabel());
            yAxis.setTitle("Value");
        } else {
            xAxis.setTitle(optionPatchAdapter.resolveXAxisTitle(spec));
            yAxis.setTitle(optionPatchAdapter.resolveYAxisTitle(spec));
        }

        XDDFCategoryDataSource categories = XDDFDataSourcesFactory.fromArray(dataset.categoryArray());
        XDDFChartData data = chart.createData(ChartTypes.BAR, xAxis, yAxis);
        addSeries(data, categories, dataset.seriesArrays());
        chart.plot(data);
        return true;
    }

    /**
     * 饼图渲染：POI 原生仅绘制首个系列。
     */
    private boolean renderPie(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        List<Map.Entry<String, Double[]>> series = dataset.seriesArrays();
        if (series.isEmpty()) {
            return false;
        }
        XDDFCategoryDataSource categories = XDDFDataSourcesFactory.fromArray(dataset.categoryArray());
        XDDFChartData data = chart.createData(ChartTypes.PIE, null, null);
        Map.Entry<String, Double[]> first = series.get(0);
        XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(first.getValue());
        XDDFChartData.Series chartSeries = data.addSeries(categories, values);
        chartSeries.setTitle(first.getKey(), null);
        chart.plot(data);
        return true;
    }

    /**
     * 组合图渲染：首系列走柱图，其余系列走折线并挂右轴。
     */
    private boolean renderCombo(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        List<Map.Entry<String, Double[]>> series = dataset.seriesArrays();
        if (series.isEmpty()) {
            return false;
        }
        if (series.size() == 1) {
            return renderLine(chart, spec, dataset);
        }

        XDDFCategoryAxis xAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
        XDDFValueAxis leftAxis = chart.createValueAxis(AxisPosition.LEFT);
        XDDFValueAxis rightAxis = chart.createValueAxis(AxisPosition.RIGHT);
        xAxis.crossAxis(leftAxis);
        leftAxis.crossAxis(xAxis);
        rightAxis.crossAxis(xAxis);
        if (spec == null) {
            xAxis.setTitle(dataset.categoryLabel());
            leftAxis.setTitle("Primary");
            rightAxis.setTitle("Secondary");
        } else {
            xAxis.setTitle(optionPatchAdapter.resolveXAxisTitle(spec));
            leftAxis.setTitle(optionPatchAdapter.resolveYAxisTitle(spec));
            rightAxis.setTitle(spec.dualAxis() ? spec.secondAxisField() : "Secondary");
        }

        XDDFCategoryDataSource categories = XDDFDataSourcesFactory.fromArray(dataset.categoryArray());

        XDDFChartData barData = chart.createData(ChartTypes.BAR, xAxis, leftAxis);
        Map.Entry<String, Double[]> first = series.get(0);
        XDDFNumericalDataSource<Double> firstValues = XDDFDataSourcesFactory.fromArray(first.getValue());
        XDDFChartData.Series barSeries = barData.addSeries(categories, firstValues);
        barSeries.setTitle(first.getKey(), null);
        chart.plot(barData);

        XDDFChartData lineData = chart.createData(ChartTypes.LINE, xAxis, rightAxis);
        for (int i = 1; i < series.size(); i++) {
            Map.Entry<String, Double[]> entry = series.get(i);
            XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(entry.getValue());
            XDDFChartData.Series lineSeries = lineData.addSeries(categories, values);
            lineSeries.setTitle(entry.getKey(), null);
        }
        chart.plot(lineData);
        ensureAxisCrossRefs(chart);
        return true;
    }

    /**
     * 散点图渲染策略：
     * - 若类目可转数值，类目作为 X
     * - 否则单序列用序号为 X
     * - 多序列且类目非数值时，首系列作为 X，其余作为 Y
     */
    private boolean renderScatter(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        List<Map.Entry<String, Double[]>> series = dataset.seriesArrays();
        if (series.isEmpty()) {
            return false;
        }

        XDDFValueAxis xAxis = chart.createValueAxis(AxisPosition.BOTTOM);
        XDDFValueAxis yAxis = chart.createValueAxis(AxisPosition.LEFT);
        if (spec == null) {
            xAxis.setTitle(dataset.categoryLabel());
            yAxis.setTitle("Value");
        } else {
            xAxis.setTitle(optionPatchAdapter.resolveXAxisTitle(spec));
            yAxis.setTitle(optionPatchAdapter.resolveYAxisTitle(spec));
        }

        Double[] numericCategoryX = numericCategoryArray(dataset.categories());
        XDDFChartData data = chart.createData(ChartTypes.SCATTER, xAxis, yAxis);

        if (series.size() == 1) {
            Double[] yValues = series.get(0).getValue();
            Double[] xValues = numericCategoryX != null ? numericCategoryX : indexArray(yValues.length);
            XDDFNumericalDataSource<Double> xData = XDDFDataSourcesFactory.fromArray(xValues);
            XDDFNumericalDataSource<Double> yData = XDDFDataSourcesFactory.fromArray(yValues);
            XDDFChartData.Series singleSeries = data.addSeries(xData, yData);
            singleSeries.setTitle(series.get(0).getKey(), null);
            chart.plot(data);
            return true;
        }

        if (numericCategoryX != null) {
            XDDFNumericalDataSource<Double> xData = XDDFDataSourcesFactory.fromArray(numericCategoryX);
            for (Map.Entry<String, Double[]> entry : series) {
                XDDFNumericalDataSource<Double> yData = XDDFDataSourcesFactory.fromArray(entry.getValue());
                XDDFChartData.Series scatterSeries = data.addSeries(xData, yData);
                scatterSeries.setTitle(entry.getKey(), null);
            }
            chart.plot(data);
            return true;
        }

        Double[] xValues = series.get(0).getValue();
        XDDFNumericalDataSource<Double> xData = XDDFDataSourcesFactory.fromArray(xValues);
        for (int i = 1; i < series.size(); i++) {
            Map.Entry<String, Double[]> entry = series.get(i);
            XDDFNumericalDataSource<Double> yData = XDDFDataSourcesFactory.fromArray(entry.getValue());
            XDDFChartData.Series scatterSeries = data.addSeries(xData, yData);
            scatterSeries.setTitle(entry.getKey(), null);
        }
        chart.plot(data);
        return true;
    }

    /**
     * 雷达图渲染并补强网格线与 marker，提升可读性。
     */
    private boolean renderRadar(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        XDDFCategoryAxis xAxis = chart.createCategoryAxis(AxisPosition.BOTTOM);
        XDDFValueAxis yAxis = chart.createValueAxis(AxisPosition.LEFT);
        if (spec == null) {
            xAxis.setTitle(dataset.categoryLabel());
            yAxis.setTitle("Value");
        } else {
            xAxis.setTitle(optionPatchAdapter.resolveXAxisTitle(spec));
            yAxis.setTitle(optionPatchAdapter.resolveYAxisTitle(spec));
        }

        XDDFCategoryDataSource categories = XDDFDataSourcesFactory.fromArray(dataset.categoryArray());
        XDDFChartData data = chart.createData(ChartTypes.RADAR, xAxis, yAxis);
        addSeries(data, categories, dataset.seriesArrays());
        chart.plot(data);
        strengthenRadarVisuals(chart);
        return true;
    }

    /**
     * 热力图目前映射为柱图近似表达。
     */
    private boolean renderHeatmap(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderBar(chart, spec, dataset);
    }

    /**
     * K 线图当前降级为折线表达。
     */
    private boolean renderKline(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderLine(chart, spec, dataset);
    }

    /**
     * 箱线图当前降级为柱图表达。
     */
    private boolean renderBoxplot(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderBar(chart, spec, dataset);
    }

    /**
     * 桑基图当前降级为柱图表达。
     */
    private boolean renderSankey(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderBar(chart, spec, dataset);
    }

    /**
     * 关系图当前降级为散点表达。
     */
    private boolean renderGraph(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderScatter(chart, spec, dataset);
    }

    /**
     * 矩形树图当前降级为饼图表达。
     */
    private boolean renderTreemap(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderPie(chart, spec, dataset);
    }

    /**
     * 旭日图当前降级为饼图表达。
     */
    private boolean renderSunburst(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderPie(chart, spec, dataset);
    }

    /**
     * 平行坐标当前降级为折线表达。
     */
    private boolean renderParallel(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderLine(chart, spec, dataset);
    }

    /**
     * 漏斗图当前降级为柱图表达。
     */
    private boolean renderFunnel(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderBar(chart, spec, dataset);
    }

    /**
     * 仪表盘图转换为双扇区饼图（value/rest）。
     */
    private boolean renderGauge(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        ChartDataset gaugeDataset = toGaugeDataset(dataset);
        return renderPie(chart, spec, gaugeDataset);
    }

    /**
     * 日历图当前复用热力图分支。
     */
    private boolean renderCalendar(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderHeatmap(chart, spec, dataset);
    }

    /**
     * 自定义图当前回退折线图。
     */
    private boolean renderCustom(XDDFChart chart, ChartSpec spec, ChartDataset dataset) {
        return renderLine(chart, spec, dataset);
    }

    /**
     * 将任意数据集规约为 gauge 需要的 [value, rest] 结构。
     */
    private ChartDataset toGaugeDataset(ChartDataset dataset) {
        List<Map.Entry<String, Double[]>> series = dataset.seriesArrays();
        if (series.isEmpty()) {
            return dataset;
        }
        Double[] first = series.get(0).getValue();
        double sum = 0.0;
        for (Double item : first) {
            sum += item == null ? 0.0 : item;
        }
        double avg = first.length == 0 ? 0.0 : sum / first.length;
        if (avg <= 1.0) {
            avg *= 100.0;
        }
        avg = Math.max(0.0, Math.min(100.0, avg));

        LinkedHashMap<String, List<Double>> gauge = new LinkedHashMap<>();
        gauge.put("gauge", List.of(avg, Math.max(0.0, 100.0 - avg)));
        return new ChartDataset("gauge", List.of("value", "rest"), gauge);
    }

    /**
     * 批量向 POI 图表对象追加系列。
     */
    private void addSeries(
            XDDFChartData data,
            XDDFCategoryDataSource categories,
            List<Map.Entry<String, Double[]>> series
    ) {
        for (Map.Entry<String, Double[]> entry : series) {
            XDDFNumericalDataSource<Double> values = XDDFDataSourcesFactory.fromArray(entry.getValue());
            XDDFChartData.Series chartSeries = data.addSeries(categories, values);
            chartSeries.setTitle(entry.getKey(), null);
        }
    }

    /**
     * 解析最终图表类型：
     * spec.chartType（支持 auto 推断） -> optionPatch.series.type 提示 -> line。
     */
    private String resolveType(ChartSpec spec) {
        if (spec == null) {
            return "line";
        }
        String rawType = spec.chartType() == null ? "" : spec.chartType().trim();
        if (rawType.isBlank()) {
            return "line";
        }
        String normalizedRaw = rawType.toLowerCase(Locale.ROOT);
        if ("auto".equals(normalizedRaw)) {
            return inferAutoType(spec);
        }

        String chartType = ChartTypeCatalog.normalize(rawType);
        if (ChartTypeCatalog.isWebChartType(chartType) && !"custom".equals(chartType) && !"auto".equals(chartType)) {
            return chartType;
        }
        String rawHint = optionPatchAdapter.resolveSeriesTypeHint(spec);
        if (rawHint != null && !rawHint.isBlank()) {
            String hint = ChartTypeCatalog.normalize(rawHint);
            if (ChartTypeCatalog.isWebChartType(hint) && !"auto".equals(hint)) {
                return hint;
            }
        }
        return "line";
    }

    /**
     * 与 Web 端一致的 auto 推断规则：
     * - 含第二轴语义 => combo
     * - 含 x + y => line
     * - 含 category + value => pie
     * - 其他 => bar
     */
    private String inferAutoType(ChartSpec spec) {
        boolean hasSecondary = false;
        boolean hasX = false;
        boolean hasY = false;
        boolean hasCategory = false;
        boolean hasValue = false;

        if (spec.secondAxisField() != null && !spec.secondAxisField().isBlank()) {
            hasSecondary = true;
        }
        for (ChartBinding binding : spec.bindings()) {
            String role = binding.role() == null ? "" : binding.role().trim().toLowerCase(Locale.ROOT);
            String axis = binding.axis() == null ? "" : binding.axis().trim().toLowerCase(Locale.ROOT);
            if ("secondary".equals(axis) || "1".equals(axis)) {
                hasSecondary = true;
            }
            if ("x".equals(role)) {
                hasX = true;
            }
            if ("category".equals(role)) {
                hasCategory = true;
            }
            if ("y".equals(role) || "y1".equals(role) || "y2".equals(role) || "secondary".equals(role) || "ysecondary".equals(role) || "value".equals(role)) {
                hasY = true;
            }
            if ("value".equals(role)) {
                hasValue = true;
            }
            if ("y2".equals(role) || "secondary".equals(role) || "ysecondary".equals(role)) {
                hasSecondary = true;
            }
        }

        if (hasSecondary) {
            return "combo";
        }
        if (hasX && hasY) {
            return "line";
        }
        if (hasCategory && hasValue) {
            return "pie";
        }
        return "bar";
    }

    /**
     * 补强雷达图视觉元素（网格线/marker）。
     */
    private void strengthenRadarVisuals(XDDFChart chart) {
        if (chart == null || chart.getCTChart() == null || chart.getCTChart().getPlotArea() == null) {
            return;
        }
        for (CTRadarChart radar : chart.getCTChart().getPlotArea().getRadarChartArray()) {
            if (radar.getRadarStyle() == null) {
                radar.addNewRadarStyle().setVal(STRadarStyle.MARKER);
            } else {
                radar.getRadarStyle().setVal(STRadarStyle.MARKER);
            }
        }
        for (CTValAx axis : chart.getCTChart().getPlotArea().getValAxArray()) {
            if (!axis.isSetMajorGridlines()) {
                axis.addNewMajorGridlines();
            }
        }
        for (CTCatAx axis : chart.getCTChart().getPlotArea().getCatAxArray()) {
            if (!axis.isSetMajorGridlines()) {
                axis.addNewMajorGridlines();
            }
        }
    }

    /**
     * POI can leave a secondary value axis as <c:crossAx/> in combo charts.
     * PowerPoint treats that as a repairable ChartML issue, so materialize the
     * axis ids explicitly after plotting.
     */
    private void ensureAxisCrossRefs(XDDFChart chart) {
        if (chart == null || chart.getCTChart() == null || chart.getCTChart().getPlotArea() == null) {
            return;
        }
        CTCatAx[] categoryAxes = chart.getCTChart().getPlotArea().getCatAxArray();
        CTValAx[] valueAxes = chart.getCTChart().getPlotArea().getValAxArray();
        if (categoryAxes.length == 0 || valueAxes.length == 0) {
            return;
        }
        long categoryAxisId = categoryAxes[0].getAxId().getVal();
        long valueAxisId = valueAxes[0].getAxId().getVal();
        for (CTCatAx axis : categoryAxes) {
            if (axis.getCrossAx() == null) {
                axis.addNewCrossAx();
            }
            axis.getCrossAx().setVal(valueAxisId);
        }
        for (CTValAx axis : valueAxes) {
            if (axis.getCrossAx() == null) {
                axis.addNewCrossAx();
            }
            axis.getCrossAx().setVal(categoryAxisId);
        }
    }

    /**
     * 若类目全可转数值，则返回数值 X 轴数组；否则返回 null。
     */
    private Double[] numericCategoryArray(List<String> categories) {
        if (categories == null || categories.isEmpty()) {
            return null;
        }
        Double[] values = new Double[categories.size()];
        for (int i = 0; i < categories.size(); i++) {
            Double parsed = toDouble(categories.get(i));
            if (parsed == null) {
                return null;
            }
            values[i] = parsed;
        }
        return values;
    }

    /**
     * 生成 1..N 序号数组作为默认 X 轴。
     */
    private Double[] indexArray(int size) {
        Double[] values = new Double[Math.max(size, 0)];
        for (int i = 0; i < values.length; i++) {
            values[i] = (double) (i + 1);
        }
        return values;
    }

    private Double toDouble(Object value) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        if (value instanceof String text) {
            try {
                return Double.parseDouble(text.trim());
            } catch (NumberFormatException ignored) {
                return null;
            }
        }
        return null;
    }
}
