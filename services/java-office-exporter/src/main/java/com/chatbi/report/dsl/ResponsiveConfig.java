package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ResponsiveConfig {
    public Boolean enabled;
    public List<ResponsiveLevelConfig> levels;
    public Double aspectRatio;
    public Double minHeight;
}
