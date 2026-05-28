package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

@JsonTypeInfo(
        use = JsonTypeInfo.Id.NAME,
        include = JsonTypeInfo.As.EXISTING_PROPERTY,
        property = "type",
        visible = true
)
@JsonSubTypes({
        @JsonSubTypes.Type(value = TimeValueFormat.class, name = "time"),
        @JsonSubTypes.Type(value = NumericValueFormat.class, name = "number"),
        @JsonSubTypes.Type(value = NumericValueFormat.class, name = "percentage"),
        @JsonSubTypes.Type(value = NumericValueFormat.class, name = "byte")
})
public interface ValueFormat {
}
