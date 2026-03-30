import { useEffect, useState } from "react";

import type { OutlineNode } from "../../../entities/chat/types";

type OutlineBlock = NonNullable<NonNullable<OutlineNode["outline_instance"]>["blocks"]>[number];

export type OutlineDraftNode = Omit<OutlineNode, "children" | "display_text" | "ai_generated" | "node_kind"> & {
  display_text: string;
  ai_generated: boolean;
  node_kind: "group" | "structured_leaf" | "freeform_leaf";
  children: OutlineDraftNode[];
};

type ReadonlyOutlineTreeProps = {
  mode: "readonly";
  nodes: OutlineNode[];
};

type EditableOutlineTreeProps = {
  mode: "editable";
  nodes: OutlineDraftNode[];
  collapsedNodeIds: Set<string>;
  editingNodeId: string | null;
  selectedNodeId: string | null;
  draftDisplayText: string;
  editingBlockKey: string | null;
  blockDraftValue: string;
  disabled: boolean;
  onToggleCollapse: (nodeId: string) => void;
  onSelectNode: (nodeId: string) => void;
  onBeginEdit: (node: OutlineDraftNode) => void;
  onDraftChange: (value: string) => void;
  onCommitEdit: (nodeId: string) => void;
  onCancelEdit: () => void;
  onBeginBlockEdit: (node: OutlineDraftNode, blockId: string) => void;
  onBlockDraftChange: (value: string) => void;
  onCommitBlockEdit: (nodeId: string, blockId: string) => void;
  onCancelBlockEdit: () => void;
  onAddSibling: (nodeId: string) => void;
  onAddChild: (nodeId: string) => void;
  onMoveUp: (nodeId: string) => void;
  onMoveDown: (nodeId: string) => void;
  onPromote: (nodeId: string) => void;
  onDemote: (nodeId: string) => void;
  onDelete: (nodeId: string) => void;
};

export type OutlineTreeProps = ReadonlyOutlineTreeProps | EditableOutlineTreeProps;

export function OutlineTree(props: OutlineTreeProps) {
  const outlineSignature = props.mode === "readonly" ? buildOutlineSignature(props.nodes) : "";
  const [readonlyCollapsedNodeIds, setReadonlyCollapsedNodeIds] = useState<Set<string>>(() =>
    props.mode === "readonly" ? buildCollapsedNodeIds(props.nodes) : new Set<string>(),
  );

  useEffect(() => {
    if (props.mode === "readonly") {
      setReadonlyCollapsedNodeIds(buildCollapsedNodeIds(props.nodes));
    }
  }, [outlineSignature, props.mode]);

  const nodes = props.mode === "readonly" ? normalizeOutlineTree(props.nodes) : props.nodes;
  const collapsedNodeIds = props.mode === "readonly" ? readonlyCollapsedNodeIds : props.collapsedNodeIds;

  const toggleCollapse = (nodeId: string) => {
    if (props.mode === "readonly") {
      setReadonlyCollapsedNodeIds((current) => {
        const next = new Set(current);
        if (next.has(nodeId)) {
          next.delete(nodeId);
        } else {
          next.add(nodeId);
        }
        return next;
      });
      return;
    }
    props.onToggleCollapse(nodeId);
  };

  return (
    <div className={`outline-tree${props.mode === "readonly" ? " outline-tree--readonly" : ""}`} role="tree">
      {nodes.map((node) => (
        <OutlineTreeNodeView
          key={node.node_id}
          node={node}
          mode={props.mode}
          collapsedNodeIds={collapsedNodeIds}
          editingNodeId={props.mode === "editable" ? props.editingNodeId : null}
          selectedNodeId={props.mode === "editable" ? props.selectedNodeId : null}
          draftDisplayText={props.mode === "editable" ? props.draftDisplayText : ""}
          editingBlockKey={props.mode === "editable" ? props.editingBlockKey : null}
          blockDraftValue={props.mode === "editable" ? props.blockDraftValue : ""}
          disabled={props.mode === "editable" ? props.disabled : false}
          onToggleCollapse={toggleCollapse}
          onSelectNode={props.mode === "editable" ? props.onSelectNode : undefined}
          onBeginEdit={props.mode === "editable" ? props.onBeginEdit : undefined}
          onDraftChange={props.mode === "editable" ? props.onDraftChange : undefined}
          onCommitEdit={props.mode === "editable" ? props.onCommitEdit : undefined}
          onCancelEdit={props.mode === "editable" ? props.onCancelEdit : undefined}
          onBeginBlockEdit={props.mode === "editable" ? props.onBeginBlockEdit : undefined}
          onBlockDraftChange={props.mode === "editable" ? props.onBlockDraftChange : undefined}
          onCommitBlockEdit={props.mode === "editable" ? props.onCommitBlockEdit : undefined}
          onCancelBlockEdit={props.mode === "editable" ? props.onCancelBlockEdit : undefined}
          onAddSibling={props.mode === "editable" ? props.onAddSibling : undefined}
          onAddChild={props.mode === "editable" ? props.onAddChild : undefined}
          onMoveUp={props.mode === "editable" ? props.onMoveUp : undefined}
          onMoveDown={props.mode === "editable" ? props.onMoveDown : undefined}
          onPromote={props.mode === "editable" ? props.onPromote : undefined}
          onDemote={props.mode === "editable" ? props.onDemote : undefined}
          onDelete={props.mode === "editable" ? props.onDelete : undefined}
        />
      ))}
    </div>
  );
}

function OutlineTreeNodeView({
  node,
  mode,
  collapsedNodeIds,
  editingNodeId,
  selectedNodeId,
  draftDisplayText,
  editingBlockKey,
  blockDraftValue,
  disabled,
  onToggleCollapse,
  onSelectNode,
  onBeginEdit,
  onDraftChange,
  onCommitEdit,
  onCancelEdit,
  onBeginBlockEdit,
  onBlockDraftChange,
  onCommitBlockEdit,
  onCancelBlockEdit,
  onAddSibling,
  onAddChild,
  onMoveUp,
  onMoveDown,
  onPromote,
  onDemote,
  onDelete,
}: {
  node: OutlineDraftNode;
  mode: "readonly" | "editable";
  collapsedNodeIds: Set<string>;
  editingNodeId: string | null;
  selectedNodeId: string | null;
  draftDisplayText: string;
  editingBlockKey: string | null;
  blockDraftValue: string;
  disabled: boolean;
  onToggleCollapse: (nodeId: string) => void;
  onSelectNode?: (nodeId: string) => void;
  onBeginEdit?: (node: OutlineDraftNode) => void;
  onDraftChange?: (value: string) => void;
  onCommitEdit?: (nodeId: string) => void;
  onCancelEdit?: () => void;
  onBeginBlockEdit?: (node: OutlineDraftNode, blockId: string) => void;
  onBlockDraftChange?: (value: string) => void;
  onCommitBlockEdit?: (nodeId: string, blockId: string) => void;
  onCancelBlockEdit?: () => void;
  onAddSibling?: (nodeId: string) => void;
  onAddChild?: (nodeId: string) => void;
  onMoveUp?: (nodeId: string) => void;
  onMoveDown?: (nodeId: string) => void;
  onPromote?: (nodeId: string) => void;
  onDemote?: (nodeId: string) => void;
  onDelete?: (nodeId: string) => void;
}) {
  const hasChildren = node.children.length > 0;
  const collapsed = collapsedNodeIds.has(node.node_id);
  const editing = mode === "editable" && editingNodeId === node.node_id;
  const selected = mode === "editable" && (selectedNodeId === node.node_id || editing);
  const blockLookup = new Map<string, OutlineBlock>(
    (node.outline_instance?.blocks ?? []).map((block) => [block.id, block]),
  );
  const hasStructuredOutline = mode === "editable" && Boolean(node.outline_instance?.segments?.length);
  const tools =
    mode === "editable"
      ? [
          { label: "新增同级章节", icon: "+", action: () => onAddSibling?.(node.node_id), disabled },
          { label: "新增子级章节", icon: "↳", action: () => onAddChild?.(node.node_id), disabled },
          { label: "上移章节", icon: "↑", action: () => onMoveUp?.(node.node_id), disabled },
          { label: "下移章节", icon: "↓", action: () => onMoveDown?.(node.node_id), disabled },
          { label: "提升层级章节", icon: "←", action: () => onPromote?.(node.node_id), disabled: disabled || node.level <= 1 },
          { label: "降低层级章节", icon: "→", action: () => onDemote?.(node.node_id), disabled },
          { label: "删除章节", icon: "×", action: () => onDelete?.(node.node_id), disabled },
        ]
      : [];

  const renderEditableContent = () => {
    if (editing && !hasStructuredOutline) {
      return (
        <input
          className="outline-tree__inline-input"
          aria-label={`编辑章节 ${node.node_id}`}
          type="text"
          value={draftDisplayText}
          autoFocus
          disabled={disabled}
          onChange={(event) => onDraftChange?.(event.target.value)}
          onBlur={() => onCommitEdit?.(node.node_id)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              onCommitEdit?.(node.node_id);
            }
            if (event.key === "Escape") {
              event.preventDefault();
              onCancelEdit?.();
            }
          }}
        />
      );
    }

    if (hasStructuredOutline) {
      return (
        <div className="outline-tree__segments">
          {(node.outline_instance?.segments ?? []).map((segment, index) => {
            if (segment.kind === "text") {
              return (
                <span key={`${node.node_id}-text-${index}`} className="outline-tree__segment-text">
                  {segment.text}
                </span>
              );
            }
            const blockKey = buildEditingBlockKey(node.node_id, segment.block_id);
            const block = blockLookup.get(segment.block_id);
            const options = block?.options ?? [];
            const isEditingBlock = editingBlockKey === blockKey;
            if (isEditingBlock && options.length) {
              return (
                <select
                  key={blockKey}
                  className="outline-tree__block-select"
                  aria-label={`编辑区块值 ${segment.block_id}`}
                  value={blockDraftValue}
                  autoFocus
                  disabled={disabled}
                  onChange={(event) => {
                    onBlockDraftChange?.(event.target.value);
                    onCommitBlockEdit?.(node.node_id, segment.block_id);
                  }}
                  onBlur={() => onCommitBlockEdit?.(node.node_id, segment.block_id)}
                >
                  {options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              );
            }
            if (isEditingBlock) {
              return (
                <input
                  key={blockKey}
                  className="outline-tree__block-input"
                  aria-label={`编辑区块值 ${segment.block_id}`}
                  type="text"
                  value={blockDraftValue}
                  autoFocus
                  disabled={disabled}
                  onChange={(event) => onBlockDraftChange?.(event.target.value)}
                  onBlur={() => onCommitBlockEdit?.(node.node_id, segment.block_id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      onCommitBlockEdit?.(node.node_id, segment.block_id);
                    }
                    if (event.key === "Escape") {
                      event.preventDefault();
                      onCancelBlockEdit?.();
                    }
                  }}
                />
              );
            }
            return (
              <button
                key={blockKey}
                type="button"
                className="outline-tree__block-chip"
                aria-label={`编辑区块 ${segment.block_id}`}
                disabled={disabled}
                onClick={() => {
                  onSelectNode?.(node.node_id);
                  onBeginBlockEdit?.(node, segment.block_id);
                }}
              >
                {segment.value || block?.hint || segment.block_id}
              </button>
            );
          })}
        </div>
      );
    }

    return (
      <button
        type="button"
        className="outline-tree__label"
        disabled={disabled}
        onClick={() => {
          onSelectNode?.(node.node_id);
          onBeginEdit?.(node);
        }}
      >
        {node.display_text}
      </button>
    );
  };

  return (
    <div className={`outline-tree__node${selected ? " is-selected" : ""}`} style={{ paddingInlineStart: `${(node.level - 1) * 18}px` }}>
      <div className="outline-tree__row" role="treeitem" aria-expanded={hasChildren ? !collapsed : undefined} aria-level={node.level}>
        <div className="outline-tree__lead">
          {hasChildren ? (
            <button
              type="button"
              className="outline-tree__toggle"
              aria-label={`${collapsed ? "展开" : "折叠"}章节 ${node.node_id}`}
              disabled={mode === "editable" ? disabled : false}
              onClick={() => onToggleCollapse(node.node_id)}
            >
              {collapsed ? "▸" : "▾"}
            </button>
          ) : (
            <span className="outline-tree__spacer" aria-hidden="true" />
          )}
          {node.ai_generated ? <span className="outline-tree__ai-badge">AI</span> : null}
        </div>

        {mode === "editable" ? (
          renderEditableContent()
        ) : (
          <span className="outline-tree__text">{node.display_text}</span>
        )}

        {mode === "editable" ? (
          <div className="outline-tree__toolbar" aria-hidden={disabled}>
            {tools.map((tool) => (
              <button
                key={tool.label}
                type="button"
                className="outline-tree__tool"
                aria-label={`${tool.label} ${node.node_id}`}
                title={tool.label}
                disabled={tool.disabled}
                onClick={tool.action}
              >
                {tool.icon}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {hasChildren && !collapsed ? (
        <div className="outline-tree__children">
          {node.children.map((child) => (
            <OutlineTreeNodeView
              key={child.node_id}
              node={child}
              mode={mode}
              collapsedNodeIds={collapsedNodeIds}
              editingNodeId={editingNodeId}
              selectedNodeId={selectedNodeId}
              draftDisplayText={draftDisplayText}
              editingBlockKey={editingBlockKey}
              blockDraftValue={blockDraftValue}
              disabled={disabled}
              onToggleCollapse={onToggleCollapse}
              onSelectNode={onSelectNode}
              onBeginEdit={onBeginEdit}
              onDraftChange={onDraftChange}
              onCommitEdit={onCommitEdit}
              onCancelEdit={onCancelEdit}
              onBeginBlockEdit={onBeginBlockEdit}
              onBlockDraftChange={onBlockDraftChange}
              onCommitBlockEdit={onCommitBlockEdit}
              onCancelBlockEdit={onCancelBlockEdit}
              onAddSibling={onAddSibling}
              onAddChild={onAddChild}
              onMoveUp={onMoveUp}
              onMoveDown={onMoveDown}
              onPromote={onPromote}
              onDemote={onDemote}
              onDelete={onDelete}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function normalizeOutlineTree(nodes: OutlineNode[]): OutlineDraftNode[] {
  return nodes.map((node) => normalizeOutlineNode(node));
}

export function serializeOutlineTree(nodes: OutlineDraftNode[]): OutlineNode[] {
  return nodes.map((node) => ({
    node_id: node.node_id,
    title: node.title,
    description: node.description,
    level: node.level,
    children: serializeOutlineTree(node.children),
    ...(node.dynamic_meta ? { dynamic_meta: node.dynamic_meta } : {}),
    ...(node.outline_instance ? { outline_instance: node.outline_instance } : {}),
  }));
}

export function buildCollapsedNodeIds(nodes: OutlineNode[]) {
  const ids = new Set<string>();
  const visit = (items: OutlineNode[]) => {
    items.forEach((node) => {
      if (node.level >= 3 && (node.children?.length ?? 0) > 0) {
        ids.add(node.node_id);
      }
      visit(node.children ?? []);
    });
  };
  visit(nodes);
  return ids;
}

export function mapOutlineTree(
  nodes: OutlineDraftNode[],
  nodeId: string,
  updater: (node: OutlineDraftNode) => OutlineDraftNode,
): OutlineDraftNode[] {
  return nodes.map((node) => {
    if (node.node_id === nodeId) {
      return normalizeOutlineNode(updater(node));
    }
    if (node.children.length) {
      return normalizeOutlineNode({ ...node, children: mapOutlineTree(node.children, nodeId, updater) });
    }
    return node;
  });
}

export function buildDisplayText(title: string, description: string) {
  const trimmedTitle = title.trim();
  const trimmedDescription = description.trim();
  if (trimmedTitle && trimmedDescription) {
    return `${trimmedTitle}：${trimmedDescription}`;
  }
  return trimmedTitle || trimmedDescription;
}

export function parseDisplayText(value: string) {
  const text = value.trim();
  const delimiterIndex = text.search(/[：:]/);
  if (delimiterIndex < 0) {
    return { title: text, description: "" };
  }
  return {
    title: text.slice(0, delimiterIndex).trim(),
    description: text.slice(delimiterIndex + 1).trim(),
  };
}

function normalizeOutlineNode(node: OutlineNode): OutlineDraftNode {
  const title = node.title ?? "";
  const description = node.description ?? "";
  const children = normalizeOutlineTree(node.children ?? []);
  const nodeKind = node.node_kind ?? (children.length ? "group" : "freeform_leaf");
  return {
    ...node,
    title,
    description,
    children,
    node_kind: children.length ? "group" : nodeKind,
    ai_generated: children.length ? false : Boolean(node.ai_generated),
    display_text: node.display_text ?? buildDisplayText(title, description),
  };
}

function buildOutlineSignature(nodes: OutlineNode[]): string {
  const parts: string[] = [];
  const visit = (items: OutlineNode[]) => {
    items.forEach((node) => {
      parts.push(`${node.node_id}:${node.level}:${node.children?.length ?? 0}`);
      visit(node.children ?? []);
    });
  };
  visit(nodes ?? []);
  return parts.join("|");
}

export function buildEditingBlockKey(nodeId: string, blockId: string) {
  return `${nodeId}:${blockId}`;
}
