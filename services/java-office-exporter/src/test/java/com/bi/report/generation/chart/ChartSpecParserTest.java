package com.bi.report.generation.chart;

import org.junit.jupiter.api.Test;
import com.bi.report.generation.model.ChartDataProperties;
import com.bi.report.generation.model.ReportColumn;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class ChartSpecParserTest {

    @Test
    void testParseLineChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "折线图测试";
        props.columns = List.of(
                createColumn("month", "月份", "dimension"),
                createColumn("value", "数值", "measure")
        );
        props.data = List.of(
                Map.of("month", "1月", "value", 100),
                Map.of("month", "2月", "value", 150),
                Map.of("month", "3月", "value", 120)
        );
        props.series = List.of(
                Map.of("type", "line", "name", "销量", "encode", Map.of("x", "month", "y", "value"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("折线图测试", spec.title());
        assertEquals(3, spec.categories().size());
        assertEquals("1月", spec.categories().get(0));
        assertEquals(1, spec.seriesList().size());
        assertEquals("销量", spec.seriesList().get(0).name());
        assertEquals(3, spec.seriesList().get(0).values().size());
        assertEquals(100.0, spec.seriesList().get(0).values().get(0));
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.LINE, spec.resolveNativeType());
    }

    @Test
    void testParseBarChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "柱状图测试";
        props.columns = List.of(
                createColumn("product", "产品", "dimension"),
                createColumn("sales", "销量", "measure")
        );
        props.data = List.of(
                Map.of("product", "A", "sales", 100),
                Map.of("product", "B", "sales", 200)
        );
        props.series = List.of(
                Map.of("type", "bar", "name", "销量", "encode", Map.of("x", "product", "y", "sales"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("柱状图测试", spec.title());
        assertEquals(2, spec.categories().size());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.BAR, spec.resolveNativeType());
    }

    @Test
    void testParsePieChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "饼图测试";
        props.columns = List.of(
                createColumn("category", "类别", "dimension"),
                createColumn("value", "数值", "measure")
        );
        props.data = List.of(
                Map.of("category", "类别1", "value", 30),
                Map.of("category", "类别2", "value", 70)
        );
        props.series = List.of(
                Map.of("type", "pie", "name", "占比", "encode", Map.of("name", "category", "value", "value"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("饼图测试", spec.title());
        assertEquals(2, spec.categories().size());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.PIE, spec.resolveNativeType());
    }

    @Test
    void testParseScatterChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "散点图测试";
        props.columns = List.of(
                createColumn("x", "X轴", "measure"),
                createColumn("y", "Y轴", "measure")
        );
        props.data = List.of(
                Map.of("x", 10, "y", 20),
                Map.of("x", 30, "y", 40)
        );
        props.series = List.of(
                Map.of("type", "scatter", "name", "数据点", "encode", Map.of("x", "x", "y", "y"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("散点图测试", spec.title());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.FALLBACK_TABLE, spec.resolveNativeType());
    }

    @Test
    void testParseRadarChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "雷达图测试";
        props.columns = List.of(
                createColumn("dimension", "维度", "dimension"),
                createColumn("value", "数值", "measure")
        );
        props.data = List.of(
                Map.of("dimension", "质量", "value", 80),
                Map.of("dimension", "价格", "value", 70)
        );
        props.series = List.of(
                Map.of("type", "radar", "name", "评分", "encode", Map.of("name", "dimension", "value", "value"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("雷达图测试", spec.title());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.FALLBACK_TABLE, spec.resolveNativeType());
    }

    @Test
    void testParseGaugeChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "仪表盘测试";
        props.columns = List.of(
                createColumn("metric", "指标", "dimension"),
                createColumn("value", "数值", "measure")
        );
        props.data = List.of(
                Map.of("metric", "完成率", "value", 85)
        );
        props.series = List.of(
                Map.of("type", "gauge", "name", "完成率", "encode", Map.of("name", "metric", "value", "value"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("仪表盘测试", spec.title());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.FALLBACK_TABLE, spec.resolveNativeType());
    }

    @Test
    void testParseCandlestickChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "K线图测试";
        props.columns = List.of(
                createColumn("date", "日期", "dimension"),
                createColumn("open", "开盘", "measure"),
                createColumn("close", "收盘", "measure")
        );
        props.data = List.of(
                Map.of("date", "05-20", "open", 100, "close", 105)
        );
        props.series = List.of(
                Map.of("type", "candlestick", "name", "股价", "encode", Map.of("x", "date", "y", List.of("open", "close")))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals("K线图测试", spec.title());
        assertTrue(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.FALLBACK_TABLE, spec.resolveNativeType());
    }

    @Test
    void testParseMultiSeriesChart() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "多系列图表";
        props.columns = List.of(
                createColumn("month", "月份", "dimension"),
                createColumn("sales", "销售", "measure"),
                createColumn("target", "目标", "measure")
        );
        props.data = List.of(
                Map.of("month", "1月", "sales", 100, "target", 120),
                Map.of("month", "2月", "sales", 150, "target", 130)
        );
        props.series = List.of(
                Map.of("type", "line", "name", "实际", "encode", Map.of("x", "month", "y", "sales")),
                Map.of("type", "line", "name", "目标", "encode", Map.of("x", "month", "y", "target"))
        );

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals(2, spec.seriesList().size());
        assertEquals("实际", spec.seriesList().get(0).name());
        assertEquals("目标", spec.seriesList().get(1).name());
        assertEquals(2, spec.seriesList().get(0).values().size());
        assertEquals(2, spec.seriesList().get(1).values().size());
    }

    @Test
    void testParseEmptyData() {
        ChartDataProperties props = new ChartDataProperties();
        props.dataType = "static";
        props.title = "空数据";
        props.columns = List.of();
        props.data = List.of();
        props.series = List.of();

        ChartSpec spec = ChartSpecParser.parse(props);

        assertNotNull(spec);
        assertEquals(0, spec.categories().size());
        assertEquals(0, spec.seriesList().size());
        assertFalse(spec.canRenderNative());
        assertEquals(ChartSpec.NativeType.FALLBACK_TABLE, spec.resolveNativeType());
    }

    @Test
    void testParseNullProperties() {
        ChartSpec spec = ChartSpecParser.parse(null);

        assertNotNull(spec);
        assertEquals(0, spec.categories().size());
        assertEquals(0, spec.seriesList().size());
        assertFalse(spec.canRenderNative());
    }

    private ReportColumn createColumn(String key, String title, String type) {
        ReportColumn col = new ReportColumn();
        col.key = key;
        col.title = title;
        col.type = type;
        return col;
    }
}
