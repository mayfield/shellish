"""
The merger of argparse and cmd goes here.  This holds the main base class
used by all commands.
"""

import collections
import functools
import inspect
import itertools
import re
import shlex
from . import supplement
from .. import completer, layout, eventing, session, paging


def parse_docstring(entity):
    """ Return sanitized docstring from an entity.  The first line of the
    docstring is the title, and remaining lines are the details, aka git
    style. """
    doc = inspect.getdoc(entity)
    if not doc:
        return None, None
    doc = [x.strip() for x in doc.splitlines()]
    if not doc[0]:
        doc.pop(0)
    title = (doc and doc.pop(0)) or None
    if doc and not doc[0]:
        doc.pop(0)
    desc = '\n'.join(doc) or None
    return title, desc


class Command(eventing.Eventer):
    """ The primary encapsulation for a shellish command.  Each command or
    subcommand should be an instance of this class.  The docstring for sub-
    classes is used in --help output for this command. """

    name = None
    title = None
    desc = None
    use_pager = False
    ArgumentParser = supplement.ShellishParser
    ArgumentFormatter = supplement.VTMLHelpFormatter
    Session = session.Session
    completion_excludes = {'--help'}
    arg_label_fmt = '__command[%d]__'
    env_scrub_re = '[^\w\s\-_]'  # chars scrubed from env vars
    env_flatten_re = '[\s\-_]+'  # chars converted to underscores

    def setup_args(self, parser):
        """ Subclasses should provide any setup for their parsers here. """
        pass

    def prerun(self, args):
        """ Hook to do something prior to invocation. """
        pass

    def postrun(self, args, result=None, exc=None):
        """ Hook to do something following invocation. """
        pass

    def run(self, args):
        """ Primary entry point for command exec. """
        self.argparser.print_help()
        raise SystemExit(1)

    def __init__(self, parent=None, title=None, desc=None, name=None, run=None,
                 prerun=None, postrun=None, **context):
        self.add_events(['prerun', 'postrun', 'setup_args', 'precomplete',
                         'postcomplete'])
        if name:
            self.name = name
        if self.name is None:
            raise RuntimeError("Command missing `name` attribute")
        if type(self) is not Command:
            alt_title, alt_desc = parse_docstring(self)
        else:
            alt_title, alt_desc = None, None
        if not self.title or title:
            self.title = title or alt_title
        if not self.desc or desc:
            self.desc = desc or alt_desc
        if run is not None:
            self.run = run
        if prerun is not None:
            self.prerun = prerun
        if postrun is not None:
            self.postrun = postrun
        self.subcommands = collections.OrderedDict()
        self.default_subcommand = None
        self.session = None
        self.context_keys = set()
        self._autoenv_actions = set()
        self.inject_context(context)
        self.subparsers = None
        self.argparser = self.create_argparser()
        self.parent = parent
        self.setup_args(self.argparser)
        self.fire_event('setup_args', self.argparser)

    def get_or_create_session(self):
        if self.session is None:
            self.attach_session()
        return self.session

    def parse_args(self, argv=None):
        """ Return an argparse.Namespace of the argv string or sys.argv if
        argv is None. """
        arg_input = shlex.split(argv) if argv is not None else None
        self.get_or_create_session()
        return self.argparser.parse_args(arg_input)

    def __call__(self, args=None, argv=None):
        """ If a subparser is present and configured  we forward invocation to
        the correct subcommand method. If all else fails we call run(). """
        session = self.get_or_create_session()
        if args is None:
            args = self.parse_args(argv)
        commands = self.get_commands_from(args)
        if self.subparsers:
            try:
                command = commands[self.depth]
            except IndexError:
                pass
            else:
                return command(args)
            if self.default_subcommand:
                parser = self.default_subcommand.argparser
                parser.parse_args([], namespace=args)
                return self(args)  # retry
        return session.execute(self, args)

    def __getitem__(self, item):
        return self.subcommands[item]

    def get_pager_spec(self):
        """ Find the best pager settings for this command.  If the user has
        specified overrides in the INI config file we prefer those. """
        self_config = self.get_config()
        pagercmd = self_config.get('pager')
        istty = self_config.getboolean('pager_istty')
        core_config = self.get_config('core')
        if pagercmd is None:
            pagercmd = core_config.get('pager')
        if istty is None:
            istty = core_config.get('pager_istty')
        return {
            "pagercmd": pagercmd,
            "istty": istty
        }

    def run_wrap(self, args):
        """ Wrap some standard protocol around a command's run method.  This
        wrapper should generally never capture exceptions.  It can look at
        them and do things but prerun and postrun should always be symmetric.
        Any exception suppression should happen in the `session.execute`. """
        self.fire_event('prerun', args)
        self.prerun(args)
        try:
            if self.session.allow_pager and self.use_pager:
                desc = 'Command\: %s' % '-'.join(self.prog.split())
                with paging.pager_redirect(desc, **self.get_pager_spec()):
                    result = self.run(args)
            else:
                result = self.run(args)
        except (SystemExit, Exception) as e:
            self.postrun(args, exc=e)
            self.fire_event('postrun', args, exc=e)
            raise e
        else:
            self.postrun(args, result=result)
            self.fire_event('postrun', args, result=result)
            return result

    def config_section(self):
        """ The string used in a .<ROOT>_config file section.  Usually this
        is just the full prog name for a command minus the root command. """
        names = []
        cmd = self
        while cmd.parent:
            names.append(cmd.name)
            cmd = cmd.parent
        if not names:
            return self.name
        else:
            return ' '.join(reversed(names))

    def default_config(self):
        """ Can be overridden to provide a 1 level deep dictionary of config
        values.  Theses values are optionally overridden by the end-user via
        the session's load_config routine, that essentially looks for an INI
        file where the `[section]` is the `.prog` value for this command. """
        return {}

    def get_config(self, section=None):
        """ Return the merged end-user configuration for this command or a
        specific section if set in `section`. """
        config = self.session.config
        section = self.config_section() if section is None else section
        try:
            return config[section]
        except KeyError:
            config.add_section(section)
            return config[section]

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, parent):
        """ Copy context from the parent into this instance as well as
        adjusting or depth value to indicate where we exist in a command
        tree. """
        self._parent = parent
        if parent:
            pctx = dict((x, getattr(parent, x)) for x in parent.context_keys)
            self.inject_context(pctx)
            self.depth = parent.depth + 1
            for command in self.subcommands.values():
                command.parent = self  # bump.
        else:
            self.depth = 0

    def find_root(self):
        """ Traverse parent refs to top. """
        cmd = self
        while cmd.parent:
            cmd = cmd.parent
        return cmd

    def inject_context(self, __context_dict__=None, **context):
        """ Map context dict to this instance as attributes and keep note of
        the keys being set so we can pass this along to any subcommands. """
        context = context or __context_dict__
        self.context_keys |= set(context.keys())
        for key, value in context.items():
            setattr(self, key, value)
        for command in self.subcommands.values():
            command.inject_context(context)

    @property
    def prog(self):
        return self.argparser.prog

    @prog.setter
    def prog(self, prog):
        """ Update ourself and any of our subcommands. """
        self.argparser.prog = prog
        fmt = '%s %%s' % prog if prog else '%s'
        for command in self.subcommands.values():
            command.prog = fmt % command.name
        # Rebind autoenv vars with recomputed key.
        for action in self._autoenv_actions:
            self.argparser.unbind_env(action)
            self.argparser.bind_env(action, self._make_autoenv(action))

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, value):
        """ Update ourself and any of our subcommands. """
        for command in self.subcommands.values():
            command.depth = value + 1
            del command.argparser._defaults[self.arg_label_fmt % self._depth]
            command.argparser._defaults[self.arg_label_fmt % value] = command
        self._depth = value

    def add_argument(self, *args, parser=None, autoenv=False, env=None,
                     complete=None, **kwargs):
        """ Allow cleaner action supplementation.  Autoenv will generate an
        environment variable to be usable as a defaults setter based on the
        command name and the dest property of the action. """
        if parser is None:
            parser = self.argparser
        action = parser.add_argument(*args, **kwargs)
        if autoenv:
            if env is not None:
                raise TypeError('Arguments `env` and `autoenv` are mutually '
                                'exclusive')
            env = self._make_autoenv(action)
        if env:
            self.argparser.bind_env(action, env)
            if autoenv:
                self._autoenv_actions.add(action)
        if complete:
            action.complete = complete
        return action

    def _make_autoenv(self, action):
        """ Generate a suitable env variable for this action.  This is
        dependant on our subcommand hierarchy.  Review the prog setter for
        details. """
        env = ('%s_%s' % (self.prog, action.dest)).upper()
        env = re.sub(self.env_scrub_re, '', env.strip())
        env = re.sub(self.env_flatten_re, '_', env)
        if re.match('^[0-9]', env):
            # Handle leading numbers.
            env = '_%s' % env
        return env

    def add_file_argument(self, *args, mode='r', buffering=1,
                          filetype_options=None, **kwargs):
        """ Add a tab-completion safe FileType argument.  This argument
        differs from a normal argparse.FileType based argument in that the
        value is a factory function that returns a file handle instead of
        providing an already open file handle.  There are various reasons
        why this is a better approach but it is also required to avoid
        erroneous creation of files with shellish tab completion. """
        type_ = supplement.SafeFileType(mode=mode, bufsize=buffering,
                                        **filetype_options or {})
        return self.add_argument(*args, type=type_, **kwargs)

    def add_table_arguments(self, *args, parser=None, **kwargs):
        if parser is None:
            parser = self.argparser
        return layout.Table.attach_arguments(parser, *args, **kwargs)

    def create_argparser(self):
        """ Factory for arg parser.  Can be overridden as long as it returns
        an ArgParser compatible instance. """
        if self.desc:
            if self.title:
                fulldesc = '%s\n\n%s' % (self.title, self.desc)
            else:
                fulldesc = self.desc
        else:
            fulldesc = self.title
        return self.ArgumentParser(self, description=fulldesc,
                                   formatter_class=self.ArgumentFormatter)

    def attach_session(self):
        """ Create a session and inject it as context for this command and any
        subcommands. """
        assert self.session is None
        root = self.find_root()
        session = self.Session(root)
        root.inject_context(session=session)
        return session

    def complete(self, text, line, begin, end):
        """ Get and format completer choices.  Note that all internal calls to
        completer functions must use [frozen]set()s. """
        self.fire_event('precomplete', text, line, begin, end)
        choices = self._complete(text, line, begin, end)
        choices -= self.completion_excludes
        sz = len(choices)
        if sz == 1:
            # XXX: This is pretty bad logic here.  In reality we need much
            # more complicated escape handling and imbalanced quote support.
            return set(shlex.quote(x) for x in choices)
        elif sz > 2:
            # We don't need the sentinel choice to prevent completion
            # when there is already more than 1 choice.
            choices -= {completer.ActionCompleter.sentinel}
        self.fire_event('postcomplete', choices)
        return choices

    def _complete(self, text, line, begin, end):
        """ Do naive argument parsing so the completer has better ability to
        understand expansion rules. """
        line = line[:end]  # Ignore characters following the cursor.
        fullargs = self.split_line(line)[1:]
        args = fullargs[:]
        options = self.deep_scan_parser(self.argparser)

        # Walk into options tree if subcommands are detected.
        last_subcommand = None
        while True:
            for key, completers in options.items():
                if key in args and hasattr(completers[0], 'items'):
                    args.remove(key)
                    last_subcommand = key
                    options = completers[0]
                    break
            else:
                break

        if text == last_subcommand:
            # We have to specially catch the case where the last argument is
            # the key used to find our subparser.  More specifically when the
            # cursor is not preceded by a space too, as this prevents the
            # completion routines from continuing.  The simplest way without
            # complicating the algo for coming up with our options list is to
            # simply shortcut the completer by returning a single item.
            # Subsequent tabs will work normally.
            return {text}

        # Look for incomplete actions.
        choices = set(x for x in options
                      if x is not None and x.startswith(text))
        arg_buf = []
        pos_args = []
        trailing_action = None
        # The slice below skips the last arg if it is 'active'.
        for x in reversed(args[:-1 if text else None]):
            if x in options:
                action = options[x][0]
                action.consume(arg_buf)
                pos_args.extend(arg_buf)
                del arg_buf[:]
                if action.full:
                    choices -= {action.key}
                if not trailing_action:
                    trailing_action = action
                    if not action.full:
                        if action.reached_min:
                            choices |= action(self, text, fullargs)
                            choices -= {action.key}
                        else:
                            choices = action(self, text, fullargs)
                            break
            else:
                arg_buf.insert(0, x)
        pos_args.extend(arg_buf)

        # Feed any remaining arguments in the buffer to positionals so long as
        # there isn't a trailing action that can still consume.
        if None in options and (not trailing_action or trailing_action.full):
            for x_action in options[None]:
                x_action.consume(pos_args)
                if not x_action.reached_min:
                    choices = x_action(self, text, fullargs)
                    break
                elif not x_action.full:
                    choices |= x_action(self, text, fullargs)
        return choices

    def split_line(self, line):
        """ Try to do pure shlex.split unless it can't parse the line. In that
        case we trim the input line until shlex can split the args and tack the
        unparsable portion on as the last argument. """
        remainder = []
        while True:
            try:
                args = shlex.split(line)
            except ValueError:
                remainder.append(line[-1])
                line = line[:-1]
            else:
                if remainder:
                    args.append(''.join(reversed(remainder)))
                return args

    @functools.lru_cache()
    def deep_scan_parser(self, parser):
        results = collections.defaultdict(list)
        for x in parser._actions:
            ac = completer.ActionCompleter(x)
            if ac.subparsers:
                for key, xx in ac.subparsers.items():
                    results[key].append(self.deep_scan_parser(xx))
            else:
                results[ac.key].append(ac)
        return results

    def get_commands_from(self, args):
        """ We have to code the key names for each depth.  This method scans
        for each level and returns a list of the command arguments. """
        commands = []
        for i in itertools.count(0):
            try:
                commands.append(getattr(args, self.arg_label_fmt % i))
            except AttributeError:
                break
        return commands

    def add_subcommand(self, command, default=False):
        if isinstance(command, type):
            command = command()
        command.parent = self
        if command.name is None:
            raise TypeError('Cannot add unnamed command: %s' % command)
        if command.name in self.subcommands:
            raise ValueError('Command name already added: %s' % command.name)
        if not self.subparsers:
            desc = 'Provide a subcommand argument to perform an operation.'
            addsub = self.argparser.add_subparsers
            self.subparsers = addsub(title='subcommands', description=desc,
                                     metavar='COMMAND')
        if default:
            if self.default_subcommand:
                raise ValueError("Default subcommand already exists.")
            self.default_subcommand = command
        if command.title is not None:
            help_fmt = '%s (default)' if default else '%s'
            help = help_fmt % command.title
        else:
            help = '(default)' if default else ''
        command.prog = '%s %s' % (self.prog, command.name)
        command.argparser._defaults[self.arg_label_fmt % self.depth] = command
        action = self.subparsers._ChoicesPseudoAction(command.name, (), help)
        self.subparsers._choices_actions.append(action)
        self.subparsers._name_parser_map[command.name] = command.argparser
        self.subcommands[command.name] = command

    def remove_subcommand(self, command=None, name=None):
        if name is None:
            if command is None:
                raise TypeError('A command or name is required')
            name = command.name
        command = self.subcommands.pop(name)
        del self.subparsers._name_parser_map[name]
        for action in self.subparsers._choices_actions:
            if action.dest == name:
                break
        else:
            raise RuntimeError("Subparser action not found for subcommand")
        self.subparsers._choices_actions.remove(action)
        command.session = None
        command.parent = None
