package com.chatbi.report.dsl;

import java.util.List;

public class MarkdownComponent implements BIEngineComponent {
    public String id;
    public ComponentType type;
    public ComponentLayout layout;
    public MarkdownBasicProperties basicProperties;
    public MarkdownAdvanceProperties advanceProperties;
    public MarkdownDataProperty dataProperties;
    public List<Interaction> interactions;
}
