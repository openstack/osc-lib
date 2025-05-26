#   Copyright 2016 NEC Corporation
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

import abc
import argparse
import logging
import typing as ty

from cliff import command
from cliff import lister
from cliff import show

from osc_lib import exceptions
from osc_lib.i18n import _


class CommandMeta(abc.ABCMeta):
    def __new__(
        mcs: type['CommandMeta'],
        name: str,
        bases: tuple[type[ty.Any], ...],
        namespace: dict[str, ty.Any],
    ) -> 'CommandMeta':
        if 'log' not in namespace:
            namespace['log'] = logging.getLogger(
                namespace['__module__'] + '.' + name
            )
        return super().__new__(mcs, name, bases, namespace)


class Command(command.Command, metaclass=CommandMeta):
    log: logging.Logger

    def run(self, parsed_args: argparse.Namespace) -> int:
        self.log.debug('run(%s)', parsed_args)
        return super().run(parsed_args)

    def validate_os_beta_command_enabled(self) -> None:
        if not self.app.options.os_beta_command:
            msg = _(
                'Caution: This is a beta command and subject to '
                'change. Use global option --os-beta-command '
                'to enable this command.'
            )
            raise exceptions.CommandError(msg)

    def deprecated_option_warning(
        self, old_option: str, new_option: str
    ) -> None:
        """Emit a warning for use of a deprecated option"""
        self.log.warning(
            _("The %(old)s option is deprecated, please use %(new)s instead.")
            % {'old': old_option, 'new': new_option}
        )


class Lister(Command, lister.Lister):
    pass


class ShowOne(Command, show.ShowOne):
    pass
