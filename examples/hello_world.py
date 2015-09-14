import shellish

class Hello(shellish.Command):
    """ I am a required docstring used to document the --help output! """

    name = 'hello'

    def run(self, args):
        """ Just run the shell if a subcommand was not given. """
        self.interact()


class World(shellish.Command):
    """ Say something. """

    name = 'world'

    def run(self, args):
        print('Hello World')


hello = Hello()
hello.add_subcommand(World)
hello()
