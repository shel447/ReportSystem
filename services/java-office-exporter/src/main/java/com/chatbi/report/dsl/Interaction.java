package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class Interaction {
    public InteractionTrigger trigger;
    public List<InteractionTarget> targets;
}
