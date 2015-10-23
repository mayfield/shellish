"""
Tree layout.
"""

import collections
import collections.abc
from . import vtml


class TreeNode(object):

    def __init__(self, value, children=None, label=None):
        self.value = value
        self.label = label
        self.children = children if children is not None else []

    def __lt__(self, item):
        return self.value < item.value


class Tree(object):
    """ Construct a visual tree from a data source. """

    tree_L = vtml.beststr('└── ', '\-- ')
    tree_T = vtml.beststr('├── ', '+-- ')
    tree_vertspace = vtml.beststr('│   ', '|   ')

    def __init__(self, formatter=None, sort_key=None, plain=None):
        self.formatter = formatter or self.default_formatter
        self.sort_key = sort_key
        if plain is None:
            plain = not vtml.is_terminal()
        self.plain = plain

    def default_formatter(self, node):
        if node.label is not None:
            return '%s: <b>%s</b>' % (node.value, node.label)
        else:
            return str(node.value)

    def render(self, nodes, prefix=None):
        node_list = list(nodes)
        end = len(node_list) - 1
        if self.sort_key is not False:
            node_list.sort(key=self.sort_key)
        for i, x in enumerate(node_list):
            if prefix is not None:
                line = [prefix]
                if end == i:
                    line.append(self.tree_L)
                else:
                    line.append(self.tree_T)
            else:
                line = ['']
            yield vtml.vtmlrender(''.join(line + [self.formatter(x)]),
                                  plain=self.plain)
            if x.children:
                if prefix is not None:
                    line[-1] = '    ' if end == i else self.tree_vertspace
                yield from self.render(x.children, prefix=''.join(line))


def treeprint(data, render_only=False, **options):
    """ Render a tree structure based on generic python containers. The keys
    should be titles and the values are children of the node or None if it's
    an empty leaf node;  Primitives are valid leaf node labels too.  E.g.

        sample = {
            "Leaf 1": None,
            "Leaf 2": "I have a label on me",
            "Branch A": {
                "Sub Leaf 1 with float label": 3.14,
                "Sub Branch": {
                    "Deep Leaf": None
                }
            },
            "Branch B": {
                "Sub Leaf 2": None
            }
        }
    """
    def crawl(obj, odict=collections.OrderedDict):
        for key, value in obj.items():
            if isinstance(value, collections.abc.Mapping):
                yield TreeNode(key, children=crawl(value))
            elif isinstance(value, collections.abc.Sequence) and \
                 not isinstance(value, str):
                value = odict((i, x) for i, x in enumerate(value))
                yield TreeNode(key, children=crawl(value))
            elif value is not None:
                yield TreeNode(key, label=value)
            else:
                yield TreeNode(key)
    t = Tree(**options)
    render_gen = t.render(crawl(data))
    if render_only:
        return render_gen
    else:
        for x in render_gen:
            print(x)
