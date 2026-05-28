package com.chatbi.report.dsl;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * JSON entry point for the Report DSL contract model.
 */
public final class ReportDslJson {
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
            .configure(SerializationFeature.FAIL_ON_EMPTY_BEANS, false);

    private ReportDslJson() {
    }

    public static ObjectMapper objectMapper() {
        return MAPPER.copy();
    }

    public static Report read(String json) throws JsonProcessingException {
        return MAPPER.readValue(json, Report.class);
    }

    public static Report read(Path path) throws IOException {
        try (InputStream input = Files.newInputStream(path)) {
            return read(input);
        }
    }

    public static Report read(InputStream input) throws IOException {
        return MAPPER.readValue(input, Report.class);
    }

    public static String write(Report report) throws JsonProcessingException {
        return MAPPER.writeValueAsString(report);
    }
}
