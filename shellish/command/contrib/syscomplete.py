"""
Utility command for setup and exec of system completion.

Currently supports bash or zsh, but mostly bash.
"""

import argparse
import os
from .. import command


class SystemCompletion(command.Command):
    """ Generate a bash/zsh compatible completion script.

    Typically this command is run once and concatenated to your .<shell>rc
    file so completion targets for your shellish command can work from your
    system shell.  The idea is lifted directly from npm-completion. """

    name = 'completion'

    script_header = '''
        ###-begin-%(prog)s-%(name)s-###
        #
        # %(prog)s command %(name)s script
        #
        # Installation: %(prog)s %(name)s >> ~/.%(shell)src
        #
    '''

    script_body = {
        'bash': '''
            _%(prog)s_%(name)s() {
                local words cword
                cword="$COMP_CWORD"
                words=("${COMP_WORDS[@]}")
                local si="$IFS"
                IFS=$'\\n' COMPREPLY=($(COMP_CWORD="$cword" \\
                                     COMP_LINE="$COMP_LINE" \\
                                     %(prog)s %(name)s --seed "${words[@]}" \\
                                     2>/dev/null)) || return $?
                IFS="$si"
            }
            complete -o nospace -F _%(prog)s_%(name)s %(prog)s
        ''',
        'zsh': '''
            _%(prog)s_%(name)s() {
                local si=$IFS
                compadd -- $(COMP_CWORD=$((CURRENT-1)) \\
                             COMP_LINE=$BUFFER \\
                             %(prog)s %(name)s -S '' --seed "${words[@]}" \\
                             2>/dev/null)
                IFS=$si
            }
            compdef _%(prog)s_%(name)s %(name)s
        '''
    }

    script_footer = '''###-end-%(prog)s-$(name)s-###'''

    def setup_args(self, parser):
        self.add_argument('--seed', nargs=argparse.REMAINDER)
        super().setup_args(parser)

    def run(self, args):
        if not args.seed:
            return self.show_setup()
        seed = args.seed
        prog = seed.pop(0)
        index = int(os.getenv('COMP_CWORD')) - 1
        line = os.getenv('COMP_LINE')[len(prog) + 1:]
        begin = len(' '.join(seed[:index]))
        end = len(line)
        if begin > 0:
            try:
                cmd, args = self.session.cmd_split(seed[0])
            except KeyError:
                return
            cfunc = cmd.complete
        else:
            cfunc = self.session.complete_names
        for x in cfunc(seed[index], line, begin, end):
            print(x)

    def show_setup(self):
        """ Provide a helper script for the user to setup completion. """
        shell = os.getenv('SHELL')
        if not shell:
            raise SystemError("No $SHELL env var found")
        shell = os.path.basename(shell)
        if shell not in self.script_body:
            raise SystemError("Unsupported shell: %s" % shell)
        tplvars = {
            "prog": '-'.join(self.prog.split()[:-1]),
            "shell": shell,
            "name": self.name
        }
        print(self.trim(self.script_header % tplvars))
        print(self.trim(self.script_body[shell] % tplvars))
        print(self.trim(self.script_footer % tplvars))

    def trim(self, text):
        """ Trim whitespace indentation from text. """
        lines = text.splitlines()
        firstline = lines[0] or lines[1]
        indent = len(firstline) - len(firstline.lstrip())
        return '\n'.join(x[indent:] for x in lines if x.strip())
