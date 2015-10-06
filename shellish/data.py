"""
Data related tools/utilities.
"""

import collections
import collections.abc
import functools
import time

__public__ = ['hone_cache']

hone_cache_finders = {}
TTLCacheEntry = collections.namedtuple("TTLCacheEntry", 'ctime, ref')
HoneCacheInfo = collections.namedtuple("HoneCacheInfo", 'hits, misses, '
                                       'maxsize, currsize, partials, maxage, '
                                       'finder')


class TTLCache(collections.abc.MutableMapping):
    """ Sized and aged mapping.  The time-to-live is fixed for the entire
    cache to simplify the garbage collector. """

    def __init__(self, maxsize=None, ttl=None, timer=time.monotonic,
                 container=collections.OrderedDict):
        self.data = container()
        self.maxsize = maxsize
        self.ttl = ttl
        self.timer = timer
        super().__init__()

    def is_expired(self, entry, time=None):
        if self.ttl is None:
            return True
        if time is None:
            time = self.timer()
        return time - entry.ctime <= self.ttl

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        """ Return valid keys as of each look into the iterator.  If the
        iterator is not used right away the keys returned will be those that
        are valid at view time and not when the iterator was created. """
        return (k for k, e in self.data.items() if self.is_expired(e))

    def __len__(self):
        """ Oddly this can be one of the more expensive calls since we may have
        to GC a lot of objects.  Best to avoid using it if you can. """
        self.gc(fullcollect=True)
        return len(self.data)

    def __setitem__(self, key, value):
        """ Wrap an item with a timestamp and if replacing an existing key
        move it to the end. """
        move = key in self.data
        entry = TTLCacheEntry(self.timer(), value)
        self.data[key] = entry
        if move:
            self.data.move_to_end(key)
        self.gc(fullcollect=False)

    def __getitem__(self, key):
        """ Unwrap and check the vitality of the entry. """
        entry =  self.data[key]
        if not self.is_expired(entry):
            del self[key]
            raise KeyError(key)
        return entry.ref

    def __contains__(self, key):
        try:
            return self.data[key].is_expired()
        except KeyError:
            return False

    def gc(self, fullcollect=True):
        """ Garbage collect overflow and/or aged entries if `fullcollect`. """
        collect = 0
        size = len(self.data)
        now = self.timer()
        for key, entry in self.data.items():
            if (self.maxsize is not None and size - collect > self.maxsize) or \
               (fullcollect and not self.is_expired(entry, time=now)):
                collect += 1
            else:
                break
        for i in range(collect):
            self.data.popitem(last=False)
        return collect


def hone_cache(maxsize=128, maxage=None, refineby='startswith'):
    """ A caching decorator that follows after the style of lru_cache. Calls
    that are sharper than previous requests are returned from the cache after
    honing in on the requested results using the `refineby` technique.

    The `refineby` technique can be `startswith`, `container` or a user
    defined function used to provide a subset of results.

    Eg.
        @hone_cache()
        def completer(prefix):
            print("MISS")
            return set(x for x in {'foo', 'foobar', 'baz'}
                       if x.startswith(prefix))
        completer('f')    # -> {'foo', 'foobar'}
        MISS
        completer('fo')   # -> {'foo', 'foobar'}
        completer('foob') # -> {'foobar'}
        completer('')     # -> {'foo', 'foobar', 'baz'}
        MISS
        completer('ba')   # -> {'baz'}

    If while trying to hone a cache hit there is an exception the wrapped
    function will be called as if it was a full miss.

    The `maxage` argument is an option time-to-live in seconds for each cache
    result.  Any cache entries over the maxage are lazily replaced. """
    if not callable(refineby):
        finder = hone_cache_finders[refineby]
    else:
        finder = refineby

    def decorator(inner_func):
        wrapper = make_hone_cache_wrapper(inner_func, maxsize, maxage, finder)
        return functools.update_wrapper(wrapper, inner_func)
    return decorator


def hone_cache_startswith_finder(radix, partial, partial_radix):
    return type(partial)(x for x in partial if x.startswith(radix))
hone_cache_finders['startswith'] = hone_cache_startswith_finder


def hone_cache_container_finder(radix, partial_radix, partial):
    path_offt = radix[len(partial_radix):]
    for x in path_offt:
        partial = partial[x]
hone_cache_finders['container'] = hone_cache_container_finder


def make_hone_cache_wrapper(inner_func, maxsize, maxage, finder):
    """ Keeps a cache of requests we've already made and use that for
    generating results if possible.  If the user asked for a root prior
    to this call we can use it to skip a new lookup using `finder`.  A
    top-level lookup will effectively serves as a global cache. """

    hits = misses = partials = 0
    cache = TTLCache(maxsize, ttl=maxage)
    miss = object()

    def wrapper(radix):
        nonlocal hits, misses, partials
        radix_size = len(radix)
        for i in range(radix_size, -1, -1):
            partial_radix = radix[:i]
            partial = cache.get(partial_radix, miss)
            if partial is not miss:
                if i == radix_size:
                    hits += 1
                    return partial
                else:
                    try:
                        print("PARTIAL")
                        r = finder(radix, partial_radix, partial)
                    except:
                        import traceback
                        traceback.print_stack()
                        print("EX DEFER")
                        break  # Defer to full call for errors.
                    else:
                        partials += 1
                        return r
        print("MISSSSS", radix)
        misses += 1
        cache[radix] = r = inner_func(radix)
        return r

    def cache_info():
        """ Emulate lru_cache so this is a low touch replacement. """
        return HoneCacheInfo(hits, misses, maxsize, len(cache), partials,
                             maxage, finder)

    def cache_clear():
        """ Clear cache and stats. """
        nonlocal hits, misses, partials
        hits = misses = partials = 0
        cache.clear()

    def cache_gc(fullcollect=True):
        """ Since this can be expensive, we expose it to the user so they
        can choose when to perform it. """
        cache.gc(fullcollect)

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear
    wrapper.cache_gc = cache_gc

    return functools.update_wrapper(wrapper, inner_func)
