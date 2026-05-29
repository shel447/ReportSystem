package com.chatbi.exporter.conf;

/**
 * 文档导出配置根对象。
 * <p>
 * 该配置独立于 Report DSL。当前 exporter 只使用内置默认配置，后续可由外部生成文档入口可选传入。
 * </p>
 */
public record DocumentExportConfiguration(
        GlobalExportConfiguration global,
        WordExportConfiguration word,
        PptExportConfiguration ppt,
        PdfExportConfiguration pdf
) {
    public DocumentExportConfiguration {
        global = global == null ? GlobalExportConfiguration.defaults() : global;
        word = word == null ? WordExportConfiguration.defaults() : word;
        ppt = ppt == null ? PptExportConfiguration.defaults() : ppt;
        pdf = pdf == null ? PdfExportConfiguration.defaults() : pdf;
    }

    public static DocumentExportConfiguration defaults() {
        return new DocumentExportConfiguration(
                GlobalExportConfiguration.defaults(),
                WordExportConfiguration.defaults(),
                PptExportConfiguration.defaults(),
                PdfExportConfiguration.defaults()
        );
    }
}
