package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonSubTypes;
import com.fasterxml.jackson.annotation.JsonTypeInfo;

import java.util.List;
import java.util.Map;

@JsonIgnoreProperties(ignoreUnknown = true)
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "type", visible = true)
@JsonSubTypes({
        @JsonSubTypes.Type(value = MarkdownComponent.class, name = "markdown"),
        @JsonSubTypes.Type(value = TextComponent.class, name = "text"),
        @JsonSubTypes.Type(value = TableComponent.class, name = "table"),
        @JsonSubTypes.Type(value = ChartComponent.class, name = "chart"),
        @JsonSubTypes.Type(value = CompositeTableComponent.class, name = "compositeTable"),
})
public abstract class ReportComponent {
    @JsonProperty("id")
    public String id;

    @JsonProperty("type")
    public String type;

    @JsonProperty("layout")
    public Map<String, Object> layout;

    @JsonProperty("basicProperties")
    public Map<String, Object> basicProperties;

    @JsonProperty("advanceProperties")
    public Map<String, Object> advanceProperties;

    @JsonProperty("interactions")
    public List<Map<String, Object>> interactions;
}
