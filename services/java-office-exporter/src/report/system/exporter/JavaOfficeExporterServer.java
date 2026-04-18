package report.system.exporter;

import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public final class JavaOfficeExporterServer {
    private static final Pattern REPORT_ID_PATTERN = Pattern.compile("\\\"reportId\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"");
    private static final Pattern REPORT_NAME_PATTERN = Pattern.compile("\\\"name\\\"\\s*:\\s*\\\"([^\\\"]+)\\\"");

    public static void main(String[] args) throws Exception {
        Config config = Config.fromArgs(args);
        Files.createDirectories(config.artifactsDir());

        HttpServer server = HttpServer.create(new InetSocketAddress(config.host(), config.port()), 0);
        server.createContext("/health", new HealthHandler());
        server.createContext("/exports", new ExportHandler(config.artifactsDir()));
        server.setExecutor(Executors.newFixedThreadPool(4));
        server.start();
        System.out.println("JavaOfficeExporterServer started on http://" + config.host() + ":" + config.port());
    }

    record Config(String host, int port, Path artifactsDir) {
        static Config fromArgs(String[] args) {
            String host = "127.0.0.1";
            int port = 18500;
            Path artifactsDir = Path.of("services", "java-office-exporter", "artifacts").toAbsolutePath();
            for (int i = 0; i < args.length; i++) {
                if ("--host".equals(args[i]) && i + 1 < args.length) {
                    host = args[++i];
                } else if ("--port".equals(args[i]) && i + 1 < args.length) {
                    port = Integer.parseInt(args[++i]);
                } else if ("--artifacts-dir".equals(args[i]) && i + 1 < args.length) {
                    artifactsDir = Path.of(args[++i]).toAbsolutePath();
                }
            }
            return new Config(host, port, artifactsDir);
        }
    }

    static final class HealthHandler implements HttpHandler {
        @Override
        public void handle(HttpExchange exchange) throws IOException {
            if (!"GET".equalsIgnoreCase(exchange.getRequestMethod())) {
                writeJson(exchange, 405, "{\"status\":\"method_not_allowed\"}");
                return;
            }
            writeJson(exchange, 200, "{\"status\":\"ok\"}");
        }
    }

    static final class ExportHandler implements HttpHandler {
        private final Path artifactsDir;

        ExportHandler(Path artifactsDir) {
            this.artifactsDir = artifactsDir;
        }

        @Override
        public void handle(HttpExchange exchange) throws IOException {
            try {
                if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
                    writeJson(exchange, 405, "{\"status\":\"method_not_allowed\"}");
                    return;
                }

                String path = exchange.getRequestURI().getPath();
                String format = path.substring(path.lastIndexOf('/') + 1).trim().toLowerCase();
                if (!("word".equals(format) || "ppt".equals(format) || "pdf".equals(format))) {
                    writeJson(exchange, 404, "{\"status\":\"unsupported_format\"}");
                    return;
                }

                String requestBody = readBody(exchange.getRequestBody());
                String reportId = extractFirst(requestBody, REPORT_ID_PATTERN, "report");
                String reportName = sanitizeFileStem(extractFirst(requestBody, REPORT_NAME_PATTERN, reportId));
                LocalDate today = LocalDate.now();
                Path targetDir = artifactsDir.resolve(String.valueOf(today.getYear())).resolve(String.format("%02d", today.getMonthValue())).resolve(String.format("%02d", today.getDayOfMonth()));
                Files.createDirectories(targetDir);

                Artifact artifact = generateArtifact(format, reportId, reportName, requestBody, targetDir);
                String response = toJson(Map.of(
                        "status", "success",
                        "artifact", artifact.toMap(),
                        "warnings", new String[0]
                ));
                writeJson(exchange, 200, response);
            } catch (Exception exc) {
                exc.printStackTrace();
                writeJson(exchange, 500, toJson(Map.of("status", "error", "message", String.valueOf(exc.getMessage()))));
            }
        }

        private Artifact generateArtifact(String format, String reportId, String reportName, String requestBody, Path targetDir) throws IOException {
            String extension = switch (format) {
                case "word" -> ".docx";
                case "ppt" -> ".pptx";
                case "pdf" -> ".pdf";
                default -> throw new IllegalArgumentException("Unsupported format: " + format);
            };
            String fileName = reportName + extension;
            Path outputPath = targetDir.resolve(fileName).toAbsolutePath();
            String summaryText = "Report ID: " + reportId + "\n\n" + requestBody;
            if ("word".equals(format)) {
                writeDocx(outputPath, reportName, summaryText);
                return new Artifact(fileName, outputPath.toString(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document");
            }
            if ("ppt".equals(format)) {
                writePptx(outputPath, reportName, summaryText);
                return new Artifact(fileName, outputPath.toString(), "application/vnd.openxmlformats-officedocument.presentationml.presentation");
            }
            writePdf(outputPath, reportName, summaryText);
            return new Artifact(fileName, outputPath.toString(), "application/pdf");
        }
    }

    record Artifact(String fileName, String storageKey, String contentType) {
        Map<String, String> toMap() {
            Map<String, String> map = new LinkedHashMap<>();
            map.put("fileName", fileName);
            map.put("storageKey", storageKey);
            map.put("contentType", contentType);
            return map;
        }
    }

    private static String readBody(InputStream stream) throws IOException {
        return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
    }

    private static String extractFirst(String text, Pattern pattern, String fallback) {
        Matcher matcher = pattern.matcher(text);
        if (matcher.find()) {
            return matcher.group(1);
        }
        return fallback;
    }

    private static String sanitizeFileStem(String text) {
        String candidate = text == null ? "report" : text.trim();
        candidate = candidate.replaceAll("[\\\\/:*?\"<>|]+", "-");
        candidate = candidate.replaceAll("\\s+", "-");
        candidate = candidate.replaceAll("-+", "-");
        candidate = candidate.replaceAll("^[.-]+|[.-]+$", "");
        return candidate.isEmpty() ? "report" : candidate;
    }

    private static void writeDocx(Path outputPath, String title, String content) throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(outputPath))) {
            addZipEntry(zip, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                      <Default Extension="xml" ContentType="application/xml"/>
                      <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
                    </Types>
                    """);
            addZipEntry(zip, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
                    </Relationships>
                    """);
            String xml = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
                    + "<w:body>"
                    + paragraph(title)
                    + paragraph(content)
                    + "<w:sectPr/></w:body></w:document>";
            addZipEntry(zip, "word/document.xml", xml);
        }
    }

    private static void writePptx(Path outputPath, String title, String content) throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(Files.newOutputStream(outputPath))) {
            addZipEntry(zip, "[Content_Types].xml", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                      <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                      <Default Extension="xml" ContentType="application/xml"/>
                      <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
                      <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
                    </Types>
                    """);
            addZipEntry(zip, "_rels/.rels", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
                    </Relationships>
                    """);
            addZipEntry(zip, "ppt/_rels/presentation.xml.rels", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
                    </Relationships>
                    """);
            addZipEntry(zip, "ppt/presentation.xml", """
                    <?xml version="1.0" encoding="UTF-8"?>
                    <p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
                      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                      xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
                      <p:sldSz cx="9144000" cy="5143500"/>
                      <p:notesSz cx="6858000" cy="9144000"/>
                      <p:sldIdLst>
                        <p:sldId id="256" r:id="rId1"/>
                      </p:sldIdLst>
                    </p:presentation>
                    """);
            String slideXml = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">"
                    + "<p:cSld><p:spTree>"
                    + "<p:nvGrpSpPr><p:cNvPr id=\"1\" name=\"\"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>"
                    + "<p:grpSpPr/>"
                    + textShape(2, title, 400000, 300000, 8400000, 800000)
                    + textShape(3, content, 400000, 1300000, 8400000, 3000000)
                    + "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>";
            addZipEntry(zip, "ppt/slides/slide1.xml", slideXml);
        }
    }

    private static void writePdf(Path outputPath, String title, String content) throws IOException {
        String safeTitle = pdfEscape(title);
        String safeContent = pdfEscape(content.length() > 240 ? content.substring(0, 240) : content);
        String stream = "BT /F1 18 Tf 50 760 Td (" + safeTitle + ") Tj 0 -28 Td /F1 11 Tf (" + safeContent + ") Tj ET";
        byte[] streamBytes = stream.getBytes(StandardCharsets.US_ASCII);
        StringBuilder pdf = new StringBuilder();
        pdf.append("%PDF-1.4\n");
        int[] offsets = new int[6];
        offsets[1] = pdf.length();
        pdf.append("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n");
        offsets[2] = pdf.length();
        pdf.append("2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n");
        offsets[3] = pdf.length();
        pdf.append("3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n");
        offsets[4] = pdf.length();
        pdf.append("4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n");
        offsets[5] = pdf.length();
        pdf.append("5 0 obj << /Length ").append(streamBytes.length).append(" >> stream\n");
        pdf.append(stream).append("\nendstream endobj\n");
        int xrefOffset = pdf.length();
        pdf.append("xref\n0 6\n");
        pdf.append("0000000000 65535 f \n");
        for (int i = 1; i <= 5; i++) {
            pdf.append(String.format("%010d 00000 n \n", offsets[i]));
        }
        pdf.append("trailer << /Size 6 /Root 1 0 R >>\nstartxref\n").append(xrefOffset).append("\n%%EOF");
        Files.writeString(outputPath, pdf.toString(), StandardCharsets.US_ASCII);
    }

    private static String paragraph(String text) {
        String normalized = escapeXml(text).replace("\r", "").replace("\n", "&#10;");
        return "<w:p><w:r><w:t xml:space=\"preserve\">" + normalized + "</w:t></w:r></w:p>";
    }

    private static String textShape(int id, String text, int x, int y, int cx, int cy) {
        String escaped = escapeXml(text).replace("\r", "").replace("\n", "&#10;");
        return "<p:sp>"
                + "<p:nvSpPr><p:cNvPr id=\"" + id + "\" name=\"TextBox " + id + "\"/><p:cNvSpPr txBox=\"1\"/><p:nvPr/></p:nvSpPr>"
                + "<p:spPr><a:xfrm><a:off x=\"" + x + "\" y=\"" + y + "\"/><a:ext cx=\"" + cx + "\" cy=\"" + cy + "\"/></a:xfrm><a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom></p:spPr>"
                + "<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/><a:p><a:r><a:rPr lang=\"zh-CN\" sz=\"1800\"/><a:t>" + escaped + "</a:t></a:r></a:p></p:txBody>"
                + "</p:sp>";
    }

    private static void addZipEntry(ZipOutputStream zip, String name, String content) throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        zip.write(content.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }

    private static String escapeXml(String text) {
        return text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\"", "&quot;")
                .replace("'", "&apos;");
    }

    private static String pdfEscape(String text) {
        String asciiOnly = text.replaceAll("[^\\x20-\\x7E]", "?");
        return asciiOnly
                .replace("\\", "\\\\")
                .replace("(", "\\(")
                .replace(")", "\\)")
                .replace("\r", " ")
                .replace("\n", " ");
    }

    private static void writeJson(HttpExchange exchange, int statusCode, String body) throws IOException {
        Headers headers = exchange.getResponseHeaders();
        headers.set("Content-Type", "application/json; charset=utf-8");
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(statusCode, payload.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(payload);
        }
    }

    private static String toJson(Map<String, ?> value) {
        StringBuilder builder = new StringBuilder();
        appendJson(builder, value);
        return builder.toString();
    }

    @SuppressWarnings("unchecked")
    private static void appendJson(StringBuilder builder, Object value) {
        if (value == null) {
            builder.append("null");
            return;
        }
        if (value instanceof String text) {
            builder.append('"').append(text.replace("\\", "\\\\").replace("\"", "\\\"")).append('"');
            return;
        }
        if (value instanceof Number || value instanceof Boolean) {
            builder.append(value);
            return;
        }
        if (value.getClass().isArray()) {
            Object[] items = (Object[]) value;
            builder.append('[');
            for (int i = 0; i < items.length; i++) {
                if (i > 0) {
                    builder.append(',');
                }
                appendJson(builder, items[i]);
            }
            builder.append(']');
            return;
        }
        if (value instanceof Map<?, ?> map) {
            builder.append('{');
            boolean first = true;
            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) {
                    builder.append(',');
                }
                first = false;
                appendJson(builder, String.valueOf(entry.getKey()));
                builder.append(':');
                appendJson(builder, entry.getValue());
            }
            builder.append('}');
            return;
        }
        appendJson(builder, String.valueOf(value));
    }
}
