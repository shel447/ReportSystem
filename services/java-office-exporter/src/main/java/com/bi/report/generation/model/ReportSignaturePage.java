package com.bi.report.generation.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class ReportSignaturePage {
    @JsonProperty("title")
    public String title;

    @JsonProperty("layoutTemplate")
    public String layoutTemplate;

    @JsonProperty("signers")
    public List<Signer> signers;

    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Signer {
        @JsonProperty("name")
        public String name;

        @JsonProperty("role")
        public String role;

        @JsonProperty("signature")
        public String signature;

        @JsonProperty("date")
        public String date;
    }
}
