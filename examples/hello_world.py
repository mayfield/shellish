import shellish

class Hello(shellish.Command):
    """ I am a required docstring used to document the --help output! """

    name = 'hello'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_subcommand(World, default=True)

    def run(self, args):
        shellish.Shell(self).cmdloop()


class World(shellish.Command):
    """ Say something. """

    name = 'world'

    def run(self, args):
        print('Hello World')


if __name__ == '__main__':
    root = Hello()
    args = root.argparser.parse_args()
    root.invoke(args)
