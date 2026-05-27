package com.bi.report.generation.chart;

import org.apache.poi.xddf.usermodel.chart.XDDFChart;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTBarChart;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTCatAx;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTLineChart;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTPlotArea;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTValAx;

public final class ChartAxisNormalizer {
    private static final long CATEGORY_AXIS_ID = 12_345_001L;
    private static final long VALUE_AXIS_ID = 12_345_002L;

    private ChartAxisNormalizer() {}

    public static void normalizeCategoryValueAxes(XDDFChart chart) {
        CTPlotArea plotArea = chart.getCTChart().getPlotArea();

        for (CTLineChart lineChart : plotArea.getLineChartList()) {
            setChartAxisIds(lineChart);
        }
        for (CTBarChart barChart : plotArea.getBarChartList()) {
            setChartAxisIds(barChart);
        }
        for (CTCatAx catAx : plotArea.getCatAxList()) {
            catAx.getAxId().setVal(CATEGORY_AXIS_ID);
            catAx.getCrossAx().setVal(VALUE_AXIS_ID);
        }
        for (CTValAx valAx : plotArea.getValAxList()) {
            valAx.getAxId().setVal(VALUE_AXIS_ID);
            valAx.getCrossAx().setVal(CATEGORY_AXIS_ID);
        }
    }

    private static void setChartAxisIds(CTLineChart chart) {
        if (chart.sizeOfAxIdArray() > 0) {
            chart.getAxIdArray(0).setVal(CATEGORY_AXIS_ID);
        }
        if (chart.sizeOfAxIdArray() > 1) {
            chart.getAxIdArray(1).setVal(VALUE_AXIS_ID);
        }
    }

    private static void setChartAxisIds(CTBarChart chart) {
        if (chart.sizeOfAxIdArray() > 0) {
            chart.getAxIdArray(0).setVal(CATEGORY_AXIS_ID);
        }
        if (chart.sizeOfAxIdArray() > 1) {
            chart.getAxIdArray(1).setVal(VALUE_AXIS_ID);
        }
    }
}
