"""
Nesting commands using simple syntax.
"""

import shellish


@shellish.autocommand
def main():
    print("Default Action")


@shellish.autocommand
def sub(option=None):
    print("Hi from sub", option)


main.add_subcommand(sub)
main()
