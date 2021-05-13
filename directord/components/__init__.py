#   Copyright Peznauts <kevin@cloudnull.com>. All Rights Reserved.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

import argparse

import jinja2

import directord
from directord import utils


class ComponentBase(object):
    def __init__(self, desc=None):
        self.desc = desc
        self.log = directord.getLogger(name="directord")
        self.known_args, self.unknown_args = None, None
        self.blueprint = jinja2.Environment(loader=jinja2.BaseLoader())

    @staticmethod
    def sanitized_args(execute):
        """Return arguments in a flattened array.

        This will inspect the execution arguments and return everything found
        as a flattened array.

        :param execute: Execution string to parse.
        :type execute: String
        :returns: List
        """

        return [i for g in execute for i in g.split()]

    def exec_parser(self, parser, exec_string, arg_vars=None):
        """Run the parser and return parsed arguments.

        :param parser: Argument parser.
        :type parser: Object
        :param exec_string: Inpute string from action
        :type exec_string: String
        :param arg_vars: Pre-Formatted arguments
        :type arg_vars: Dictionary
        :returns: Tuple
        """

        self.known_args, self.unknown_args = parser.parse_known_args(
            self.sanitized_args(execute=exec_string)
        )
        if hasattr(self.known_args, "exec_help") and self.known_args.exec_help:
            raise SystemExit(parser.print_help())
        else:
            if arg_vars:
                for key, value in arg_vars.items():
                    self.known_args.__dict__[key] = value
            return self.known_args, self.unknown_args

    def args(self):
        """Set default arguments for a component."""

        self.parser = argparse.ArgumentParser(
            description=self.desc,
            allow_abbrev=False,
            add_help=False,
        )
        self.parser.add_argument(
            "--exec-help",
            action="help",
            help="Show this execution help message.",
        )
        self.parser.add_argument(
            "--skip-cache",
            action="store_true",
            help="For a task to skip the on client cache.",
        )
        self.parser.add_argument(
            "--run-once",
            action="store_true",
            help="Force a given task to run once.",
        )
        self.parser.add_argument(
            "--timeout",
            default=600,
            type=int,
            help="Set the action timeout. Default %(default)s.",
        )

    @staticmethod
    def set_cache(
        cache, key, value, value_update=False, expire=28800, tag=None
    ):
        """Set a cached item.

        :param cache: Cached access object.
        :type cache: Object
        :param key: Key for the cached item.
        :type key: String
        :param value: Value for the cached item.
        :type value: ANY
        :param value_update: Instructs the method to update a Dictionary with
                             another dictionary.
        :type value_update: Boolean
        :param expire: Sets the expire time, defaults to 12 hours.
        :type expire: Integer
        :param tag: Sets the index for a given cached item.
        :type tag: String
        """

        if value_update:
            orig = cache.pop(key, default=dict())
            value = utils.merge_dict(orig, value)

        cache.set(key, value, tag=tag, expire=expire)

    def file_blueprinter(self, cache, file_to):
        """Read a file and blueprint its contents.

        :param cache: Cached access object.
        :type cache: Object
        :param file_to: String path to a file which will blueprint.
        :type file_to: String
        :returns: Boolean
        """

        try:
            with open(file_to) as f:
                file_contents = self.blueprinter(
                    content=f.read(), values=cache.get("args")
                )
                if not file_contents:
                    return False

            with open(file_to, "w") as f:
                f.write(file_contents)
        except Exception as e:
            self.log.critical("File blueprint failure: %s", str(e))
            return False
        else:
            self.log.info("File %s has been blueprinted.", file_to)
            return True

    def blueprinter(self, content, values):
        """Return blue printed content.

        :param content: A string item that will be interpreted and blueprinted.
        :type content: String
        :param values: Dictionary items that will be used to render a
                       blueprinted item.
        :type values: Dictionary
        :returns: String | None
        """

        if values:
            try:
                _contents = self.blueprint.from_string(content)
                rendered_content = _contents.render(**values)
            except Exception as e:
                self.log.critical(
                    "blueprint failure: %s values: %s", str(e), values
                )
                return
            else:
                return rendered_content
        else:
            return content

    def parser_error(self):
        """Return parser help information."""

        return self.parser.print_help()

    def server(self, exec_string, data, arg_vars):
        """Server operation.

        :param exec_string: Inpute string from action
        :type exec_string: String
        :param data: Formatted data hash
        :type data: Dictionary
        :returns: Dictionary
        """

        self.args()
        self.exec_parser(
            parser=self.parser, exec_string=exec_string, arg_vars=arg_vars
        )

    def client(self, conn, cache, job):
        """Client operation.

        Command operations are rendered with cached data from the args dict.

        :param conn: Connection object used to store information used in a
                     return message.
        :type conn: Object
        :param cache: Caching object used to template items within a command.
        :type cache: Object
        :param job: Information containing the original job specification.
        :type job: Dictionary
        """

        pass

    def close(self):
        """Close a component."""

        pass

    def __enter__(self):
        """Return self when using a component as a context manager."""

        return self

    def __exit__(self, *args, **kwargs):
        """Exit the context manager and close."""

        self.close()
