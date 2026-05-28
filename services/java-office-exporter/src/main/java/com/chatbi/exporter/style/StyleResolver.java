package com.chatbi.exporter.style;

import com.chatbi.exporter.core.ExportRequest;
import com.chatbi.exporter.model.VDoc;

/**
 * 主题解析接口。
 * <p>
 * 输入 DSL 文档与导出请求，输出导出阶段统一使用的 ThemeTokens。
 * </p>
 */
public interface StyleResolver {
    ThemeTokens resolve(VDoc doc, ExportRequest request);
}
