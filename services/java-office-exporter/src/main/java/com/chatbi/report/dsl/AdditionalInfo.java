package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class AdditionalInfo {
    public AdditionalInfoType type;
    public String name;
    public String value;
    public String appendix;
}
