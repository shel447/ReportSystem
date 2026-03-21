# 报告实例与文档模块设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，详细描述报告实例和报告文档的数据模型设计。

---

## 1. 内部模板实例 (TemplateInstance)

`TemplateInstance` 仍然存在，但它已经从用户侧模块退回为**内部生成基线快照**。它不再作为独立页面或独立术语暴露给用户，而是作为 `ReportInstance` 的生成前基线被内部保存，用于支持：

- 从报告实例重新打开一轮“更新”对话
- 查看该实例生成时所确认的大纲与参数
- 基于来源会话节点继续 `Fork` 对话分支

### 1.1 数据结构

```python
@dataclass
class TemplateInstance:
    template_instance_id: str
    template_id: str
    template_version: str
    session_id: str
    capture_stage: str  # generation_baseline

    input_params_snapshot: Dict[str, Any]
    outline_snapshot: List[Dict[str, Any]]
    warnings: List[str]

    report_instance_id: str
    created_at: datetime
    created_by: str
```

### 1.2 生命周期说明

- `prepare_outline_review`：仅进入大纲确认，不落模板实例
- `edit_outline`：只更新当前对话上下文中的待确认大纲
- `confirm_outline_generation`：生成报告实例时，同时创建其唯一的 `generation_baseline` 快照
- `ReportInstance -> update-chat`：基于内部生成基线恢复到 `outline_review` 阶段继续修改（用户侧先在实例详情预览确认大纲，再显式进入对话）

> `TemplateInstance` 现在不再是追加式历史记录。对每个新 `ReportInstance`，系统只保留一份对应的内部生成基线。

### 1.3 与对话分支的关系

- `generation_baseline` 内部模板实例可以作为“更新会话”的来源
- 报告实例的 `Fork` 入口则基于其来源对话中的消息节点发起分支
- 恢复/分支后生成新的 `ChatSession`，并记录来源信息
- 基于内部模板实例恢复时，聊天页会恢复：
  - `matched_template_id`
  - 参数快照
  - 待确认大纲
  - 大纲 warnings
- 该恢复会话继续走对话式流程，但不会修改原始报告实例

> 更新会话与 Fork 会话语义分离：
> - 更新会话：`source_kind = update_from_instance`，只注入一个可见 `review_outline` 节点（不回放原会话前后消息）
> - Fork 会话：沿用消息锚点分支语义，保留分支上下文链

---

## 2. 报告实例 (ReportInstance)

### 2.1 类图

```mermaid
classDiagram
    class ReportInstance {
        +instance_id: str
        +template_id: str
        +template_version: str
        +status: str
        +input_params: Dict~str, Any~
        +outline: List~CatalogContent~
        +metadata: InstanceMetadata
    }
    
    class CatalogContent {
        +catalog_id: str
        +title: str
        +level: int
        +generation_meta: GenerationMeta
        +sections: List~SectionContent~
        +catalogs: List~CatalogContent~
    }
    
    class SectionContent {
        +section_id: str
        +title: str
        +generation_type: str
        +generated_chart: Dict
        +generated_insight: str
        +generated_content_blocks: List
        +trace_info: TraceInfo
        +user_edited: bool
        +user_edit_content: str
        +section_instance_id: str
        +dynamic_params: Dict
    }
    
    class TraceInfo {
        +data_used: Dict
        +llm_prompt: str
        +llm_response: str
        +generated_at: datetime
        +model_name: str
        +generation_cost_ms: int
    }
    
    ReportInstance "1" *-- "0..*" CatalogContent
    CatalogContent "1" *-- "0..*" SectionContent
    CatalogContent "1" *-- "0..*" CatalogContent
    SectionContent "1" *-- "0..1" TraceInfo
```

### 2.2 数据结构

```python
@dataclass
class ReportInstance:
    instance_id: str
    template_id: str
    template_version: str
    status: str  # draft/reviewing/finalized
    
    input_params: Dict[str, Any]
    outline: List[CatalogContent]  # 与模板结构对应，内联生成内容
    
    metadata: InstanceMetadata
```

```python
@dataclass
class CatalogContent:
    """目录内容（内联生成内容）"""
    catalog_id: str
    title: str
    level: int
    
    generation_meta: Optional[GenerationMeta] = None
    
    sections: List['SectionContent'] = field(default_factory=list)
    catalogs: List['CatalogContent'] = field(default_factory=list)
```

```python
@dataclass
class SectionContent:
    """内容节（内联生成内容）"""
    section_id: str
    title: str
    generation_type: str
    
    # 生成内容
    generated_chart: Optional[Dict[str, Any]] = None  # ECharts DSL
    generated_insight: Optional[str] = None
    generated_content_blocks: List[Dict[str, Any]] = field(default_factory=list)
    
    # 溯源信息
    trace_info: Optional[TraceInfo] = None
    
    # 用户编辑状态
    user_edited: bool = False
    user_edit_content: Optional[str] = None
    regenerate_count: int = 0
    
    # 动态生成相关
    section_instance_id: Optional[str] = None
    dynamic_params: Optional[Dict[str, Any]] = None
```

```python
@dataclass
class TraceInfo:
    """溯源信息"""
    data_used: Dict[str, Any]
    llm_prompt: Optional[str] = None
    llm_response: Optional[str] = None
    generated_at: Optional[datetime] = None
    model_name: Optional[str] = None
    generation_cost_ms: Optional[int] = None
```

---

## 3. 报告文档 (ReportDocument)

### 3.1 类图

```mermaid
classDiagram
    class ReportDocument {
        +document_id: str
        +instance_id: str
        +template_id: str
        +format: str
        +file_path: str
        +file_size: int
        +version: int
        +status: str
        +created_at: datetime
        +created_by: str
        +schedule_type: str
        +cron_expression: str
        +timezone: str
        +enabled: bool
        +auto_generate_doc: bool
    }
    
    class ReportInstance {
        +instance_id: str
        +status: str
    }
    
    ReportDocument "1" --> "1" ReportInstance : 关联
```

### 3.2 数据结构

```python
@dataclass
class ReportDocument:
    document_id: str
    instance_id: str
    template_id: str
    
    format: str  # word/pdf/markdown
    file_path: str  # 文档存储路径
    file_size: int
    
    version: int
    status: str  # generating/ready/failed
    
    created_at: datetime
    created_by: str

```

---

## 附录

- 报告实例示例请参见 `instance_example.json`
- 报告文档样例请参见 `report_sample.md`
- 内部模板实例用于承接“模板 -> 实例”的生成基线，不承担报告内容重生成职责
