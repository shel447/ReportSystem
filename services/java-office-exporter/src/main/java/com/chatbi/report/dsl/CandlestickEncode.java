package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class CandlestickEncode {
    public String open;
    public String close;
    public String low;
    public String high;
}
