package com.bi.report.generation;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpHandler;
import com.sun.net.httpserver.HttpServer;
import com.bi.report.generation.core.ExportRequest;
import com.bi.report.generation.core.ExportTarget;
import com.bi.report.generation.core.ExporterOrchestrator;
import com.bi.report.generation.docx.ReportDocxExporter;
import com.bi.report.generation.model.ExportPayload;
import com.bi.report.generation.pptx.ReportPptxExporter;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

public final class HttpServerMain {

    public static void main(String[] args) throws Exception {
        Config config = Config.fromArgs(args);
        Files.createDirectories(config.artifactsDir());

        ExporterOrchestrator orchestrator = new ExporterOrchestrator(
                List.of(new ReportDocxExporter(), new ReportPptxExporter())
        );

        HttpServer server = HttpServer.create(new InetSocketAddress(config.host(), config.port()), 0);
        server.createContext("/health", new HealthHandler());
        server.createContext("/exports", new ExportHandler(orchestrator, config.artifactsDir()));
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
        private final ExporterOrchestrator orchestrator;
        private final Path artifactsDir;
        private final ObjectMapper mapper = new ObjectMapper();

        ExportHandler(ExporterOrchestrator orchestrator, Path artifactsDir) {
            this.orchestrator = orchestrator;
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

                ExportTarget target;
                try {
                    target = ExportTarget.fromFormat(format);
                } catch (IllegalArgumentException e) {
                    writeJson(exchange, 404, "{\"status\":\"unsupported_format\",\"message\":\"" + format + "\"}");
                    return;
                }

                String requestBody = readBody(exchange.getRequestBody());
                ExportPayload payload = mapper.readValue(requestBody, ExportPayload.class);

                String reportId = payload.reportId != null ? payload.reportId : "report";
                String reportName = sanitizeFileStem(
                        payload.reportDsl != null && payload.reportDsl.basicInfo != null && payload.reportDsl.basicInfo.name != null
                                ? payload.reportDsl.basicInfo.name : reportId
                );

                LocalDate today = LocalDate.now();
                Path targetDir = artifactsDir
                        .resolve(String.valueOf(today.getYear()))
                        .resolve(String.format("%02d", today.getMonthValue()))
                        .resolve(String.format("%02d", today.getDayOfMonth()));
                Files.createDirectories(targetDir);

                String fileName = reportName + target.extension();
                Path outputPath = targetDir.resolve(fileName);

                String theme = payload.options != null && payload.options.theme != null ? payload.options.theme : "enterprise-light";
                boolean strict = payload.options != null && payload.options.strictValidation;
                ExportRequest request = new ExportRequest(theme, strict);

                orchestrator.export(payload.reportDsl, target, outputPath, request);

                Map<String, Object> response = new LinkedHashMap<>();
                response.put("status", "success");
                Map<String, String> artifact = new LinkedHashMap<>();
                artifact.put("fileName", fileName);
                artifact.put("storageKey", outputPath.toString());
                artifact.put("contentType", target.contentType());
                response.put("artifact", artifact);
                response.put("warnings", List.of());

                writeJson(exchange, 200, mapper.writeValueAsString(response));

            } catch (Exception exc) {
                exc.printStackTrace();
                Map<String, String> error = Map.of("status", "error", "message", String.valueOf(exc.getMessage()));
                writeJson(exchange, 500, mapper.writeValueAsString(error));
            }
        }
    }

    private static String readBody(InputStream stream) throws IOException {
        return new String(stream.readAllBytes(), StandardCharsets.UTF_8);
    }

    private static String sanitizeFileStem(String text) {
        String candidate = text == null ? "report" : text.trim();
        candidate = candidate.replaceAll("[\\\\/:*?\"<>|]+", "-");
        candidate = candidate.replaceAll("\\s+", "-");
        candidate = candidate.replaceAll("-+", "-");
        candidate = candidate.replaceAll("^[.-]+|[.-]+$", "");
        return candidate.isEmpty() ? "report" : candidate;
    }

    private static void writeJson(HttpExchange exchange, int statusCode, String body) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        byte[] payload = body.getBytes(StandardCharsets.UTF_8);
        exchange.sendResponseHeaders(statusCode, payload.length);
        try (OutputStream output = exchange.getResponseBody()) {
            output.write(payload);
        }
    }
}
