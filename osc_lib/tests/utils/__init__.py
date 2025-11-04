#   Copyright 2012-2013 OpenStack Foundation
#   Copyright 2013 Nebula Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import warnings

from osc_lib.test.base import ParserException, TestCase, TestCommand
from osc_lib.tests.test_clientmanager import (
    BaseTestClientManager as TestClientManager,
)
from osc_lib.tests.test_shell import (
    fake_execute,
    make_shell,
    opt2attr,
    opt2env,
    TestShell,
    EnvFixture,
)

__all__ = [
    'fake_execute',
    'make_shell',
    'opt2attr',
    'opt2env',
    'EnvFixture',
    'ParserException',
    'TestCase',
    'TestClientManager',
    'TestCommand',
    'TestShell',
]

warnings.warn(
    "The osc_lib.tests.utils module is deprecated for removal and should not "
    "be used externally. Use the osc_lib.test module instead, which provides "
    "a public API.",
    DeprecationWarning,
)
