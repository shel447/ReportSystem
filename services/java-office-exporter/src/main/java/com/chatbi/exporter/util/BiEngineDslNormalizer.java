package com.chatbi.exporter.util;

import com.chatbi.exporter.model.VDoc;
import com.chatbi.exporter.model.VNode;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Adapts the BI Engine authoritative frontend DSL to the exporter VDoc model.
 */
public final class BiEngineDslNormalizer {
    private static final TypeReference<LinkedHashMap<String, Object>> MAP_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<List<Map<String, Object>>> ROWS_TYPE = new TypeReference<>() {
    };
    private static final TypeReference<List<Map<String, Object>>> MAP_LIST_TYPE = new TypeReference<>() {
    };

    private BiEngineDslNormalizer() {
    }

    public static VDoc normalize(JsonNode root, ObjectMapper mapper) {
        if (root == null || root.isNull() || !root.isObject()) {
            throw new IllegalArgumentException("Unsupported DSL: root must be an object.");
        }
        if (root.has("catalogs")) {
            return normalizeReport(root, mapper);
        }
        if (root.has("content")) {
            return normalizePpt(root, mapper);
        }
        throw new IllegalArgumentException("Unsupported DSL: expected VDoc, BI Engine Report, or BI Engine PPT.");
    }

    private static VDoc normalizeReport(JsonNode root, ObjectMapper mapper) {
        Map<String, Object> basic = map(root.get("basicInfo"), mapper);
        VDoc doc = new VDoc();
        doc.docId = str(basic.get("id"), "report");
        doc.docType = "report";
        doc.schemaVersion = str(basic.get("schemaVersion"), "1.0.0");
        doc.title = str(basic.get("name"), "Report");

        VNode rootNode = new VNode();
        rootNode.id = "root";
        rootNode.kind = "container";
        rootNode.layout = normalizeLayout(root.get("layout"), mapper);
        rootNode.props = reportRootProps(root, basic, mapper, doc.title);
        rootNode.children = collectReportCatalogs(root.get("catalogs"), mapper);
        doc.root = rootNode;
        return doc;
    }

    private static Map<String, Object> reportRootProps(
            JsonNode root,
            Map<String, Object> basic,
            ObjectMapper mapper,
            String title
    ) {
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        Map<String, Object> cover = map(root.get("cover"), mapper);
        Map<String, Object> summary = map(root.get("summary"), mapper);
        Map<String, Object> signature = map(root.get("signaturePage"), mapper);
        Map<String, Object> layout = map(root.get("layout"), mapper);
        Map<String, Object> grid = objectMap(layout.get("grid"));
        String header = str(basic.get("header"), title);
        String footer = str(basic.get("footer"), "Visual Document OS");
        String layoutType = str(layout.get("type"), "flow");

        props.put("reportTitle", title);
        props.put("tocShow", true);
        props.put("coverEnabled", !cover.isEmpty());
        props.put("coverTitle", str(cover.get("title"), title));
        props.put("coverSubtitle", str(cover.get("subTitle"), str(basic.get("subTitle"), "Report")));
        props.put("coverAuthor", str(cover.get("author"), str(basic.get("creator"), "")));
        props.put("coverDate", str(cover.get("date"), str(basic.get("createdAt"), "")));
        props.put("coverNote", str(basic.get("description"), ""));
        if (cover.containsKey("image")) {
            props.put("coverImage", cover.get("image"));
        }
        List<String> coverContents = coverContents(cover);
        if (!coverContents.isEmpty()) {
            props.put("coverContents", coverContents);
        }
        props.put("summaryEnabled", !summary.isEmpty());
        props.put("summaryTitle", str(summary.get("title"), "总结"));
        props.put("summaryText", str(summary.get("overview"), str(basic.get("description"), "")));
        props.put("signatureEnabled", !signature.isEmpty());
        props.put("signatureTitle", str(signature.get("title"), "签字确认"));
        List<Map<String, Object>> signers = mapList(signature.get("signers"));
        if (!signers.isEmpty()) {
            props.put("signers", signers);
        }
        props.put("headerShow", !header.isBlank());
        props.put("headerText", header);
        props.put("footerShow", true);
        props.put("footerText", footer);
        props.put("showPageNumber", true);
        props.put("pageSize", "A4");
        props.put("paginationStrategy", "flow".equalsIgnoreCase(layoutType) ? "continuous" : "section");
        props.put("marginPreset", "normal");
        props.put("bodyPaddingPx", 12);
        props.put("sectionGapPx", Math.round(VNode.asDouble(grid.get("gap"), 12.0)));
        props.put("blockGapPx", Math.round(Math.max(8.0, VNode.asDouble(grid.get("gap"), 8.0) * 0.75)));
        props.put("nativeChartEnabled", true);
        return props;
    }

    private static List<String> coverContents(Map<String, Object> cover) {
        List<Map<String, Object>> contents = mapList(cover.get("contents"));
        if (contents.isEmpty()) {
            return List.of();
        }
        ArrayList<String> result = new ArrayList<>();
        for (Map<String, Object> item : contents) {
            if (!"text".equalsIgnoreCase(str(item.get("type"), ""))) {
                continue;
            }
            String content = str(item.get("content"), "");
            if (!content.isBlank()) {
                result.add(content);
            }
        }
        return result;
    }

    private static String coverNote(Map<String, Object> cover, Map<String, Object> basic) {
        List<String> parts = new ArrayList<>();
        addIfPresent(parts, cover.get("author"));
        addIfPresent(parts, cover.get("date"));
        addIfPresent(parts, basic.get("description"));
        return String.join(" | ", parts);
    }

    private static List<VNode> collectReportCatalogs(JsonNode catalogs, ObjectMapper mapper) {
        ArrayList<VNode> nodes = new ArrayList<>();
        if (catalogs == null || !catalogs.isArray()) {
            return nodes;
        }
        List<JsonNode> catalogNodes = sortedNodes(catalogs);
        for (int i = 0; i < catalogNodes.size(); i++) {
            VNode catalog = normalizeCatalog(catalogNodes.get(i), mapper, List.of(i + 1));
            if (catalog != null) {
                nodes.add(catalog);
            }
        }
        return nodes;
    }

    private static VNode normalizeCatalog(
            JsonNode catalog,
            ObjectMapper mapper,
            List<Integer> outlinePath
    ) {
        Map<String, Object> catalogMap = map(catalog, mapper);
        String catalogName = str(catalogMap.get("name"), "");
        VNode node = new VNode();
        node.id = str(catalogMap.get("id"), "catalog_" + outlineNumber(outlinePath));
        node.kind = "catalog";
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        props.put("title", catalogName.isBlank() ? "目录 " + outlineNumber(outlinePath) : catalogName);
        props.put("outlineNumber", outlineNumber(outlinePath));
        props.put("outlineLevel", outlinePath.size());
        if (catalogMap.containsKey("order")) {
            props.put("order", catalogMap.get("order"));
        }
        node.props = props;
        node.children = new ArrayList<>();

        JsonNode sections = catalog.get("sections");
        if (sections != null && sections.isArray()) {
            for (JsonNode section : sortedNodes(sections)) {
                node.children.add(normalizeSection(section, mapper));
            }
        }
        JsonNode subCatalogs = catalog.get("subCatalogs");
        if (subCatalogs != null && subCatalogs.isArray()) {
            List<JsonNode> sortedSubCatalogs = sortedNodes(subCatalogs);
            for (int i = 0; i < sortedSubCatalogs.size(); i++) {
                ArrayList<Integer> childPath = new ArrayList<>(outlinePath);
                childPath.add(i + 1);
                VNode subCatalog = normalizeCatalog(sortedSubCatalogs.get(i), mapper, childPath);
                if (subCatalog != null) {
                    node.children.add(subCatalog);
                }
            }
        }
        return node;
    }

    private static VNode normalizeSection(JsonNode section, ObjectMapper mapper) {
        Map<String, Object> sectionMap = map(section, mapper);
        String sectionTitle = str(sectionMap.get("title"), "章节");
        VNode node = new VNode();
        node.id = str(sectionMap.get("id"), "section");
        node.kind = "section";
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        props.put("title", sectionTitle);
        if (sectionMap.containsKey("order")) {
            props.put("order", sectionMap.get("order"));
        }
        node.props = props;
        node.children = new ArrayList<>();
        JsonNode components = section.get("components");
        if (components != null && components.isArray()) {
            for (JsonNode component : components) {
                node.children.addAll(normalizeComponent(component, mapper));
            }
        }
        Map<String, Object> summary = map(section.get("summary"), mapper);
        String overview = str(summary.get("overview"), "");
        if (!overview.isBlank()) {
            VNode text = new VNode();
            text.id = node.id + "_summary";
            text.kind = "text";
            text.props = Map.of("text", overview);
            node.children.add(text);
        }
        return node;
    }

    private static String outlineNumber(List<Integer> outlinePath) {
        ArrayList<String> parts = new ArrayList<>();
        for (Integer item : outlinePath) {
            parts.add(String.valueOf(item));
        }
        return String.join(".", parts);
    }

    private static VDoc normalizePpt(JsonNode root, ObjectMapper mapper) {
        Map<String, Object> basic = map(root.get("basicInfo"), mapper);
        VDoc doc = new VDoc();
        doc.docId = str(basic.get("id"), "ppt");
        doc.docType = "ppt";
        doc.schemaVersion = str(basic.get("schemaVersion"), "1.0.0");
        doc.title = str(basic.get("name"), "PPT");

        VNode rootNode = new VNode();
        rootNode.id = "root";
        rootNode.kind = "container";
        rootNode.props = pptRootProps(basic, doc.title);
        rootNode.children = new ArrayList<>();
        if (root.has("cover")) {
            rootNode.children.add(coverSlide(root.get("cover"), mapper, doc.title));
        }
        rootNode.children.addAll(collectSlides(root.get("content"), mapper));
        if (root.has("backCover")) {
            rootNode.children.add(backCoverSlide(root.get("backCover"), mapper));
        }
        doc.root = rootNode;
        return doc;
    }

    private static Map<String, Object> pptRootProps(Map<String, Object> basic, String title) {
        String header = str(basic.get("header"), title);
        String footer = str(basic.get("footer"), "Visual Document OS");
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        props.put("size", "16:9");
        props.put("defaultBg", "#ffffff");
        props.put("masterShowHeader", !header.isBlank());
        props.put("masterHeaderText", header);
        props.put("masterShowFooter", true);
        props.put("masterFooterText", footer);
        props.put("masterShowSlideNumber", true);
        props.put("masterAccentColor", "#1d4ed8");
        props.put("masterPaddingXPx", 24);
        props.put("masterHeaderTopPx", 12);
        props.put("masterHeaderHeightPx", 26);
        props.put("masterFooterBottomPx", 10);
        props.put("masterFooterHeightPx", 22);
        props.put("nativeChartEnabled", true);
        return props;
    }

    private static List<VNode> collectSlides(JsonNode content, ObjectMapper mapper) {
        ArrayList<VNode> slides = new ArrayList<>();
        if (content == null || !content.isArray()) {
            return slides;
        }
        for (JsonNode item : content) {
            if ("section".equalsIgnoreCase(item.path("type").asText(""))) {
                JsonNode sectionSlides = item.get("slides");
                if (sectionSlides != null && sectionSlides.isArray()) {
                    for (JsonNode slide : sectionSlides) {
                        slides.add(normalizeSlide(slide, mapper));
                    }
                }
                continue;
            }
            slides.add(normalizeSlide(item, mapper));
        }
        return slides;
    }

    private static VNode normalizeSlide(JsonNode slide, ObjectMapper mapper) {
        Map<String, Object> slideMap = map(slide, mapper);
        VNode node = new VNode();
        node.id = str(slideMap.get("id"), "slide");
        node.kind = "slide";
        node.props = Map.of("title", str(slideMap.get("title"), "Slide"));
        node.layout = Map.of("mode", "absolute", "x", 0, "y", 0, "w", 960, "h", 540);
        node.children = new ArrayList<>();
        Map<String, Object> slideLayout = map(slide.get("layout"), mapper);
        JsonNode components = slide.get("components");
        if (components != null && components.isArray()) {
            for (JsonNode component : components) {
                node.children.addAll(normalizeComponent(component, mapper, slideLayout));
            }
        }
        return node;
    }

    private static VNode coverSlide(JsonNode coverNode, ObjectMapper mapper, String fallbackTitle) {
        Map<String, Object> cover = map(coverNode, mapper);
        VNode slide = new VNode();
        slide.id = "cover";
        slide.kind = "slide";
        slide.props = Map.of("title", "封面");
        slide.layout = Map.of("mode", "absolute", "x", 0, "y", 0, "w", 960, "h", 540);
        slide.children = List.of(
                textNode("cover_title", str(cover.get("title"), fallbackTitle), 80, 150, 800, 72, 34, true),
                textNode("cover_subtitle", str(cover.get("subTitle"), ""), 80, 235, 800, 42, 20, false),
                textNode("cover_meta", coverNote(cover, Map.of()), 80, 350, 800, 42, 14, false)
        );
        return slide;
    }

    private static VNode backCoverSlide(JsonNode backCoverNode, ObjectMapper mapper) {
        Map<String, Object> backCover = map(backCoverNode, mapper);
        VNode slide = new VNode();
        slide.id = "back_cover";
        slide.kind = "slide";
        slide.props = Map.of("title", "封底");
        slide.layout = Map.of("mode", "absolute", "x", 0, "y", 0, "w", 960, "h", 540);
        slide.children = List.of(textNode("back_cover_text", str(backCover.get("text"), "Thank You"), 120, 210, 720, 80, 36, true));
        return slide;
    }

    private static VNode textNode(String id, String text, int x, int y, int w, int h, int fontSize, boolean bold) {
        VNode node = new VNode();
        node.id = id;
        node.kind = "text";
        node.layout = Map.of("mode", "absolute", "x", x, "y", y, "w", w, "h", h);
        node.props = Map.of("text", text);
        node.style = Map.of("fontSize", fontSize, "bold", bold);
        return node;
    }

    private static List<VNode> normalizeComponent(JsonNode component, ObjectMapper mapper) {
        return normalizeComponent(component, mapper, Map.of());
    }

    private static List<VNode> normalizeComponent(
            JsonNode component,
            ObjectMapper mapper,
            Map<String, Object> pageLayout
    ) {
        String type = component.path("type").asText("");
        if ("compositeTable".equalsIgnoreCase(type)) {
            return normalizeCompositeTable(component, mapper, pageLayout);
        }
        VNode node = new VNode();
        node.id = component.path("id").asText(type.isBlank() ? "component" : type);
        node.kind = normalizeKind(type);
        node.layout = normalizeLayout(component.get("layout"), mapper, pageLayout);
        node.data = dataBinding(component.get("dataProperties"), mapper);
        node.style = styleMap(component, mapper);
        node.props = switch (node.kind) {
            case "chart" -> chartProps(component, mapper);
            case "table" -> tableProps(component, mapper);
            default -> textProps(component, mapper);
        };
        return List.of(node);
    }

    private static List<VNode> normalizeCompositeTable(
            JsonNode component,
            ObjectMapper mapper,
            Map<String, Object> pageLayout
    ) {
        VNode composite = new VNode();
        composite.id = component.path("id").asText("composite_table");
        composite.kind = "compositeTable";
        composite.layout = normalizeLayout(component.get("layout"), mapper, pageLayout);
        composite.style = styleMap(component, mapper);
        Map<String, Object> data = map(component.get("dataProperties"), mapper);
        LinkedHashMap<String, Object> props = mergedProps(component, mapper);
        props.put("titleText", str(data.get("title"), str(props.get("titleText"), "复合表")));
        composite.props = props;
        composite.children = new ArrayList<>();

        JsonNode tables = component.get("tables");
        if (tables == null || !tables.isArray()) {
            return List.of(composite);
        }
        int index = 0;
        for (JsonNode table : tables) {
            List<VNode> tableNodes = normalizeComponent(table, mapper, pageLayout);
            for (VNode node : tableNodes) {
                if (!"table".equalsIgnoreCase(node.kind)) {
                    continue;
                }
                node.id = component.path("id").asText("composite_table") + "_" + (++index);
                composite.children.add(node);
            }
        }
        return List.of(composite);
    }

    private static String normalizeKind(String type) {
        if ("markdown".equalsIgnoreCase(type)) {
            return "text";
        }
        if ("table".equalsIgnoreCase(type) || "chart".equalsIgnoreCase(type) || "text".equalsIgnoreCase(type)) {
            return type.toLowerCase();
        }
        return type == null || type.isBlank() ? "text" : type;
    }

    private static Map<String, Object> textProps(JsonNode component, ObjectMapper mapper) {
        Map<String, Object> data = map(component.get("dataProperties"), mapper);
        LinkedHashMap<String, Object> props = mergedProps(component, mapper);
        props.put("text", str(data.get("content"), str(data.get("title"), "")));
        return props;
    }

    private static Map<String, Object> tableProps(JsonNode component, ObjectMapper mapper) {
        Map<String, Object> data = map(component.get("dataProperties"), mapper);
        Map<String, Object> advance = map(component.get("advanceProperties"), mapper);
        LinkedHashMap<String, Object> props = mergedProps(component, mapper);
        props.put("titleText", str(data.get("title"), str(props.get("titleText"), "表格")));
        List<Map<String, Object>> columns = mapList(data.get("columns"), mapper);
        List<Map<String, Object>> flatColumns = flattenColumns(columns);
        if (!flatColumns.isEmpty()) {
            props.put("columns", flatColumns);
        }
        List<List<Map<String, Object>>> headerRows = headerRows(columns);
        if (!headerRows.isEmpty()) {
            props.put("headerRows", headerRows);
        }
        List<Map<String, Object>> rows = rows(data.get("data"), mapper);
        if (!rows.isEmpty()) {
            props.put("rows", rows);
        }
        props.put("repeatHeader", bool(advance.get("showHeader"), true));
        Map<String, Object> pagination = objectMap(advance.get("pagination"));
        if (pagination.containsKey("defaultDisplayRows")) {
            props.put("maxRows", pagination.get("defaultDisplayRows"));
        }
        List<Map<String, Object>> mergeCells = mergeRows(data.get("mergeRows"), flatColumns, mapper);
        if (!mergeCells.isEmpty()) {
            props.put("mergeCells", mergeCells);
        }
        return props;
    }

    private static Map<String, Object> chartProps(JsonNode component, ObjectMapper mapper) {
        JsonNode dataProperties = component.get("dataProperties");
        Map<String, Object> data = map(dataProperties, mapper);
        LinkedHashMap<String, Object> props = mergedProps(component, mapper);
        List<Map<String, Object>> series = mapList(data.get("series"), mapper);
        String chartType = resolveChartType(series);
        props.put("chartType", chartType);
        props.put("titleText", str(data.get("title"), str(props.get("titleText"), "图表")));
        List<Map<String, Object>> sampleRows = rows(data.get("data"), mapper);
        if (!sampleRows.isEmpty()) {
            props.put("sampleRows", sampleRows);
        }
        props.put("bindings", chartBindings(series, data));
        props.put("stacked", series.stream().anyMatch(item -> item.get("stack") != null));
        readAxisTitle(preferredAxisNode(dataProperties, component, "xAxis"), props, "xAxisTitle", mapper);
        readAxisTitle(preferredAxisNode(dataProperties, component, "yAxis"), props, "yAxisTitle", mapper);
        Map<String, Object> options = map(component.get("options"), mapper);
        Map<String, Object> eChartOption = objectMap(options.get("eChartOption"));
        if (!eChartOption.isEmpty()) {
            props.put("optionPatch", eChartOption);
        }
        if (options.containsKey("centerText")) {
            props.put("centerText", options.get("centerText"));
        }
        return props;
    }

    private static String resolveChartType(List<Map<String, Object>> series) {
        if (series.isEmpty()) {
            return "auto";
        }
        Set<String> types = new LinkedHashSet<>();
        boolean secondary = false;
        for (Map<String, Object> item : series) {
            types.add(normalizeChartType(str(item.get("type"), "auto")));
            Map<String, Object> encode = objectMap(item.get("encode"));
            if ("1".equals(str(encode.get("yAxisIndex"), ""))) {
                secondary = true;
            }
        }
        if (secondary || types.size() > 1 && (types.contains("bar") || types.contains("line"))) {
            return "combo";
        }
        return types.iterator().next();
    }

    private static List<Map<String, Object>> chartBindings(List<Map<String, Object>> series, Map<String, Object> data) {
        ArrayList<Map<String, Object>> bindings = new ArrayList<>();
        Set<String> seen = new LinkedHashSet<>();
        List<String> axisGroup = stringList(data.get("axisGroup"));
        for (Map<String, Object> item : series) {
            String type = str(item.get("type"), "");
            Map<String, Object> encode = objectMap(item.get("encode"));
            if (!axisGroup.isEmpty()) {
                addBinding(bindings, seen, "x", axisGroup.get(0), "", "");
            }
            if ("pie".equals(type) || "radar".equals(type)) {
                addBinding(bindings, seen, "category", str(encode.get("name"), ""), "", "");
                addBinding(bindings, seen, "value", str(encode.get("value"), ""), "", "");
                continue;
            }
            if ("gauge".equals(type)) {
                addBinding(bindings, seen, "value", str(encode.get("value"), ""), "", "");
                continue;
            }
            if ("candlestick".equals(type)) {
                addBinding(bindings, seen, "y", str(encode.get("close"), ""), "", "");
                continue;
            }
            String axis = "1".equals(str(encode.get("yAxisIndex"), "")) ? "secondary" : "";
            addBinding(bindings, seen, "x", str(encode.get("x"), ""), "", "");
            addBinding(bindings, seen, axis.isBlank() ? "y" : "y2", str(encode.get("y"), ""), "", axis);
        }
        return bindings;
    }

    private static void addBinding(
            List<Map<String, Object>> bindings,
            Set<String> seen,
            String role,
            String field,
            String agg,
            String axis
    ) {
        if (field == null || field.isBlank()) {
            return;
        }
        String key = role + "\u0001" + field + "\u0001" + axis;
        if (!seen.add(key)) {
            return;
        }
        LinkedHashMap<String, Object> binding = new LinkedHashMap<>();
        binding.put("role", role);
        binding.put("field", field);
        if (!agg.isBlank()) {
            binding.put("agg", agg);
        }
        if (!axis.isBlank()) {
            binding.put("axis", axis);
        }
        bindings.add(binding);
    }

    private static void readAxisTitle(JsonNode axisNode, Map<String, Object> props, String key, ObjectMapper mapper) {
        if (axisNode == null || axisNode.isNull()) {
            return;
        }
        JsonNode first = axisNode.isArray() && axisNode.size() > 0 ? axisNode.get(0) : axisNode;
        Map<String, Object> axis = map(first, mapper);
        String name = str(axis.get("name"), "");
        if (!name.isBlank()) {
            props.put(key, name);
        }
    }

    private static JsonNode preferredAxisNode(JsonNode dataProperties, JsonNode component, String key) {
        JsonNode fromDataProperties = dataProperties == null ? null : dataProperties.get(key);
        if (fromDataProperties != null && !fromDataProperties.isNull()) {
            return fromDataProperties;
        }
        return component == null ? null : component.get(key);
    }

    private static String normalizeChartType(String raw) {
        if ("candlestick".equalsIgnoreCase(raw)) {
            return "kline";
        }
        return raw == null || raw.isBlank() ? "auto" : raw;
    }

    private static LinkedHashMap<String, Object> mergedProps(JsonNode component, ObjectMapper mapper) {
        LinkedHashMap<String, Object> props = new LinkedHashMap<>();
        props.putAll(map(component.get("basicProperties"), mapper));
        props.putAll(map(component.get("advanceProperties"), mapper));
        return props;
    }

    private static Map<String, Object> dataBinding(JsonNode dataProperties, ObjectMapper mapper) {
        Map<String, Object> data = map(dataProperties, mapper);
        LinkedHashMap<String, Object> binding = new LinkedHashMap<>();
        copyIfPresent(binding, data, "sourceId");
        copyIfPresent(binding, data, "dataType");
        copyIfPresent(binding, data, "url");
        copyIfPresent(binding, data, "method");
        return binding;
    }

    private static Map<String, Object> styleMap(JsonNode component, ObjectMapper mapper) {
        LinkedHashMap<String, Object> style = new LinkedHashMap<>();
        style.putAll(map(component.get("basicProperties"), mapper));
        style.putAll(map(component.get("advanceProperties"), mapper));
        return style;
    }

    private static Map<String, Object> normalizeLayout(JsonNode layoutNode, ObjectMapper mapper) {
        return normalizeLayout(layoutNode, mapper, Map.of());
    }

    private static Map<String, Object> normalizeLayout(
            JsonNode layoutNode,
            ObjectMapper mapper,
            Map<String, Object> pageLayout
    ) {
        LinkedHashMap<String, Object> layout = new LinkedHashMap<>(map(layoutNode, mapper));
        Object type = layout.remove("type");
        if (type != null) {
            layout.put("mode", String.valueOf(type).toLowerCase());
        }
        Object zIndex = layout.remove("zIndex");
        if (zIndex != null) {
            layout.put("z", zIndex);
        }
        if ("grid".equalsIgnoreCase(str(layout.get("mode"), ""))) {
            return gridToAbsolute(layout, pageLayout);
        }
        return layout;
    }

    private static Map<String, Object> gridToAbsolute(Map<String, Object> layout, Map<String, Object> pageLayout) {
        Map<String, Object> grid = objectMap(pageLayout.get("grid"));
        int cols = Math.max(1, (int) Math.round(VNode.asDouble(grid.get("cols"), 12)));
        double rowHeight = Math.max(24.0, VNode.asDouble(grid.get("rowHeight"), 74.0));
        double gap = Math.max(0.0, VNode.asDouble(grid.get("gap"), 14.0));
        double paddingX = Math.max(0.0, VNode.asDouble(grid.get("paddingX"), 36.0));
        double paddingTop = Math.max(0.0, VNode.asDouble(grid.get("paddingTop"), 78.0));
        double pageWidth = Math.max(120.0, VNode.asDouble(pageLayout.get("w"), 960.0));
        double pageHeight = Math.max(120.0, VNode.asDouble(pageLayout.get("h"), 540.0));
        double paddingBottom = Math.max(0.0, VNode.asDouble(grid.get("paddingBottom"), 28.0));

        double contentWidth = Math.max(60.0, pageWidth - paddingX * 2.0);
        double colWidth = Math.max(1.0, (contentWidth - gap * Math.max(0, cols - 1)) / cols);
        int gx = Math.max(0, (int) Math.round(VNode.asDouble(layout.get("gx"), 0.0)));
        int gy = Math.max(0, (int) Math.round(VNode.asDouble(layout.get("gy"), 0.0)));
        int gw = Math.max(1, (int) Math.round(VNode.asDouble(layout.get("gw"), 1.0)));
        int gh = Math.max(1, (int) Math.round(VNode.asDouble(layout.get("gh"), 1.0)));
        double x = paddingX + gx * (colWidth + gap);
        double y = paddingTop + gy * (rowHeight + gap);
        double w = gw * colWidth + Math.max(0, gw - 1) * gap;
        double h = gh * rowHeight + Math.max(0, gh - 1) * gap;
        double maxW = Math.max(60.0, pageWidth - paddingX - x);
        double maxH = Math.max(40.0, pageHeight - paddingBottom - y);

        LinkedHashMap<String, Object> absolute = new LinkedHashMap<>();
        absolute.put("mode", "absolute");
        absolute.put("x", Math.round(x));
        absolute.put("y", Math.round(y));
        absolute.put("w", Math.round(Math.min(w, maxW)));
        absolute.put("h", Math.round(Math.min(h, maxH)));
        if (layout.containsKey("z")) {
            absolute.put("z", layout.get("z"));
        }
        return absolute;
    }

    private static List<Map<String, Object>> flattenColumns(List<Map<String, Object>> columns) {
        ArrayList<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> column : columns) {
            List<Map<String, Object>> children = mapList(column.get("children"));
            if (!children.isEmpty()) {
                result.addAll(flattenColumns(children));
                continue;
            }
            if (VNode.asDouble(column.get("colSpan"), 1.0) == 0.0) {
                continue;
            }
            LinkedHashMap<String, Object> out = new LinkedHashMap<>();
            out.put("key", str(column.get("key"), ""));
            out.put("title", str(column.get("title"), str(column.get("key"), "")));
            out.put("width", width(column.get("width")));
            out.put("format", format(column));
            result.add(out);
        }
        return result;
    }

    private static List<List<Map<String, Object>>> headerRows(List<Map<String, Object>> columns) {
        boolean hasChildren = columns.stream().anyMatch(column -> !mapList(column.get("children")).isEmpty());
        if (!hasChildren) {
            return List.of();
        }
        ArrayList<Map<String, Object>> top = new ArrayList<>();
        ArrayList<Map<String, Object>> bottom = new ArrayList<>();
        for (Map<String, Object> column : columns) {
            List<Map<String, Object>> children = mapList(column.get("children"));
            if (children.isEmpty()) {
                top.add(headerCell(str(column.get("title"), str(column.get("key"), "")), 2, 1));
                continue;
            }
            top.add(headerCell(str(column.get("title"), ""), 1, Math.max(1, children.size())));
            for (Map<String, Object> child : children) {
                bottom.add(headerCell(str(child.get("title"), str(child.get("key"), "")), 1, 1));
            }
        }
        return List.of(top, bottom);
    }

    private static Map<String, Object> headerCell(String text, int rowSpan, int colSpan) {
        LinkedHashMap<String, Object> cell = new LinkedHashMap<>();
        cell.put("text", text);
        cell.put("rowSpan", rowSpan);
        cell.put("colSpan", colSpan);
        cell.put("align", "center");
        return cell;
    }

    private static List<Map<String, Object>> mergeRows(Object raw, List<Map<String, Object>> flatColumns, ObjectMapper mapper) {
        List<Map<String, Object>> mergeRows = mapList(raw, mapper);
        if (mergeRows.isEmpty()) {
            return List.of();
        }
        LinkedHashMap<String, Integer> columnIndex = new LinkedHashMap<>();
        for (int i = 0; i < flatColumns.size(); i++) {
            columnIndex.put(str(flatColumns.get(i).get("key"), ""), i);
        }
        ArrayList<Map<String, Object>> result = new ArrayList<>();
        for (Map<String, Object> merge : mergeRows) {
            String column = str(merge.get("column"), "");
            Integer col = columnIndex.get(column);
            if (col == null) {
                continue;
            }
            LinkedHashMap<String, Object> out = new LinkedHashMap<>();
            out.put("scope", "body");
            out.put("row", merge.getOrDefault("startRowIndex", 0));
            out.put("col", col);
            out.put("rowSpan", merge.getOrDefault("rowSpan", 1));
            out.put("colSpan", 1);
            result.add(out);
        }
        return result;
    }

    private static List<JsonNode> sortedNodes(JsonNode array) {
        ArrayList<JsonNode> nodes = new ArrayList<>();
        array.forEach(nodes::add);
        nodes.sort(Comparator.comparingInt(node -> node.path("order").asInt(Integer.MAX_VALUE)));
        return nodes;
    }

    private static Map<String, Object> map(JsonNode node, ObjectMapper mapper) {
        if (node == null || node.isNull() || !node.isObject()) {
            return new LinkedHashMap<>();
        }
        return mapper.convertValue(node, MAP_TYPE);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> objectMap(Object raw) {
        if (raw instanceof Map<?, ?> map) {
            LinkedHashMap<String, Object> result = new LinkedHashMap<>();
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                result.put(String.valueOf(entry.getKey()), entry.getValue());
            }
            return result;
        }
        return new LinkedHashMap<>();
    }

    private static List<Map<String, Object>> mapList(Object raw, ObjectMapper mapper) {
        if (raw == null) {
            return List.of();
        }
        return mapper.convertValue(raw, MAP_LIST_TYPE);
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> mapList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        ArrayList<Map<String, Object>> result = new ArrayList<>();
        for (Object item : list) {
            if (item instanceof Map<?, ?> map) {
                LinkedHashMap<String, Object> row = new LinkedHashMap<>();
                for (Map.Entry<?, ?> entry : map.entrySet()) {
                    row.put(String.valueOf(entry.getKey()), entry.getValue());
                }
                result.add(row);
            }
        }
        return result;
    }

    private static List<Map<String, Object>> rows(Object raw, ObjectMapper mapper) {
        if (raw == null) {
            return List.of();
        }
        return mapper.convertValue(raw, ROWS_TYPE);
    }

    private static List<String> stringList(Object raw) {
        if (!(raw instanceof List<?> list)) {
            return List.of();
        }
        ArrayList<String> result = new ArrayList<>();
        for (Object item : list) {
            String text = str(item, "");
            if (!text.isBlank()) {
                result.add(text);
            }
        }
        return result;
    }

    private static String format(Map<String, Object> column) {
        Map<String, Object> uiConfig = objectMap(column.get("uiConfig"));
        Map<String, Object> valueFormat = objectMap(uiConfig.get("valueFormat"));
        String type = str(valueFormat.get("type"), "");
        if ("percentage".equals(type)) {
            return "pct";
        }
        if ("number".equals(type)) {
            return "number";
        }
        return "";
    }

    private static double width(Object raw) {
        if (raw instanceof String text) {
            String clean = text.replace("px", "").trim();
            return VNode.asDouble(clean, 120.0);
        }
        return VNode.asDouble(raw, 120.0);
    }

    private static void copyIfPresent(Map<String, Object> target, Map<String, Object> source, String key) {
        if (source.containsKey(key)) {
            target.put(key, source.get(key));
        }
    }

    private static void addIfPresent(List<String> values, Object raw) {
        String text = str(raw, "");
        if (!text.isBlank()) {
            values.add(text);
        }
    }

    private static boolean bool(Object raw, boolean fallback) {
        return VNode.asBoolean(raw, fallback);
    }

    private static String str(Object raw, String fallback) {
        if (raw == null) {
            return fallback;
        }
        String text = String.valueOf(raw);
        return text == null ? fallback : text;
    }
}
