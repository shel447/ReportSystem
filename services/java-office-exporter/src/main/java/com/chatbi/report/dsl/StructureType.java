package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonProperty;

public enum StructureType {
    @JsonProperty("flow")
    FLOW,
    @JsonProperty("paged")
    PAGED
}
