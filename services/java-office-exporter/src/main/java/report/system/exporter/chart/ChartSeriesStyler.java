package report.system.exporter.chart;

import org.apache.poi.xddf.usermodel.XDDFColor;
import org.apache.poi.xddf.usermodel.XDDFLineProperties;
import org.apache.poi.xddf.usermodel.XDDFShapeProperties;
import org.apache.poi.xddf.usermodel.XDDFSolidFillProperties;
import org.apache.poi.xddf.usermodel.chart.XDDFChartData;

public final class ChartSeriesStyler {
    private static final String[] PALETTE = {
            "2563EB", "10B981", "F59E0B", "EF4444", "8B5CF6", "14B8A6"
    };

    private ChartSeriesStyler() {}

    public static void apply(XDDFChartData.Series series, int index, boolean lineChart) {
        XDDFSolidFillProperties fill = new XDDFSolidFillProperties(color(index));
        XDDFLineProperties line = new XDDFLineProperties(fill);
        line.setWidth(lineChart ? 2.25 : 1.0);

        XDDFShapeProperties shape = series.getShapeProperties();
        if (shape == null) {
            shape = new XDDFShapeProperties();
        }
        shape.setFillProperties(fill);
        shape.setLineProperties(line);
        series.setShapeProperties(shape);

        if (lineChart) {
            series.setLineProperties(line);
        }
    }

    private static XDDFColor color(int index) {
        String hex = PALETTE[index % PALETTE.length];
        return XDDFColor.from(new byte[] {
                (byte) Integer.parseInt(hex.substring(0, 2), 16),
                (byte) Integer.parseInt(hex.substring(2, 4), 16),
                (byte) Integer.parseInt(hex.substring(4, 6), 16)
        });
    }
}
