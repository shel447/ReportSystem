package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class InteractionTarget {
    public String componentId;
    public InteractionTargetType type;
    public Map<String, Object> params;
}
