package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ResponsiveLevelConfig {
    public ResponsiveSize size;
    public Double maxWidth;
}
