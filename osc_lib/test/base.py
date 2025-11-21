# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import argparse
from collections.abc import Sequence
import os
from typing import Any
from unittest import mock

from cliff import columns as cliff_columns
from cliff import command as cliff_command
import fixtures
import testtools  # type: ignore

from osc_lib.test import fakes


class ParserException(Exception):
    pass


class TestCase(testtools.TestCase):  # type: ignore
    # provide additional context for failures
    maxDiff = None

    def setUp(self) -> None:
        super().setUp()

        if (
            os.environ.get("OS_STDOUT_CAPTURE") == "True"
            or os.environ.get("OS_STDOUT_CAPTURE") == "1"
        ):
            stdout = self.useFixture(fixtures.StringStream("stdout")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stdout", stdout))

        if (
            os.environ.get("OS_STDERR_CAPTURE") == "True"
            or os.environ.get("OS_STDERR_CAPTURE") == "1"
        ):
            stderr = self.useFixture(fixtures.StringStream("stderr")).stream
            self.useFixture(fixtures.MonkeyPatch("sys.stderr", stderr))

    def assertNotCalled(self, m: mock.Mock, msg: str | None = None) -> None:
        """Assert a function was not called"""
        if m.called:
            if not msg:
                msg = f'method {m} should not have been called'
            self.fail(msg)


class TestCommand(TestCase):
    """Test cliff command classes"""

    def setUp(self) -> None:
        super().setUp()
        # Build up a fake app
        self.fake_stdout = fakes.FakeStdout()
        self.fake_log = fakes.FakeLog()
        self.app = fakes.FakeApp(self.fake_stdout, self.fake_log)
        self.app.client_manager = fakes.FakeClientManager()

    def check_parser(
        self,
        cmd: cliff_command.Command,
        args: list[str],
        verify_args: list[tuple[str, Any]],
    ) -> argparse.Namespace:
        cmd_parser = cmd.get_parser('check_parser')
        try:
            parsed_args = cmd_parser.parse_args(args)
        except SystemExit:
            raise ParserException("Argument parse failed")
        for av in verify_args:
            attr, value = av
            if attr:
                self.assertIn(attr, parsed_args)
                self.assertEqual(value, getattr(parsed_args, attr))
        return parsed_args

    def assertItemEqual(
        self, expected: Sequence[Any], actual: Sequence[Any]
    ) -> None:
        """Compare item considering formattable columns.

        This method compares an observed item to an expected item column by
        column. If a column is a formattable column, observed and expected
        columns are compared using human_readable() and machine_readable().
        """
        self.assertEqual(len(expected), len(actual))
        for col_expected, col_actual in zip(expected, actual):
            if isinstance(col_expected, cliff_columns.FormattableColumn):
                self.assertIsInstance(col_actual, col_expected.__class__)
                self.assertEqual(
                    col_expected.human_readable(), col_actual.human_readable()
                )
                self.assertEqual(
                    col_expected.machine_readable(),
                    col_actual.machine_readable(),
                )
            else:
                self.assertEqual(col_expected, col_actual)

    def assertListItemEqual(
        self, expected: Sequence[Any], actual: Sequence[Any]
    ) -> None:
        """Compare a list of items considering formattable columns.

        Each pair of observed and expected items are compared
        using assertItemEqual() method.
        """
        self.assertEqual(len(expected), len(actual))
        for item_expected, item_actual in zip(expected, actual):
            self.assertItemEqual(item_expected, item_actual)
