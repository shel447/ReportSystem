package com.chatbi.exporter.conf;

/**
 * Word 封面配置。
 */
public record WordCoverConfiguration(
        CoverMetaPosition metaPosition,
        boolean keepMetaOnFirstPage
) {
    public WordCoverConfiguration {
        metaPosition = metaPosition == null ? CoverMetaPosition.BOTTOM_RIGHT : metaPosition;
    }

    public static WordCoverConfiguration defaults() {
        return new WordCoverConfiguration(CoverMetaPosition.BOTTOM_RIGHT, true);
    }
}
