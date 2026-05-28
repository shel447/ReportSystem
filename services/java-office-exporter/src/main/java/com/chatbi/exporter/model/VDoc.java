package com.chatbi.exporter.model;

import java.util.List;
import java.util.Map;

/**
 * 虚拟文档（VDoc）根模型。
 * <p>
 * 与 Web DSL 结构对齐，保留通用字段并允许各子域按需扩展。
 * 这里使用 public 字段以匹配 Jackson 的轻量反序列化路径。
 * </p>
 */
public class VDoc {
    /** 文档唯一标识。 */
    public String docId;
    /** 文档类型：report/ppt/dashboard。 */
    public String docType;
    /** DSL 版本号。 */
    public String schemaVersion;
    /** 文档标题。 */
    public String title;
    /** 文档语言区域。 */
    public String locale;
    /** 主题标识。 */
    public String themeId;
    /** 节点树根节点。 */
    public VNode root;

    /** 数据源列表（支持静态样例与后续扩展）。 */
    public List<Map<String, Object>> dataSources;
    /** 查询结果列表（可通过 queryId/sourceId 关联图表）。 */
    public List<Map<String, Object>> queries;
    /** 全局过滤条件。 */
    public List<Map<String, Object>> filters;
}
