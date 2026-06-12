from ..exceptions import UnsupportedSyntaxException


def apply_syntax_validation_rules():
    """增强Ibis语法约束：
    1、禁止表与字段进行比较
    """
    strict_comparison()


def strict_comparison():
    """增强比较操作中的类型检查"""
    from ibis.expr.types.core import Expr
    import ibis.expr.operations as ops

    original_eq = Expr.__eq__

    def is_incompatible(left, right):
        return isinstance(left, ops.Relation) and isinstance(right, ops.Value)

    def strict_eq(self, other):
        self_op = self.op()
        if isinstance(other, Expr):
            other_op = other.op()

            if is_incompatible(self_op, other_op) or is_incompatible(other_op, self_op):
                raise UnsupportedSyntaxException("Comparison between 'Relation' and 'Value' is not supported.")

        return original_eq(self, other)

    Expr.__eq__ = strict_eq
