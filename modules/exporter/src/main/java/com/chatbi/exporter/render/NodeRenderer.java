package com.chatbi.exporter.render;

import com.chatbi.exporter.model.VNode;

import java.io.IOException;

/**
 * 节点渲染器接口。
 *
 * @param <C> 渲染上下文类型（DOCX/PPTX 各自定义）
 */
public interface NodeRenderer<C> {
    /**
     * @return 该渲染器负责的节点 kind
     */
    String kind();

    /**
     * 渲染指定节点。
     */
    void render(C context, VNode node) throws IOException;
}
