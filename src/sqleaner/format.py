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


class ExpressionKey(Enum):
    """
    Keys returned when walking the AST.

    Attributes:
        EXPRESSIONS (str): Key for expressions, e.g. at the top level of a select statement or a column, means there is more data nested inside
        EXPRESSION (str): key for expression
        NONE (None): key for None
        TABLE (str): key for table, specialisation of `this` for table alias tokens
        THIS (str): key for this, means the current path has reached an end or is an identifier
        FROM (str): key for from, specialisation of `this` for from token
        ALIAS (str): key for alias, specialisation of `this` for alias token, e.g `AS t`
        JOINS (str): key for joins, like expressions but for joins specifically
            i.e. its nested
        WITH (str): key for with
        ON (str): key for on
    """

    EXPRESSIONS = "expressions"
    EXPRESSION = "expression"
    NONE = None
    TABLE = "table"
    THIS = "this"
    FROM = "from"
    ALIAS = "alias"
    JOINS = "joins"
    WITH = "with"
    ON = "on"


class ExpressionVisitor:
    def __init__(self, col_sep: str, indent_chars: str) -> None:
        self.col_sep = col_sep
        self.indent_chars = indent_chars
        self.visited_nodes: list[expressions.Expression] = []

    def visit_expression(self, exp: expressions.Expression) -> str:
        """
        Handle a node in the AST.
        If formatting the node, the formatted string is returned.
        Else an empty string is returned.
        Means that the caller can just append the return value to the output string
        while walking the ast.

        Args:
            exp (expressions.Expression):

        Returns:
            str: empty string if the node is not formatted/skipped, else the formatted sql string
        """
        sql = ""
        # if the node is too below a level we have already handled then skip it
        if self._skip_node(exp) is True:
            return ""

        # if the node gets formatted all its children will be too, so add them to the visited nodes
        sql = self.route_expression(exp)
        # only want the nodes added to the visited nodes if they are formatted
        # don't care about key or parent node (2nd and 3rd items in tuple)
        self.visited_nodes.extend([node for node, *_ in exp.dfs()])  # type: ignore [no-untyped-call]
        return sql

    def route_expression(self, exp: expressions.Expression) -> str:
        match exp:
            case _ if isinstance(exp, expressions.Select):
                formatted_exp = _format_select(exp, self.col_sep, self.indent_chars)
            case _:
                logger.warning(
                    "Expression handling not implemented: %s. Falling back to default formatting",
                    exp,
                )
                formatted_exp = exp.sql()
        return formatted_exp

    def _skip_node(self, node: expressions.Expression) -> bool:
        """
        Filter for the types of expressions to skip.

        Args:
            node (expressions.Expression):

        Returns:
            bool:
        """
        if node in self.visited_nodes:
            return True
        return False


def format_sql(sql_str: str) -> str:
    parsed = _parse_statement(sql_str)
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
        formatted_exp = ""
        logger.debug("current expression: (type: %s) %s", type(exp), exp)
        # TODO start using the walk/dfs methods to iterate over the AST instead of manually handling each expression type
        visitor = ExpressionVisitor(col_sep=col_sep, indent_chars=indent_chars)
        for node, parent_node, raw_key in exp.dfs():  # type: ignore [no-untyped-call]
            # narrow types from the walk
            if not isinstance(node, expressions.Expression):
                raise RuntimeError("Node is not an expression")
            if (
                not isinstance(parent_node, expressions.Expression)
                and parent_node is not None
            ):
                raise RuntimeError("Parent node is not an expression")
            try:
                key = ExpressionKey(raw_key)
            except ValueError:
                raise RuntimeError(f"{raw_key} is not a valid ExpressionKey")

            formatted_exp += visitor.visit_expression(node)

        # add ending e.g. semi-colon
        formatted_exp += expression_ending
        output.append(formatted_exp)
        # check the ast has not changes post formatting
        formatted_ast_expressions = _parse_statement(formatted_exp)
        if len(formatted_ast_expressions) != 1:
            raise RuntimeError(
                "Received multiple statements from parsing formatted AST"
            )
        formatted_ast = formatted_ast_expressions[0]
        if exp != formatted_ast:
            raise RuntimeError("AST has changed post formatting")
        del formatted_exp

    #     for node in exp.dfs():
    #         logger.debug("current node: %s", node)
    # dfs = [
    #     {"current": current, "previous": prev, "key": key}
    #     for current, prev, key in exp.dfs()
    # ]

    # join it all back to together and add newline to end of query
    return "".join(output) + "\n"


def _parse_statement(sql_str: str) -> list[expressions.Expression | None]:
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
    parsed = parser.parse(tokens)
    return parsed


def _format_select(
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
