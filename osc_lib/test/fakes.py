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

from collections.abc import Iterable, Mapping
import json
import sys
from typing import Any, Protocol
from unittest import mock

import requests

AUTH_URL = "https://example.com/identity"
USERNAME = 'itchy'
USER_ID = '2354b7c1-f681-4c39-8003-4fe9d1eabb65'
PASSWORD = 'scratchy'  # noqa: S105
PROJECT_NAME = 'poochie'
PROJECT_ID = '30c3da29-61f5-4b7b-8eb2-3d18287428c7'
REGION_NAME = 'richie'
INTERFACE = 'catchy'
TOKEN = 'foobar'  # noqa: S105
IDENTITY_API_VERSION = '3'


class FakeStdout:
    def __init__(self) -> None:
        self.content: list[str] = []

    def write(self, text: str) -> None:
        self.content.append(text)

    def make_string(self) -> str:
        result = ''
        for line in self.content:
            result = result + line
        return result


# TODO(stephenfin): Replace with io.Writer when Python 3.14 is our minimum
# supported version
class IOWriterProtocol(Protocol):
    def write(self, text: str) -> None: ...


class LoggerProtocol(Protocol):
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None: ...

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None: ...


class FakeLog:
    def __init__(self) -> None:
        self.messages: dict[str, str] = {}

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages['debug'] = msg

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages['info'] = msg

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages['warning'] = msg

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages['error'] = msg

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.messages['critical'] = msg


class FakeApp:
    client_manager: 'FakeClientManager'

    def __init__(self, _stdout: IOWriterProtocol, _log: LoggerProtocol):
        self.api_version: dict[str, str] = {}
        self.stdin = sys.stdin
        self.stdout = _stdout or sys.stdout
        self.stderr = sys.stderr
        self.log = _log


class FakeOptions:
    def __init__(self, **kwargs: Any) -> None:
        self.os_beta_command = False


class FakeClientManager:
    def __init__(self) -> None:
        self.compute = None
        self.identity = None
        self.image = None
        self.object_store = None
        self.volume = None
        self.network = None
        self.sdk_connection = mock.Mock()

        self.session = None
        self.auth_ref = None
        self.auth_plugin_name = None

    def get_configuration(self) -> dict[str, Any]:
        return {
            'auth': {
                'username': USERNAME,
                'password': PASSWORD,
                'token': TOKEN,
            },
            'region': REGION_NAME,
            'identity_api_version': IDENTITY_API_VERSION,
        }


class FakeModule:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.__version__ = version
        # Workaround for openstacksdk case
        self.version = mock.Mock()
        self.version.__version__ = version


class FakeResource:
    def __init__(
        self,
        manager: Any = None,
        info: dict[str, Any] | None = None,
        loaded: bool = False,
        methods: dict[str, Any] | None = None,
    ) -> None:
        """Set attributes and methods for a resource.

        :param manager: The resource manager
        :param info: A dictionary with all attributes
        :param loaded: True if the resource is loaded in memory
        :param methods: A dictionary with all methods
        """
        info = info or {}
        methods = methods or {}

        self.__name__ = type(self).__name__
        self.manager = manager
        self._info = info
        self._add_details(info)
        self._add_methods(methods)
        self._loaded = loaded

    def _add_details(self, info: dict[str, Any]) -> None:
        for k, v in info.items():
            setattr(self, k, v)

    def _add_methods(self, methods: dict[str, Any]) -> None:
        """Fake methods with MagicMock objects.

        For each <@key, @value> pairs in methods, add an callable MagicMock
        object named @key as an attribute, and set the mock's return_value to
        @value. When users access the attribute with (), @value will be
        returned, which looks like a function call.
        """
        for name, ret in methods.items():
            method = mock.MagicMock(return_value=ret)
            setattr(self, name, method)

    def __repr__(self) -> str:
        reprkeys = sorted(
            k for k in self.__dict__.keys() if k[0] != '_' and k != 'manager'
        )
        info = ", ".join(f"{k}={getattr(self, k)}" for k in reprkeys)
        return f"<{self.__class__.__name__} {info}>"

    def keys(self) -> Iterable[str]:
        return self._info.keys()

    def to_dict(self) -> dict[str, Any]:
        return self._info

    @property
    def info(self) -> dict[str, Any]:
        return self._info

    def __getitem__(self, item: str) -> Any:
        return self._info.get(item)

    def get(self, item: str, default: Any = None) -> Any:
        return self._info.get(item, default)

    def pop(self, key: str, default_value: Any = None) -> Any:
        return self.info.pop(key, default_value)


class FakeResponse(requests.Response):
    def __init__(
        self,
        headers: Mapping[str, str] | None = None,
        status_code: int = 200,
        data: object | None = None,
        encoding: type[str] | type[bytes] | None = None,
    ) -> None:
        super().__init__()

        headers = headers or {}

        self.status_code = status_code

        self.headers.update(headers)
        self._content = json.dumps(data).encode()
