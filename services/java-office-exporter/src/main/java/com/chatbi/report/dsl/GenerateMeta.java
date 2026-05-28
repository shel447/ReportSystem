package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
public class GenerateMeta {
    public Status status;
    public String question;
    public List<AdditionalInfo> additionalInfos;
    public GenerateOutline outline;
    public Map<String, Parameter> parameters;
}
