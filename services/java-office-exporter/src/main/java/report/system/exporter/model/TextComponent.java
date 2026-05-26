package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class TextComponent extends ReportComponent {
    @JsonProperty("dataProperties")
    public TextDataProperties dataProperties;
}
