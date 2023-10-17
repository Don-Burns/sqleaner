import logging
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Type, TypeGuard, TypeVar

import sqlglot
import sqlglot.expressions as expressions
from sqlglot.tokens import Tokenizer

logger = logging.getLogger(__name__)


class ExpressionType(Enum):
    DDL = [
        expressions.Create,
        expressions.AlterTable,
        expressions.AlterColumn,
        expressions.Drop,
    ]
    DML = [
        expressions.Select,
        expressions.Insert,
        expressions.Update,
        expressions.Delete,
    ]


@dataclass(slots=True)
class ColumnBlock:
    identifier: str
    alias: Optional[str] = None


def format_sql(sql_str: str) -> str:
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(sql_str)
    parser = sqlglot.Parser()
    parsed = parser.parse(tokens)
    output: list[str] = []
    base_col_sep = ","
    expression_ending = "\n;"
    indent_level = 0
    for exp in parsed:
        if exp is None:
            continue
        # set indentation
        indent_chars = " " * 4 * (indent_level + 1)
        col_sep = f"\n{indent_chars}{base_col_sep} "
        logger.debug("current expression: %s", exp)
        match exp:
            case _ if isinstance(exp, expressions.Select):
                formatted_exp = __format_select(exp, col_sep, indent_chars)
            case _:
                raise NotImplementedError(f"Expression handling not implemented: {exp}")

        # add ending e.g. semi-colon
        formatted_exp += expression_ending
        output.append(formatted_exp)
        del formatted_exp

    #     for node in exp.dfs():
    #         logger.debug("current node: %s", node)
    # dfs = [
    #     {"current": current, "previous": prev, "key": key}
    #     for current, prev, key in exp.dfs()
    # ]

    return "".join(output) + "\n"  # add newline at end of file


def __format_select(
    exp: expressions.Select, col_sep: str, indentation_chars: str
) -> str:
    """
    Func to take a select expression and format it into a string.

    Args:
        exp (expressions.Select): expression to format in AST form
        col_sep (str): column separator for cols in select statement
        indentation_chars (str): characters to use for indentation

    Returns:
        str: formatted string
    """
    formatted_exp = "SELECT"
    # add space for single column select
    if len(exp.named_selects) == 1:
        formatted_exp += " "
    # add newline for multiple column select with indent for first column
    if len(exp.named_selects) > 1:
        formatted_exp += f"\n{indentation_chars}"
    col_strings: list[str] = []
    for col in exp.selects:
        col_str = col.sql()
        col_strings.append(col_str)
    formatted_exp += col_sep.join((col for col in col_strings))

    # from clause
    from_clause = exp.args.get("from")
    if from_clause is not None and isinstance(from_clause, expressions.From):
        from_sql = from_clause.sql()
        formatted_exp += f"\n{from_sql}"

    # join clauses
    join_clauses = exp.args.get("joins")
    if join_clauses is not None and check_all_of_type(join_clauses, expressions.Join):
        joins: list[str] = []
        for join in join_clauses:
            join_sql = join.sql()
            joins.append(join_sql)
        join_str = "\n".join(joins)
        formatted_exp += f"\n{join_str}"

    return formatted_exp


T = TypeVar("T")


def check_all_of_type(iterable: Iterable[object], t: Type[T]) -> TypeGuard[Iterable[T]]:
    """
    To type check an iterable of objects and make sure they match a given type.

    Args:
        iterable (Iterable[object]): iterable of objects to type check
        t (Type[T]): type to check against

    Returns:
        TypeGuard[Iterable[T]]: True if all items in iterable are of type t else False
    """
    return all((isinstance(item, t) for item in iterable))
