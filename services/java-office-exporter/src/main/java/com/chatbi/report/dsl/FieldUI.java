package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

@JsonIgnoreProperties(ignoreUnknown = true)
public class FieldUI {
    public DisplayPriority displayPriority;
    public ValueFormat valueFormat;
    public UIEvent event;
}
