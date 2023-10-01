from pathlib import Path

import pytest

from sqleaner.format import format_sql


class TestInOut:
    """
    Testing input and output on real files
    """

    input_file_base_path = Path(__file__).parent / "inputs"

    def _read_file(
        self, file_category: str, input_file: bool = False, output_file: bool = False
    ) -> str:
        if input_file == output_file and input_file is False:
            raise ValueError("Exactly 1 of input and output must be True")
        if input_file is True:
            target_file = "input.sql"
        if output_file is True:
            target_file = "output.sql"
        with open(
            self.input_file_base_path / file_category / target_file, encoding="utf-8"
        ) as file:
            return file.read()

    def read_input_file(self, file_category: str) -> str:
        return self._read_file(file_category=file_category, input_file=True)

    def read_output_file(self, file_category: str) -> str:
        return self._read_file(file_category=file_category, output_file=True)

    @pytest.mark.parametrize(
        argnames="file_category", argvalues=("single_col", "multiple_cols")
    )
    def test_formatting(self, file_category: str):
        input_str = self.read_input_file(file_category)
        expected_str = self.read_output_file(file_category)

        output_str = format_sql(input_str)

        assert output_str == expected_str
