import contextvars


compile_sql_state = contextvars.ContextVar("_state")


class CompileSqlState:
    """
    SQL编译过程中的一些状态数据，线程隔离
    """

    def __init__(self):
        self.lineage = SqlLineage()

class SqlLineage:
    def __init__(self):
        self.count_expr_alias = set()
        """count表达式的信息，值是别名"""
