import sqlglot
from sqlglot.tokens import Tokenizer
import sqlglot.expressions as expressions
import logging

logger = logging.getLogger(__name__)


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
        # set indentation
        indent_chars = " " * 4 * (indent_level + 1)
        col_sep = f"\n{indent_chars}{base_col_sep} "
        if exp is None:
            continue
        formatted_exp = ""
        logger.debug("current expression: %s", exp)

        # select clause
        if isinstance(exp, expressions.Select):
            formatted_exp = "SELECT"
            # add space for single column select
            if len(exp.named_selects) == 1:
                formatted_exp += " "
            # add newline for multiple column select with indent for first column
            if len(exp.named_selects) > 1:
                formatted_exp += f"\n{indent_chars}"
            formatted_exp += col_sep.join(col for col in exp.named_selects)

            # from clause
            from_clause = exp.args.get("from")
            if from_clause is not None and isinstance(from_clause, expressions.From):
                formatted_exp += f"\nFROM {from_clause.name}"

        # add ending e.g. semi-colon
        formatted_exp += expression_ending
        output.append(formatted_exp)
        del formatted_exp

    return "".join(output) + "\n"  # add newline at end of file
