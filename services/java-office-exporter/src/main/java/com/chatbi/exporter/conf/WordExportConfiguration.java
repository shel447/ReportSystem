package com.chatbi.exporter.conf;

/**
 * Word/DOCX 导出配置。
 */
public record WordExportConfiguration(
        WordCoverConfiguration cover,
        WordTocConfiguration toc,
        WordTableConfiguration table
) {
    public WordExportConfiguration {
        cover = cover == null ? WordCoverConfiguration.defaults() : cover;
        toc = toc == null ? WordTocConfiguration.defaults() : toc;
        table = table == null ? WordTableConfiguration.defaults() : table;
    }

    public static WordExportConfiguration defaults() {
        return new WordExportConfiguration(
                WordCoverConfiguration.defaults(),
                WordTocConfiguration.defaults(),
                WordTableConfiguration.defaults()
        );
    }
}
