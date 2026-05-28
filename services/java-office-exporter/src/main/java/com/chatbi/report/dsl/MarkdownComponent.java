package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class MarkdownComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public MarkdownBasicProperties basicProperties;
    public MarkdownAdvanceProperties advanceProperties;
    public MarkdownDataProperty dataProperties;
    public List<Interaction> interactions;
}
