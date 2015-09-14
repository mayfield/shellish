"""
Demo how to add your auto tab completers.
"""

import random
import shellish

def thing_completer(prefix):
    letters = 'qwertyuiopasdfghjklzxcvbnm'
    word = lambda: ''.join(random.sample(letters, random.randint(1, 16)))
    return set(word() for x in range(random.randint(1, 1000)))

thing = shellish.Command(name='thing', doc='Demo Tab Completion')
thing.add_argument('--choices', choices=['one', 'two', 'three'])
thing.add_argument('--function', complete=thing_completer)
root = shellish.Command()
root.add_subcommand(thing)
root.interact()
