package com.chatbi.exporter.core;

import com.chatbi.exporter.model.VDoc;

import java.io.IOException;
import java.nio.file.Path;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * 导出编排器。
 * <p>
 * 负责将导出请求路由到目标导出器，并在导出前执行 DSL 校验。
 * 该类是 CLI/服务端可复用的统一入口。
 * </p>
 */
public final class ExporterOrchestrator {
    private final Map<ExportTarget, DocumentExporter> exporters;
    private final VDocValidator validator;

    /**
     * @param exporterList 已注册的导出器列表（按 target 去重）
     * @param validator DSL 校验器
     */
    public ExporterOrchestrator(List<DocumentExporter> exporterList, VDocValidator validator) {
        EnumMap<ExportTarget, DocumentExporter> map = new EnumMap<>(ExportTarget.class);
        for (DocumentExporter exporter : exporterList) {
            map.put(exporter.target(), exporter);
        }
        this.exporters = map;
        this.validator = validator;
    }

    /**
     * 导出主流程：
     * 1) 兜底默认请求；2) DSL 校验；3) 目标导出器查找；4) 兼容性校验；5) 导出执行。
     */
    public void export(VDoc doc, ExportTarget target, Path output, ExportRequest request) throws IOException {
        ExportRequest safeRequest = request == null ? ExportRequest.defaults() : request;
        validator.ensureValid(doc, safeRequest.strictValidation());
        DocumentExporter exporter = exporters.get(target);
        if (exporter == null) {
            throw new IllegalArgumentException("No exporter registered for target: " + target);
        }
        if (!exporter.supports(doc)) {
            throw new IllegalArgumentException("Target " + target + " does not support docType: " + doc.docType);
        }
        exporter.export(doc, output, safeRequest);
    }
}
