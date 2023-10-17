from enum import Enum
import sqlglot
from sqlglot.tokens import Tokenizer
import sqlglot.expressions as expressions
import logging

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
    formatted_exp += col_sep.join(col for col in exp.named_selects)

    # from clause
    from_clause = exp.args.get("from")
    if from_clause is not None and isinstance(from_clause, expressions.From):
        formatted_exp += f"\nFROM {from_clause.name}"

    return formatted_exp
