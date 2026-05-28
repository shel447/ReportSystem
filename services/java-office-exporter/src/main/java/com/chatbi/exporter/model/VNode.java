package com.chatbi.exporter.model;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * 虚拟节点（VNode）模型。
 * <p>
 * 节点承载布局（layout）、样式（style）、数据绑定（data）与组件属性（props），
 * 是 Web 编辑器与导出器共享的统一抽象。
 * </p>
 */
public class VNode {
    public String id;
    public String kind;
    public String name;
    public Map<String, Object> layout;
    public Map<String, Object> style;
    public Map<String, Object> data;
    public Map<String, Object> props;
    public List<VNode> children;

    /**
     * 空安全 children 访问。
     */
    public List<VNode> childrenOrEmpty() {
        return children == null ? Collections.emptyList() : children;
    }

    /**
     * 空安全 props 访问。
     */
    public Map<String, Object> propsOrEmpty() {
        return props == null ? Collections.emptyMap() : props;
    }

    /**
     * 空安全 layout 访问。
     */
    public Map<String, Object> layoutOrEmpty() {
        return layout == null ? Collections.emptyMap() : layout;
    }

    /**
     * 空安全 style 访问。
     */
    public Map<String, Object> styleOrEmpty() {
        return style == null ? Collections.emptyMap() : style;
    }

    /**
     * 按字符串读取 props 字段。
     */
    public String propString(String key, String fallback) {
        Object value = propsOrEmpty().get(key);
        return value == null ? fallback : String.valueOf(value);
    }

    /**
     * 按布尔读取 props 字段，兼容字符串 "true"/"false"。
     */
    public boolean propBoolean(String key, boolean fallback) {
        Object value = propsOrEmpty().get(key);
        if (value instanceof Boolean b) {
            return b;
        }
        if (value instanceof String s) {
            if ("true".equalsIgnoreCase(s)) {
                return true;
            }
            if ("false".equalsIgnoreCase(s)) {
                return false;
            }
        }
        return fallback;
    }

    /**
     * 读取 layout 数值字段。
     */
    public double layoutDouble(String key, double fallback) {
        return asDouble(layoutOrEmpty().get(key), fallback);
    }

    /**
     * 读取 style 数值字段。
     */
    public double styleDouble(String key, double fallback) {
        return asDouble(styleOrEmpty().get(key), fallback);
    }

    /**
     * 通用字符串转换。
     */
    public static String asString(Object value, String fallback) {
        return value == null ? fallback : String.valueOf(value);
    }

    /**
     * 通用布尔转换，兼容字符串输入。
     */
    public static boolean asBoolean(Object value, boolean fallback) {
        if (value instanceof Boolean b) {
            return b;
        }
        if (value instanceof String s) {
            if ("true".equalsIgnoreCase(s)) {
                return true;
            }
            if ("false".equalsIgnoreCase(s)) {
                return false;
            }
        }
        return fallback;
    }

    /**
     * 通用数值转换，兼容字符串输入。
     */
    public static double asDouble(Object value, double fallback) {
        if (value instanceof Number n) {
            return n.doubleValue();
        }
        if (value instanceof String s) {
            try {
                return Double.parseDouble(s);
            } catch (NumberFormatException ignored) {
                return fallback;
            }
        }
        return fallback;
    }
}
