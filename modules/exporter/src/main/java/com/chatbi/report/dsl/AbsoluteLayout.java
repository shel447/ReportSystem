package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class AbsoluteLayout implements ComponentLayout {
    public LayoutType type;
    public Double x;
    public Double y;
    public Double w;
    public Double h;
    public Double zIndex;
}
