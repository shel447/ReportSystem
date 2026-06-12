from sqlglot import exp

from sqlglot.optimizer.merge_subqueries import merge_subqueries

from ....exceptions import UnsupportedSyntaxException
from ....state import CompileSqlState
from ....ibis_ext import compile_sql_state


class ConnectBySchema:
    """ibis不支持递归语法，使用特殊字段把递归信息传递过来，递归信息以'__cb__|'开头，遵循特定格式"""

    def __init__(self, level: int, prior_column: str, no_prior_column: str):
        self.level = level
        self.prior_column = prior_column
        self.no_prior_column = no_prior_column

    def format(self):
        return f"__cb__|l:{self.level}|p:{self.prior_column}|np:{self.no_prior_column}"

    @staticmethod
    def restore(info: str):
        conditions = info.replace("__cb__|", "").split("|")
        level = 0
        prior_column = ""
        no_prior_column = ""
        for condition in conditions:
            pair = condition.split(":")
            if pair[0] == "l":
                level = pair[1]
            elif pair[0] == "p":
                prior_column = pair[1]
            elif pair[0] == "np":
                no_prior_column = pair[1]
        return ConnectBySchema(level=int(level), prior_column=prior_column, no_prior_column=no_prior_column)


def make_up_connect_by(expression: exp.Expression) -> exp.Expression:
    def extract_start_with(where: exp.Where):
        raw_conditions = []
        if isinstance(where.this, exp.And):
            raw_conditions.append(where.this.left)
            raw_conditions.append(where.this.right)

        start_con = [con for con in raw_conditions if not is_custom_connect_by_expr(con)]

        if not start_con:
            return None

        return start_con[0]

    def extract_connect_info(where: exp.Where, columns: list[exp.Column]):
        raw_conditions = []
        if isinstance(where.this, exp.And):
            raw_conditions.append(where.this.left)
            raw_conditions.append(where.this.right)

        info_con = [con.expression.this for con in raw_conditions if is_custom_connect_by_expr(con)]

        if not info_con:
            raise UnsupportedSyntaxException("Connect by query without connect condition.")

        connect_by_schema = ConnectBySchema.restore(info_con[0])
        return {
            "prior_column": [col for col in columns if col.name == connect_by_schema.prior_column][0],
            "no_prior_column": [col for col in columns if col.name == connect_by_schema.no_prior_column][0],
            "level": connect_by_schema.level,
        }

    def is_custom_connect_by_expr(con):
        if not isinstance(con, exp.EQ):
            return False

        return isinstance(con.expression, exp.Literal) and con.expression.this.startswith("__cb__|")

    with_expr = expression.args.get("with_")
    if not with_expr:
        return expression

    connect_by_cte = None
    for cte in with_expr.expressions:
        if cte.alias_or_name.startswith("__connect"):
            connect_by_cte = cte
            break

    if not connect_by_cte:
        return expression

    # 简化
    cte.args["this"] = merge_subqueries(cte.this)

    where = cte.this.args["where"]
    from_ = cte.this.args["from_"]
    selects = cte.this.args["expressions"]

    connect_by_info = extract_connect_info(where, selects)
    start_with = extract_start_with(where)

    connect_by_query = exp.select(*selects).from_(from_)
    prior_part = exp.Prior(this=connect_by_info["prior_column"])
    condition = exp.EQ(this=prior_part, expression=connect_by_info["no_prior_column"])
    connect_expression = exp.Connect(
        start=start_with,
        connect=condition,
        nocycle=True,
    )

    level_cluase = exp.GT(
        this=exp.Column(this=exp.Identifier(this="level", quoted=True)),
        expression=exp.Literal.number(connect_by_info["level"]),
    )
    connect_by_query = connect_by_query.where(level_cluase)
    connect_by_query.set("connect", connect_expression)

    connect_by_cte = exp.CTE(
        this=connect_by_query,
        alias=connect_by_cte.args["alias"],
    )

    new_ctes = []
    ctes = with_expr.expressions
    for cte in ctes:
        if cte.alias_or_name == connect_by_cte.alias_or_name:
            new_ctes.append(connect_by_cte)
        else:
            new_ctes.append(cte)

    expression.set("ctes", new_ctes)
    expression.args["with_"] = exp.With(expressions=new_ctes, recursive=False)

    return expression


def rename_count_alias(expression: exp.Expression) -> exp.Expression:
    """
    把别名，以及外层对别名的引用，都加上特定前缀

    约束：
    1、原始别名起得太简短通用，容易误伤其它字段
    2、别名 映射关系需要在上下文中 妥善传递

    """

    def transformer(node):
        # --- 处理字段引用和原始字段名 ---
        # 匹配所有 Column 节点，比如 SELECT name, WHERE name = ...
        _state: CompileSqlState = compile_sql_state.get()
        rename_alias = _state.lineage.count_expr_alias

        if isinstance(node, exp.Column):
            if node.name in rename_alias:
                # 使用 set('this', ...) 修改字段标识符，保留其原有的引号设置
                node.set(
                    "this",
                    exp.Identifier(
                        this=custom_count_alias(node.name),
                        quoted=node.this.args.get("quoted", False),
                    ),
                )
                return node

        # --- 处理别名定义 ---
        # 匹配 SELECT col AS name 中的 Alias 节点
        if isinstance(node, exp.Alias):
            if node.alias in rename_alias:
                # 修改别名部分
                node.set(
                    "alias",
                    exp.Identifier(
                        this=custom_count_alias(node.alias),
                        quoted=node.args["alias"].args.get("quoted", False),
                    ),
                )
                return node

        # --- 处理 ORDER BY 中的裸标识符 (Identifier) ---
        # 有些情况下，某些方言的引用在 AST 中可能直接是 Identifier 而不是 Column
        if isinstance(node, exp.Identifier) and not isinstance(node.parent, (exp.Column, exp.Alias)):
            if node.name in rename_alias:
                node.set("this", custom_count_alias(node.name))
                return node

        return node

    def custom_count_alias(alias: str) -> str:
        return f"_dte_count_{alias}"

    return expression.transform(transformer)
