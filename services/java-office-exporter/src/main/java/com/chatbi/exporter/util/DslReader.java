package com.chatbi.exporter.util;

import com.chatbi.exporter.model.VDoc;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * DSL 读取器。
 * <p>
 * 负责将 JSON DSL 文件反序列化为 {@link com.chatbi.exporter.model.VDoc}。
 * 关闭 FAIL_ON_UNKNOWN_PROPERTIES，确保向前兼容新增字段。
 * </p>
 */
public final class DslReader {
    private static final ObjectMapper MAPPER = new ObjectMapper()
            .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

    private DslReader() {
    }

    /**
     * 从文件读取 DSL。
     */
    public static VDoc read(Path inputPath) throws IOException {
        try (var in = Files.newInputStream(inputPath)) {
            JsonNode root = MAPPER.readTree(in);
            if (root.has("docType") || root.has("root")) {
                return MAPPER.treeToValue(root, VDoc.class);
            }
            return BiEngineDslNormalizer.normalize(root, MAPPER);
        }
    }
}
