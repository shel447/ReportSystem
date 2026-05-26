package report.system.exporter.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonIgnoreProperties(ignoreUnknown = true)
public class BackCoverConfig {
    @JsonProperty("image")
    public String image;

    @JsonProperty("text")
    public String text;
}
