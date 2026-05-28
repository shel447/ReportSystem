package com.chatbi.exporter.core;

import com.chatbi.exporter.model.VDoc;

import java.io.IOException;
import java.nio.file.Path;

/**
 * 导出器统一接口。
 * <p>
 * 每种目标格式（DOCX/PPTX）实现一个导出器，
 * 由 {@link com.chatbi.exporter.core.ExporterOrchestrator} 进行路由与调度。
 * </p>
 */
public interface DocumentExporter {
    /**
     * @return 当前导出器支持的目标类型
     */
    ExportTarget target();

    /**
     * 判断当前 DSL 文档是否能被该导出器处理。
     */
    boolean supports(VDoc doc);

    /**
     * 执行导出。
     *
     * @param doc DSL 文档
     * @param output 输出文件路径
     * @param request 导出请求参数（主题覆盖、严格校验等）
     */
    void export(VDoc doc, Path output, ExportRequest request) throws IOException;
}
