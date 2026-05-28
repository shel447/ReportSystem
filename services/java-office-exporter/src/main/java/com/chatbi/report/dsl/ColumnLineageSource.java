package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ColumnLineageSource {
    public String dataSourceName;
    public String businessName;
    public String businessName_cn;
    public String field;
    public List<EnumValue> enumValues;
    public FieldUI ui;
}
