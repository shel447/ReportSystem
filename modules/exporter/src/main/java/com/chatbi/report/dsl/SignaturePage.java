package com.chatbi.report.dsl;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.util.List;

@JsonIgnoreProperties(ignoreUnknown = true)
public class SignaturePage {
    public CoverLayoutType layoutTemplate;
    public String title;
    public List<Signer> signers;
}
