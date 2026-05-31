package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GenerateOutline {
    public String requirement;
    public String renderedRequirement;
    public Boolean isBroken;
    public List<RequirementItem> items;
}
