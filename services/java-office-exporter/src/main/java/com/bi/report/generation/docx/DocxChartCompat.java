package com.bi.report.generation.docx;

import org.apache.poi.xddf.usermodel.chart.XDDFChart;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFRun;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTChart;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTChartSpace;
import org.openxmlformats.schemas.drawingml.x2006.chart.CTExternalData;
import org.openxmlformats.schemas.drawingml.x2006.chart.STDispBlanksAs;
import org.openxmlformats.schemas.drawingml.x2006.wordprocessingDrawing.CTInline;
import org.openxmlformats.schemas.wordprocessingml.x2006.main.CTDrawing;

public final class DocxChartCompat {

    private DocxChartCompat() {}

    public static void normalize(XWPFDocument doc, XDDFChart chart) {
        normalizeDrawingMarkup(doc);
        normalizeChartSpace(chart);
    }

    private static void normalizeDrawingMarkup(XWPFDocument doc) {
        long drawingId = 1;
        for (XWPFParagraph paragraph : doc.getParagraphs()) {
            for (XWPFRun run : paragraph.getRuns()) {
                for (CTDrawing drawing : run.getCTR().getDrawingList()) {
                    for (CTInline inline : drawing.getInlineList()) {
                        inline.getDocPr().setId(drawingId);
                        inline.getDocPr().setName("Chart " + drawingId);
                        inline.getDocPr().setDescr("Report chart " + drawingId);
                        if (!inline.isSetCNvGraphicFramePr()) {
                            inline.addNewCNvGraphicFramePr();
                        }
                        if (!inline.getCNvGraphicFramePr().isSetGraphicFrameLocks()) {
                            inline.getCNvGraphicFramePr().addNewGraphicFrameLocks();
                        }
                        inline.getCNvGraphicFramePr().getGraphicFrameLocks().setNoGrp(true);
                        drawingId++;
                    }
                }
            }
        }
    }

    private static void normalizeChartSpace(XDDFChart chart) {
        CTChartSpace chartSpace = chart.getCTChartSpace();
        if (!chartSpace.isSetRoundedCorners()) {
            chartSpace.addNewRoundedCorners();
        }
        chartSpace.getRoundedCorners().setVal(false);

        CTChart ctChart = chartSpace.getChart();
        if (!ctChart.isSetPlotVisOnly()) {
            ctChart.addNewPlotVisOnly();
        }
        ctChart.getPlotVisOnly().setVal(true);
        if (!ctChart.isSetDispBlanksAs()) {
            ctChart.addNewDispBlanksAs();
        }
        ctChart.getDispBlanksAs().setVal(STDispBlanksAs.GAP);
        if (!ctChart.isSetShowDLblsOverMax()) {
            ctChart.addNewShowDLblsOverMax();
        }
        ctChart.getShowDLblsOverMax().setVal(false);

        CTExternalData externalData = chartSpace.getExternalData();
        if (externalData != null) {
            if (!externalData.isSetAutoUpdate()) {
                externalData.addNewAutoUpdate();
            }
            externalData.getAutoUpdate().setVal(false);
        }
    }
}
