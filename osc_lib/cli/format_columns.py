#   Copyright 2017 Huawei, Inc. All rights reserved.
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
#

"""Formattable column for specify content type"""

import typing as ty

from cliff import columns

from osc_lib import utils


class DictColumn(columns.FormattableColumn[dict[str, ty.Any]]):
    """Format column for dict content"""

    def human_readable(self) -> str:
        return utils.format_dict(self._value)

    def machine_readable(self) -> dict[str, ty.Any]:
        return dict(self._value or {})


class DictListColumn(columns.FormattableColumn[dict[str, list[ty.Any]]]):
    """Format column for dict, key is string, value is list"""

    def human_readable(self) -> str:
        return utils.format_dict_of_list(self._value) or ''

    def machine_readable(self) -> dict[str, list[ty.Any]]:
        return dict(self._value or {})


class ListColumn(columns.FormattableColumn[list[ty.Any]]):
    """Format column for list content"""

    def human_readable(self) -> str:
        return utils.format_list(self._value) or ''

    def machine_readable(self) -> list[ty.Any]:
        return [x for x in self._value or []]


class ListDictColumn(columns.FormattableColumn[list[dict[str, ty.Any]]]):
    """Format column for list of dict content"""

    def human_readable(self) -> str:
        return utils.format_list_of_dicts(self._value) or ''

    def machine_readable(self) -> list[dict[str, ty.Any]]:
        return [dict(x) for x in self._value or []]


class SizeColumn(columns.FormattableColumn[ty.Union[int, float]]):
    """Format column for file size content"""

    def human_readable(self) -> str:
        return utils.format_size(self._value)
