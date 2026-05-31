package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

/**
 * Marker for component layout variants.
 */
@JsonTypeInfo(
        use = JsonTypeInfo.Id.NAME,
        include = JsonTypeInfo.As.EXISTING_PROPERTY,
        property = "type",
        visible = true
)
@JsonSubTypes({
        @JsonSubTypes.Type(value = GridLayout.class, name = "grid"),
        @JsonSubTypes.Type(value = FlowLayout.class, name = "flow"),
        @JsonSubTypes.Type(value = AbsoluteLayout.class, name = "absolute")
})
public interface ComponentLayout {
}
