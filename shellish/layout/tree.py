"""
Tree layout.
"""

import collections
import collections.abc
import sys
from .. import rendering


class TreeNode(object):

    def __init__(self, value, children=None, label=None):
        self.value = value
        self.label = label
        self.children = children if children is not None else []

    def __lt__(self, item):
        return self.value < item.value


class Tree(object):
    """ Construct a visual tree from a data source. """

    tree_L = rendering.beststr('└── ', '\-- ')
    tree_T = rendering.beststr('├── ', '+-- ')
    tree_vertspace = rendering.beststr('│   ', '|   ')

    def __init__(self, formatter=None, sort_key=None):
        self.formatter = formatter or self.default_formatter
        self.sort_key = sort_key

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
            yield rendering.vtmlrender(''.join(line + [self.formatter(x)]))
            if x.children:
                if prefix is not None:
                    line[-1] = '    ' if end == i else self.tree_vertspace
                yield from self.render(x.children, prefix=''.join(line))


def treeprint(data, render_only=False, file=None, **options):
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

    def getiter(obj):
        if isinstance(obj, collections.abc.Mapping):
            return obj.items()
        elif isinstance(obj, collections.abc.Iterable) and \
             not isinstance(obj, str):
            return enumerate(obj)

    def cycle_check(item, seen=set()):
        item_id = id(item)
        if item_id in seen:
            raise ValueError('Cycle detected for: %s' % repr(item))
        else:
            seen.add(item_id)

    def crawl(obj, cc=cycle_check):
        cc(obj)
        objiter = getiter(obj)
        if objiter is None:
            yield TreeNode(obj)
        else:
            for key, item in objiter:
                if isinstance(item, collections.abc.Iterable) and \
                   not isinstance(item, str):
                    yield TreeNode(key, children=crawl(item))
                elif item is None:
                    yield TreeNode(key)
                else:
                    yield TreeNode(key, label=item)
    t = Tree(**options)
    render_gen = t.render(crawl(data))
    if render_only:
        return render_gen
    else:
        file = sys.stdout if file is None else file
        conv = (lambda x: x.plain()) if not file.isatty() else (lambda x: x)
        for x in render_gen:
            print(conv(x), file=file)
