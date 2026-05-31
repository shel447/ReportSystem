package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class EnumValueFormat implements ValueFormat {
    public ValueFormatType type;
    @JsonProperty("enum")
    public List<EnumFormatItem> items;
}
