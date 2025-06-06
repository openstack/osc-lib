#   Copyright 2013 OpenStack Foundation
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

"""argparse Custom Actions"""

import argparse
import collections.abc
import typing as ty

from osc_lib.i18n import _

_T = ty.TypeVar('_T')


class KeyValueAction(argparse.Action):
    """A custom action to parse arguments as key=value pairs

    Ensures that ``dest`` is a dict and values are strings.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            raise TypeError('expected str')

        # Make sure we have an empty dict rather than None
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, {})

        # Add value if an assignment else remove it
        if '=' in values:
            values_list = values.split('=', 1)
            # NOTE(qtang): Prevent null key setting in property
            if '' == values_list[0]:
                msg = _("Property key must be specified: %s")
                raise argparse.ArgumentError(self, msg % str(values))
            else:
                getattr(namespace, self.dest, {}).update(dict([values_list]))
        else:
            msg = _("Expected 'key=value' type, but got: %s")
            raise argparse.ArgumentError(self, msg % str(values))


class KeyValueAppendAction(argparse.Action):
    """A custom action to parse arguments as key=value pairs

    Ensures that ``dest`` is a dict and values are lists of strings.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            raise TypeError('expected str')

        # Make sure we have an empty dict rather than None
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, {})

        # Add value if an assignment else remove it
        if '=' in values:
            key, value = values.split('=', 1)
            # NOTE(qtang): Prevent null key setting in property
            if '' == key:
                msg = _("Property key must be specified: %s")
                raise argparse.ArgumentError(self, msg % str(values))

            dest = getattr(namespace, self.dest)
            if key in dest:
                dest[key].append(value)
            else:
                dest[key] = [value]
        else:
            msg = _("Expected 'key=value' type, but got: %s")
            raise argparse.ArgumentError(self, msg % str(values))


class MultiKeyValueAction(argparse.Action):
    """A custom action to parse arguments as key1=value1,key2=value2 pairs

    Ensure that ``dest`` is a list. The list will finally contain multiple
    dicts, with key=value pairs in them.

    NOTE: The arguments string should be a comma separated key-value pairs.
    And comma(',') and equal('=') may not be used in the key or value.
    """

    def __init__(
        self,
        option_strings: ty.Sequence[str],
        dest: str,
        nargs: int | str | None = None,
        required_keys: ty.Sequence[str] | None = None,
        optional_keys: ty.Sequence[str] | None = None,
        const: _T | None = None,
        default: _T | str | None = None,
        type: collections.abc.Callable[[str], _T] | None = None,
        choices: collections.abc.Iterable[_T] | None = None,
        required: bool = False,
        help: str | None = None,
        metavar: str | tuple[str, ...] | None = None,
    ) -> None:
        """Initialize the action object, and parse customized options

        Required keys and optional keys can be specified when initializing
        the action to enable the key validation. If none of them specified,
        the key validation will be skipped.

        :param required_keys: a list of required keys
        :param optional_keys: a list of optional keys
        """
        if nargs:
            msg = _("Parameter 'nargs' is not allowed, but got %s")
            raise ValueError(msg % nargs)

        super().__init__(
            option_strings,
            dest,
            nargs=nargs,
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

        # required_keys: A list of keys that is required. None by default.
        if required_keys and not isinstance(required_keys, list):
            msg = _("'required_keys' must be a list")
            raise TypeError(msg)

        self.required_keys = set(required_keys or [])

        # optional_keys: A list of keys that is optional. None by default.
        if optional_keys and not isinstance(optional_keys, list):
            msg = _("'optional_keys' must be a list")
            raise TypeError(msg)
        self.optional_keys = set(optional_keys or [])

    def validate_keys(self, keys: ty.Sequence[str]) -> None:
        """Validate the provided keys.

        :param keys: A list of keys to validate.
        """
        # Check key validation
        valid_keys = self.required_keys | self.optional_keys
        if valid_keys:
            invalid_keys = [k for k in keys if k not in valid_keys]
            if invalid_keys:
                msg = _(
                    "Invalid keys %(invalid_keys)s specified.\n"
                    "Valid keys are: %(valid_keys)s"
                )
                raise argparse.ArgumentError(
                    self,
                    msg
                    % {
                        'invalid_keys': ', '.join(invalid_keys),
                        'valid_keys': ', '.join(valid_keys),
                    },
                )

        if self.required_keys:
            missing_keys = [k for k in self.required_keys if k not in keys]
            if missing_keys:
                msg = _(
                    "Missing required keys %(missing_keys)s.\n"
                    "Required keys are: %(required_keys)s"
                )
                raise argparse.ArgumentError(
                    self,
                    msg
                    % {
                        'missing_keys': ', '.join(missing_keys),
                        'required_keys': ', '.join(self.required_keys),
                    },
                )

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            raise TypeError('expected str')

        # Make sure we have an empty list rather than None
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, [])

        params: dict[str, str] = {}
        for kv in values.split(','):
            # Add value if an assignment else raise ArgumentError
            if '=' in kv:
                kv_list = kv.split('=', 1)
                # NOTE(qtang): Prevent null key setting in property
                if '' == kv_list[0]:
                    msg = _("Each property key must be specified: %s")
                    raise argparse.ArgumentError(self, msg % str(kv))
                else:
                    params.update(dict([kv_list]))
            else:
                msg = _(
                    "Expected comma separated 'key=value' pairs, but got: %s"
                )
                raise argparse.ArgumentError(self, msg % str(kv))

        # Check key validation
        self.validate_keys(list(params))

        # Update the dest dict
        getattr(namespace, self.dest, []).append(params)


class MultiKeyValueCommaAction(MultiKeyValueAction):
    """Custom action to parse arguments from a set of key=value pair

    Ensures that ``dest`` is a dict.
    Parses dict by separating comma separated string into individual values
    Ex. key1=val1,val2,key2=val3 => {"key1": "val1,val2", "key2": "val3"}
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        """Overwrite the __call__ function of MultiKeyValueAction

        This is done to handle scenarios where we may have comma seperated
        data as a single value.
        """
        if not isinstance(values, str):
            msg = _("Invalid key=value pair, non-string value provided: %s")
            raise argparse.ArgumentError(self, msg % str(values))

        # Make sure we have an empty list rather than None
        if getattr(namespace, self.dest, None) is None:
            setattr(namespace, self.dest, [])

        params: dict[str, str] = {}
        key = ''
        for kv in values.split(','):
            # Add value if an assignment else raise ArgumentError
            if '=' in kv:
                kv_list = kv.split('=', 1)
                # NOTE(qtang): Prevent null key setting in property
                if '' == kv_list[0]:
                    msg = _("A key must be specified before '=': %s")
                    raise argparse.ArgumentError(self, msg % str(kv))
                else:
                    params.update(dict([kv_list]))
                key = kv_list[0]
            else:
                # If the ',' split does not have key=value pair, then it
                # means the current value is a part of the previous
                # key=value pair, so append it.
                try:
                    params[key] = f"{params[key]},{kv}"
                except KeyError:
                    msg = _("A key=value pair is required: %s")
                    raise argparse.ArgumentError(self, msg % str(kv))

        # Check key validation
        self.validate_keys(list(params))

        # Update the dest dict
        getattr(namespace, self.dest, []).append(params)


class RangeAction(argparse.Action):
    """A custom action to parse a single value or a range of values

    Parses single integer values or a range of integer values delimited
    by a colon and returns a tuple of integers:
    '4' sets ``dest`` to (4, 4)
    '6:9' sets ``dest`` to (6, 9)
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str):
            msg = _("Invalid range, non-string value provided")
            raise argparse.ArgumentError(self, msg)

        range = values.split(':')
        if len(range) == 0:
            # Nothing passed, return a zero default
            setattr(namespace, self.dest, (0, 0))
        elif len(range) == 1:
            # Only a single value is present
            setattr(namespace, self.dest, (int(range[0]), int(range[0])))
        elif len(range) == 2:
            # Range of two values
            if int(range[0]) <= int(range[1]):
                setattr(namespace, self.dest, (int(range[0]), int(range[1])))
            else:
                msg = _("Invalid range, %(min)s is not less than %(max)s")
                raise argparse.ArgumentError(
                    self,
                    msg
                    % {
                        'min': range[0],
                        'max': range[1],
                    },
                )
        else:
            # Too many values
            msg = _("Invalid range, too many values")
            raise argparse.ArgumentError(self, msg)


class NonNegativeAction(argparse.Action):
    """A custom action to check whether the value is non-negative or not

    Ensures the value is >= 0.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | ty.Sequence[ty.Any] | None,
        option_string: str | None = None,
    ) -> None:
        if not isinstance(values, str | int | float):
            msg = _("%s expected a non-negative integer")
            raise argparse.ArgumentError(self, msg % str(option_string))

        if int(values) >= 0:
            setattr(namespace, self.dest, values)
        else:
            msg = _("%s expected a non-negative integer")
            raise argparse.ArgumentError(self, msg % str(option_string))
