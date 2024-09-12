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

import collections

from osc_lib.cli import format_columns
from osc_lib.tests import utils


class TestDictColumn(utils.TestCase):
    def test_dict_column(self):
        data = {
            'key1': 'value1',
            'key2': 'value2',
        }
        col = format_columns.DictColumn(data)
        self.assertEqual(data, col.machine_readable())
        self.assertEqual("key1='value1', key2='value2'", col.human_readable())

    def test_complex_object(self):
        """Non-dict objects should be converted to a dict."""
        data = collections.OrderedDict(
            [('key1', 'value1'), ('key2', 'value2')]
        )
        col = format_columns.DictColumn(data)
        # we explicitly check type rather than use isinstance since an
        # OrderedDict is a subclass of dict and would inadvertently pass
        self.assertEqual(type(col.machine_readable()), dict)


class TestDictListColumn(utils.TestCase):
    def test_dict_list_column(self):
        data = {
            'public': ['2001:db8::8', '172.24.4.6'],
            'private': ['2000:db7::7', '192.24.4.6'],
        }
        col = format_columns.DictListColumn(data)
        self.assertEqual(data, col.machine_readable())
        self.assertEqual(
            'private=192.24.4.6, 2000:db7::7; public=172.24.4.6, 2001:db8::8',
            col.human_readable(),
        )

    def test_complex_object(self):
        """Non-dict-of-list objects should be converted to a dict-of-lists."""
        data = collections.OrderedDict(
            [('key1', ['value1']), ('key2', ['value2'])],
        )
        col = format_columns.DictListColumn(data)
        # we explicitly check type rather than use isinstance since an
        # OrderedDict is a subclass of dict and would inadvertently pass
        self.assertEqual(type(col.machine_readable()), dict)


class TestListColumn(utils.TestCase):
    def test_list_column(self):
        data = [
            'key1',
            'key2',
        ]
        col = format_columns.ListColumn(data)
        self.assertEqual(data, col.machine_readable())
        self.assertEqual("key1, key2", col.human_readable())

    def test_complex_object(self):
        """Non-list objects should be converted to a list."""
        data = {'key1', 'key2'}
        col = format_columns.ListColumn(data)
        # we explicitly check type rather than use isinstance since an
        # OrderedDict is a subclass of dict and would inadvertently pass
        self.assertEqual(type(col.machine_readable()), list)


class TestListDictColumn(utils.TestCase):
    def test_list_dict_column(self):
        data = [
            {'key1': 'value1'},
            {'key2': 'value2'},
        ]
        col = format_columns.ListDictColumn(data)
        self.assertEqual(data, col.machine_readable())
        self.assertEqual("key1='value1'\nkey2='value2'", col.human_readable())

    def test_complex_object(self):
        """Non-list-of-dict objects should be converted to a list-of-dicts."""
        # not actually a list (which is the point)
        data = (
            collections.OrderedDict([('key1', 'value1'), ('key2', 'value2')]),
        )
        col = format_columns.ListDictColumn(data)
        # we explicitly check type rather than use isinstance since an
        # OrderedDict is a subclass of dict and would inadvertently pass
        self.assertEqual(type(col.machine_readable()), list)  # noqa: H212
        for x in col.machine_readable():
            self.assertEqual(type(x), dict)  # noqa: H211


class TestSizeColumn(utils.TestCase):
    def test_size_column(self):
        content = 1576395005
        col = format_columns.SizeColumn(content)
        self.assertEqual(content, col.machine_readable())
        self.assertEqual('1.6G', col.human_readable())
