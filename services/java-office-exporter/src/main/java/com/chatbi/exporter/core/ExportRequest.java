package com.chatbi.exporter.core;

/**
 * 导出请求参数。
 * <p>
 * 用于承载导出时的运行配置，而非 DSL 原始内容。
 * </p>
 */
public final class ExportRequest {
    private final String themeOverride;
    private final boolean strictValidation;

    /**
     * @param themeOverride 可选主题覆盖（优先级高于 DSL 中的 themeId）
     * @param strictValidation 是否启用严格校验（遇到问题直接失败）
     */
    public ExportRequest(String themeOverride, boolean strictValidation) {
        this.themeOverride = themeOverride;
        this.strictValidation = strictValidation;
    }

    public String themeOverride() {
        return themeOverride;
    }

    public boolean strictValidation() {
        return strictValidation;
    }

    /**
     * 默认导出配置：
     * - 不覆盖主题
     * - 非严格校验（只告警不抛错）
     */
    public static ExportRequest defaults() {
        return new ExportRequest(null, false);
    }
}
