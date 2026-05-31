package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

/**
 * Marker for component variants allowed by Report DSL.
 */
@JsonTypeInfo(
        use = JsonTypeInfo.Id.NAME,
        include = JsonTypeInfo.As.EXISTING_PROPERTY,
        property = "type",
        visible = true
)
@JsonSubTypes({
        @JsonSubTypes.Type(value = TextComponent.class, name = "text"),
        @JsonSubTypes.Type(value = TableComponent.class, name = "table"),
        @JsonSubTypes.Type(value = ChartComponent.class, name = "chart"),
        @JsonSubTypes.Type(value = MarkdownComponent.class, name = "markdown"),
        @JsonSubTypes.Type(value = CompositeTable.class, name = "compositeTable")
})
public interface BIEngineComponent {
}
