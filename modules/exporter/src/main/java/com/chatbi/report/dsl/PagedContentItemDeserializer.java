package com.chatbi.report.dsl;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;

/**
 * Resolves paged content items that do not share a single discriminator.
 */
public final class PagedContentItemDeserializer extends JsonDeserializer<PagedContentItem> {
    @Override
    public PagedContentItem deserialize(JsonParser parser, DeserializationContext context) throws IOException {
        JsonNode node = parser.getCodec().readTree(parser);
        if (node.has("slides") || "section".equals(node.path("type").asText())) {
            return parser.getCodec().treeToValue(node, SlideSection.class);
        }
        return parser.getCodec().treeToValue(node, Slide.class);
    }
}
