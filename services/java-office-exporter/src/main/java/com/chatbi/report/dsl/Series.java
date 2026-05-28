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
        @JsonSubTypes.Type(value = LineSeries.class, name = "line"),
        @JsonSubTypes.Type(value = BarSeries.class, name = "bar"),
        @JsonSubTypes.Type(value = PieSeries.class, name = "pie"),
        @JsonSubTypes.Type(value = ScatterSeries.class, name = "scatter"),
        @JsonSubTypes.Type(value = RadarSeries.class, name = "radar"),
        @JsonSubTypes.Type(value = GaugeSeries.class, name = "gauge"),
        @JsonSubTypes.Type(value = CandlestickSeries.class, name = "candlestick")
})
public interface Series {
}
