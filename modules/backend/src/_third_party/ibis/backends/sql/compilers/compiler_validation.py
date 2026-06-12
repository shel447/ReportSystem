import ibis.expr.operations as ops
from ....exceptions import UnsupportedSyntaxException


def validate(op: ops.Node) -> None:
    _raise_on_leaked_derived_fields(op)


def _raise_on_leaked_derived_fields(op: ops.Node) -> None:
    seen: set[tuple[ops.Node, frozenset[ops.Relation]]] = set()

    def walk_values(values, visible_relations: frozenset[ops.Relation]) -> None:
        for item in values:
            if isinstance(item, ops.Node):
                walk(item, visible_relations)

    def walk(node: ops.Node, visible_relations: frozenset[ops.Relation]) -> None:
        key = (node, visible_relations)
        if key in seen:
            return
        seen.add(key)

        if isinstance(node, ops.Filter):
            current_relations = visible_relations | frozenset((node.parent,))

            for predicate in node.predicates:
                if any(rel not in current_relations for rel in predicate.relations):
                    raise UnsupportedSyntaxException(
                        "DSQL does not support using a derived table field as a scalar expression"
                    )

            walk(node.parent, visible_relations)
            walk_values(node.predicates, current_relations)
            return

        if isinstance(node, ops.Project):
            current_relations = visible_relations | frozenset((node.parent,))

            walk(node.parent, visible_relations)
            walk_values(node.values.values(), current_relations)
            return

        for argname in node.__argnames__:
            value = getattr(node, argname)

            if isinstance(value, ops.Node):
                walk(value, visible_relations)
            elif isinstance(value, tuple):
                walk_values(value, visible_relations)
            elif hasattr(value, "values"):
                walk_values(value.values(), visible_relations)

    walk(op, frozenset())
