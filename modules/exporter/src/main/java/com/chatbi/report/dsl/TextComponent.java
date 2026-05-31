package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TextComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public TextBasicProperties basicProperties;
    public TextAdvanceProperties advanceProperties;
    public TextDataProperty dataProperties;
    public List<Interaction> interactions;
}
