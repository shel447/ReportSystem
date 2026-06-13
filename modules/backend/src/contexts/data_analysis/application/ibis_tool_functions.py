from typing import Optional

import ibis

RECURSIVE_QUERY_SYMBOL = "recursive_query"

def create_recursive_query(
        root_table_expr: ibis.Table,
        id_col: str,
        parent_col: str,
        start_condition: Optional[ibis.Expr] = None,
        max_depth: int = 2,
        include_columns: Optional[list[str]] = None,
        include_root_layer: Optional[bool] = False,
) -> ibis.Expr:
    """
    创建一个递归查询的纯函数

    参数:
        root_table_expr: Ibis 表表达式
        id_col: 节点ID列名
        parent_col: 父节点ID列名
        start_condition: 起始条件表达式，默认为根节点(parent_col is NULL)
        max_depth: 最大递归深度
        include_columns: 要包含的额外列
        include_root_layer: 查询结果是否包含root层，默认不包含

    返回:
        一个函数，调用时返回递归查询的 Ibis 表达式
    """

    # 加一个字段，专门用来传递 递归的逻辑
    root_table_expr = root_table_expr.mutate(__connect_by_info_field=f"{id_col}")

    # 确定要选择的列
    if include_columns is None:
        include_columns = []
    base_columns = [id_col, parent_col] + include_columns
    base_columns = list(set(base_columns))

    # 给start_condition再加上一点条件，携带level、prior信息
    from src._third_party.ibis.backends.sql.sqlglot.custom_optimize_rules import ConnectBySchema

    connect_condition = (
        root_table_expr.__connect_by_info_field
        == ConnectBySchema(
        level=0 if include_root_layer else 1, prior_column=id_col, no_prior_column=parent_col
    ).format()
    )
    wrapped_cond = start_condition & connect_condition
    result = root_table_expr.filter(wrapped_cond).select(base_columns).alias("__connect").as_table()

    result = result.as_table().alias(RECURSIVE_QUERY_SYMBOL)
    return result