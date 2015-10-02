"""
Demo of different ways to skin a cat.
"""

import shellish

##############
# Decorators #
##############
@shellish.autocommand
def cat1():
    cat1.interact()

@shellish.autocommand
def sub1(optional:int=1):
    print("ran subcommand1", optional)

cat1.add_subcommand(sub1)


###############
# Composition #
###############
cat2 = shellish.Command(name='cat2', title='composition cat')
cat2.run = lambda args: cat2.interact()

sub2 = shellish.Command(name='sub2', title='composition cat sub')
sub2.add_argument('--optional', type=int, default=2)
sub2.run = lambda args: print("ran subcommand2", args.optional)
cat2.add_subcommand(sub2)


###############
# Inheritance #
###############
class Cat3(shellish.Command):
    """ Inheritance cat. """

    name = 'cat3'

    def run(self, args):
        self.interact()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_subcommand(Sub3)


class Sub3(shellish.Command):
    """ Inheritance cat sub. """

    name = 'sub3'

    def setup_args(self, parser):
        self.add_argument('--optional', type=int, default=3)

    def run(self, args):
        print("ran subcommand3", args.optional)


# Putting it together for a demo..
main = shellish.Command(name='main', title='harness')
main.add_subcommand(cat1)
main.add_subcommand(cat2)
main.add_subcommand(Cat3)
main.interact()
