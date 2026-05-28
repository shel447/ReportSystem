package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class UIEvent {
    public UITrigger trigger;
    public String name;
    public List<String> dependency;
}
