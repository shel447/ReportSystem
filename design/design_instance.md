# 报告实例与文档模块设计

> 本文档是 [总设计文档 (design.md)](design.md) 的子文档，详细描述报告实例和报告文档的数据模型设计。

---

## 1. 模板实例 (TemplateInstance)

模板实例是位于“报告模板”和“报告实例”之间的中间快照。它只在对话式生成流程中产生，用于记录用户在大纲确认阶段显式保存下来的状态，不替代 `ReportInstance`。

### 1.1 数据结构

```python
@dataclass
class TemplateInstance:
    template_instance_id: str
    template_id: str
    template_version: str
    session_id: str
    capture_stage: str  # outline_saved / outline_confirmed

    input_params_snapshot: Dict[str, Any]
    outline_snapshot: List[Dict[str, Any]]
    warnings: List[str]

    report_instance_id: Optional[str] = None
    created_at: datetime
    created_by: str
```

### 1.2 生命周期说明

- `prepare_outline_review`：仅进入大纲确认，不落模板实例
- `edit_outline`：每次显式保存大纲，追加一条 `outline_saved` 记录
- `confirm_outline_generation`：生成报告实例后，再追加一条 `outline_confirmed` 记录，并关联 `report_instance_id`

> 模板实例采用追加式历史记录，不做覆盖更新，也不回写模板。

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
- 模板实例用于承接“模板 -> 实例”的生成前快照，不承担报告内容重生成职责
