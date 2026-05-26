package report.system.exporter.core;

import report.system.exporter.model.ReportDslModel;

public final class DslValidator {
    private DslValidator() {}

    public static void validate(ReportDslModel dsl, boolean strict) {
        if (dsl == null) {
            throw new IllegalArgumentException("ReportDsl is null");
        }
        if (dsl.basicInfo == null) {
            if (strict) {
                throw new IllegalArgumentException("basicInfo is required in strict mode");
            }
        }
    }
}
