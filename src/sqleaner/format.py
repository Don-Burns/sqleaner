import logging
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Type, TypeGuard, TypeVar

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


def calc_indentation_chars(indent_level: int) -> str:
    return " " * 4 * (indent_level)


def calc_column_separator(indent_level: int, col_sep: str) -> str:
    return f"\n{calc_indentation_chars(indent_level)}{col_sep} "


def format_sql(sql_str: str) -> str:
    parsed = __parse_statement(sql_str)
    output: list[str] = []
    expression_ending = "\n;"
    for exp in parsed:
        if exp is None:
            continue
        # set indentation
        logger.debug("current expression: %s", exp)
        # TODO start using the walk/dfs methods to iterate over the AST instead of manually handling each expression type
        match exp:
            case _ if isinstance(exp, expressions.Select):
                formatted_exp = format_select_expression(exp)
            case _:
                raise NotImplementedError(f"Expression handling not implemented: {exp}")

        # add ending e.g. semi-colon
        formatted_exp += expression_ending
        output.append(formatted_exp)
        # check the ast has not changes post formatting
        formatted_ast_expressions = __parse_statement(formatted_exp)
        if len(formatted_ast_expressions) != 1:
            raise RuntimeError(
                "Received multiple statements from parsing formatted AST"
            )
        formatted_ast = formatted_ast_expressions[0]
        if exp != formatted_ast:
            raise RuntimeError("AST has changed post formatting")
        del formatted_exp

    # join it all back to together and add newline to end of query
    return "".join(output) + "\n"


def __parse_statement(sql_str: str) -> list[expressions.Expression | None]:
    """
    Func to parse a sql statement into an AST.

    Args:
        sql_str (str): sql statement to parse

    Returns:
        list[expressions.Expression | None]: sql AST
    """
    tokenizer = Tokenizer()
    tokens = tokenizer.tokenize(sql_str)
    parser = sqlglot.Parser()
    parsed = parser.parse(tokens, sql_str)
    return parsed


def format_select_expression(exp: expressions.Select) -> str:
    formatted_exp = ""
    ctes = exp.ctes
    column_separator = ","
    indent_level = 0
    if (
        ctes is not None
        # ensure ctes is list as expected
        and isinstance(ctes, list)
        and len(ctes) > 0
        # ensure ctes is a list of CTEs expressions
        and check_all_of_type(ctes, expressions.CTE)
    ):
        formatted_exp += f"{__with_statements(ctes, column_separator)}\n"
    formatted_exp += __format_select(exp, column_separator, indent_level)
    return formatted_exp


def __format_select(exp: expressions.Select, col_sep: str, indent_level: int) -> str:
    """
    Func to take a select expression and format it into a string.

    Args:
        exp (expressions.Select): expression to format in AST form
        col_sep (str): column separator for cols in select statement
        indent_level (int): indentation level for select statement

    Returns:
        str: formatted string
    """
    base_indent = calc_indentation_chars(indent_level)
    col_indent = calc_indentation_chars(indent_level + 1)
    col_sep = calc_column_separator(indent_level + 1, col_sep)
    formatted_exp = f"{base_indent}SELECT"
    # add space for single column select
    if len(exp.named_selects) == 1:
        formatted_exp += " "
    # add newline for multiple column select with indent for first column
    if len(exp.named_selects) > 1:
        formatted_exp += f"\n{col_indent}"
    col_strings: list[str] = []
    for col in exp.selects:
        col_str = col.sql()
        col_strings.append(col_str)
    formatted_exp += col_sep.join((col for col in col_strings))

    # from clause
    from_clause = exp.args.get("from")
    if from_clause is not None and isinstance(from_clause, expressions.From):
        from_sql = from_clause.sql()
        formatted_exp += f"\n{base_indent}{from_sql}"

    # join clauses
    join_clauses = exp.args.get("joins")
    if join_clauses is not None and check_all_of_type(join_clauses, expressions.Join):
        joins: list[str] = []
        for join in join_clauses:
            join_sql = join.sql()
            # add indent to each line
            join_sql = f"{base_indent}{join_sql}"
            joins.append(join_sql)
        join_str = "\n".join(joins)
        formatted_exp += f"\n{join_str}"

    return formatted_exp


def __with_statements(exps: Iterable[expressions.CTE], col_sep: str) -> str:
    """
    goal is statement like:
    ```
    WITH cte AS (
        ...
    ),
    cte2 AS (
        ...
    )
    ...


    Args:
        exps (Iterable[expressions.CTE]):
        col_sep (str): column separator for cols in select statement

    Returns:
        str: formatted ctes
    """
    # since all selects are within a set of brackets at least
    indent_level = 1

    formatted_exp = "WITH "
    formatted_ctes: list[str] = []
    for cte in exps:
        # target = `cte AS (...)`
        # build line with alias + opening bracket
        opening_clause = cte.alias + " AS ("
        # format the select within brackets
        select_statement = __format_select(
            cte.this,
            col_sep=col_sep,
            indent_level=indent_level,
        )
        # close brackets
        closing_clause = ")"
        formatted_cte = f"{opening_clause}\n{select_statement}\n{closing_clause}"
        formatted_ctes.append(formatted_cte)

    formatted_exp += ",\n".join(formatted_ctes)
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
