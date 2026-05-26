package report.system.exporter.chart;

import java.util.List;

public record ChartSpec(
        String chartType,
        String title,
        List<String> categories,
        List<Series> seriesList,
        boolean canRenderNative
) {
    public record Series(String name, List<Double> values) {}

    public enum NativeType {
        LINE, BAR, PIE, FALLBACK_TABLE
    }

    public NativeType resolveNativeType() {
        if (chartType == null || !canRenderNative || categories.isEmpty() || seriesList.isEmpty()) {
            return NativeType.FALLBACK_TABLE;
        }
        return switch (chartType.toLowerCase()) {
            case "line" -> NativeType.LINE;
            case "bar" -> NativeType.BAR;
            case "pie" -> NativeType.PIE;
            default -> NativeType.FALLBACK_TABLE;
        };
    }
}
