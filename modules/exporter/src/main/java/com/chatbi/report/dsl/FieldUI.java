package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class FieldUI {
    public Object displayPriority;
    public ValueFormat valueFormat;
    public UIEvent event;
    public ConditionalFormat conditionalFormat;
}
