package com.chatbi.report.dsl;

import java.util.List;

public class Parameter {
    public String id;
    public String label;
    public String description;
    public ParameterInputType inputType;
    public Boolean required;
    public Boolean multi;
    public InteractionMode interactionMode;
    public Integer priority;
    public String placeholder;
    public List<ParameterValue> defaultValue;
    public List<ParameterValue> options;
    public List<ParameterValue> values;
    public Object runtimeContext;
    public String source;
}
