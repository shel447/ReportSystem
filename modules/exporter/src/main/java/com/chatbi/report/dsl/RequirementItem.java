package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class RequirementItem {
    public String id;
    public String label;
    public RequirementKind kind;
    public Boolean required;
    public Boolean multi;
    public String description;
    public String sourceParameterId;
    public RequirementWidget widget;
    public List<ParameterValue> defaultValue;
    public List<ParameterValue> values;
    public ValueSource valueSource;
}
