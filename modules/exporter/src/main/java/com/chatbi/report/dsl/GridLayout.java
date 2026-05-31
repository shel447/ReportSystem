package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GridLayout implements ComponentLayout {
    public LayoutType type;
    public Double gx;
    public Double gy;
    public Double gw;
    public Double gh;
}
