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

from osc_lib.test.base import TestCase, TestCommand
from osc_lib.test.fakes import (
    AUTH_URL,
    INTERFACE,
    IDENTITY_API_VERSION as VERSION,
    PASSWORD,
    PROJECT_ID,
    PROJECT_NAME,
    REGION_NAME,
    TOKEN as AUTH_TOKEN,
    USERNAME,
    USER_ID,
    FakeApp,
    FakeClientManager,
    FakeLog,
    FakeModule,
    FakeOptions,
    FakeResource,
    FakeStdout,
)
from osc_lib.tests.test_clientmanager import (
    SERVICE_PROVIDER_ID,
    TEST_RESPONSE_DICT,
    TEST_RESPONSE_DICT_V3,
    TEST_VERSIONS,
)

__all__ = [
    'AUTH_TOKEN',
    'AUTH_URL',
    'FakeApp',
    'FakeClientManager',
    'FakeLog',
    'FakeModule',
    'FakeOptions',
    'FakeResource',
    'FakeStdout',
    'INTERFACE',
    'PASSWORD',
    'PROJECT_ID',
    'PROJECT_NAME',
    'REGION_NAME',
    'SERVICE_PROVIDER_ID',
    'TEST_RESPONSE_DICT',
    'TEST_RESPONSE_DICT_V3',
    'TEST_VERSIONS',
    'TestCase',
    'TestCommand',
    'to_unicode_dict',
    'USER_ID',
    'USERNAME',
    'VERSION',
]


warnings.warn(
    "The osc_lib.tests.fakes module is deprecated for removal and should not "
    "be used externally. Use the osc_lib.test module instead, which provides "
    "a public API.",
    DeprecationWarning,
)


# NOTE(stephenfin): This isn't moved since it's unused now. We can delete it in
# the future.
def to_unicode_dict(catalog_dict):
    """Converts dict to unicode dict"""
    if isinstance(catalog_dict, dict):
        return {
            to_unicode_dict(key): to_unicode_dict(value)
            for key, value in catalog_dict.items()
        }
    elif isinstance(catalog_dict, list):
        return [to_unicode_dict(element) for element in catalog_dict]
    elif isinstance(catalog_dict, str):
        return catalog_dict + ""
    else:
        return catalog_dict
