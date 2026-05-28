package com.chatbi.exporter.render;

import com.chatbi.exporter.model.VNode;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * 节点渲染器注册表。
 * <p>
 * 以 kind 为 key 分发到对应渲染器，未命中时走 fallback，避免导出流程中断。
 * </p>
 */
public final class RendererRegistry<C> {
    private final Map<String, NodeRenderer<C>> renderers = new HashMap<>();
    private final NodeRenderer<C> fallback;

    /**
     * @param fallback 未注册 kind 时使用的兜底渲染器
     */
    public RendererRegistry(NodeRenderer<C> fallback) {
        this.fallback = Objects.requireNonNull(fallback, "fallback");
    }

    /**
     * 注册一个 kind 渲染器。
     */
    public RendererRegistry<C> register(NodeRenderer<C> renderer) {
        renderers.put(normalize(renderer.kind()), renderer);
        return this;
    }

    /**
     * 根据节点 kind 执行渲染。
     */
    public void render(C context, VNode node) throws IOException {
        String kind = node == null ? "" : normalize(node.kind);
        NodeRenderer<C> renderer = renderers.getOrDefault(kind, fallback);
        renderer.render(context, node);
    }

    /**
     * 标准化 kind，规避大小写与空白差异。
     */
    private String normalize(String kind) {
        return kind == null ? "" : kind.trim().toLowerCase();
    }
}
