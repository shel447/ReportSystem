package com.chatbi.exporter.conf;

/**
 * PPT/PPTX 导出配置。
 */
public record PptExportConfiguration(
        PptMasterConfiguration master,
        PptTextBoxConfiguration textBox,
        PptTableConfiguration table
) {
    public PptExportConfiguration {
        master = master == null ? PptMasterConfiguration.defaults() : master;
        textBox = textBox == null ? PptTextBoxConfiguration.defaults() : textBox;
        table = table == null ? PptTableConfiguration.defaults() : table;
    }

    public static PptExportConfiguration defaults() {
        return new PptExportConfiguration(
                PptMasterConfiguration.defaults(),
                PptTextBoxConfiguration.defaults(),
                PptTableConfiguration.defaults()
        );
    }
}
