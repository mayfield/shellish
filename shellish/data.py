"""
Data related tools/utilities.
"""

import collections
import collections.abc
import functools
import time

hone_cache_finders = {}
TTLCacheInfo = collections.namedtuple("TTLCacheInfo", ('hits', 'misses',
                                      'maxsize', 'currsize', 'maxage'))
HoneCacheInfo = collections.namedtuple('HoneCacheInfo', TTLCacheInfo._fields +
                                       ('partials', 'findger'))
TTLMappingEntry = collections.namedtuple("TTLMappingEntry", 'ctime, ref')


class TTLMapping(collections.abc.MutableMapping):
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
        time = self.timer() if time is None else time
        return time - entry.ctime > self.ttl

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        """ Return valid keys as of each look into the iterator.  If the
        iterator is not used right away the keys returned will be those that
        are valid at view time and not when the iterator was created. """
        if self.ttl is None:
            return iter(self.data)
        else:
            return (k for k, e in self.data.items() if not self.is_expired(e))

    def __len__(self):
        self.gc()
        return len(self.data)

    def __setitem__(self, key, value):
        """ Wrap an item with a timestamp and if replacing an existing key
        move it to the end. """
        move = key in self.data
        time = self.timer() if self.ttl is not None else None
        entry = TTLMappingEntry(time, value)
        self.data[key] = entry
        if move:
            self.data.move_to_end(key)
        self.gc()

    def __getitem__(self, key):
        """ Unwrap and check the vitality of the entry. """
        entry = self.data[key]
        if self.ttl is not None and self.is_expired(entry):
            del self.data[key]
            raise KeyError(key)
        return entry.ref

    def __contains__(self, key):
        if self.ttl is None:
            return key in self.data
        try:
            return not self.is_expired(self.data[key])
        except KeyError:
            return False

    def gc(self):
        """ Garbage collect overflow and/or aged entries. """
        manifest = []
        overlimit = len(self.data) - self.maxsize \
                    if self.maxsize is not None else 0
        now = self.ttl is not None and self.timer()
        for key, entry in self.data.items():
            if overlimit > 0 or (now and self.is_expired(entry, time=now)):
                overlimit -= 1
                manifest.append(key)
            else:
                break
        for x in manifest:
            del self.data[x]

    def clear(self):
        self.data.clear()


def hone_cache(maxsize=128, maxage=None, refineby='startswith',
               store_partials=False):
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
        wrapper = make_hone_cache_wrapper(inner_func, maxsize, maxage, finder,
                                          store_partials)
        return functools.update_wrapper(wrapper, inner_func)
    return decorator


def hone_cache_startswith_finder(radix, partial_radix, partial):
    return type(partial)(x for x in partial if x.startswith(radix))

hone_cache_finders['startswith'] = hone_cache_startswith_finder


def hone_cache_container_finder(radix, partial_radix, partial):
    path_offt = radix[len(partial_radix):]
    for x in path_offt:
        partial = partial[x]
    return partial

hone_cache_finders['container'] = hone_cache_container_finder


def make_hone_cache_wrapper(inner_func, maxsize, maxage, finder,
                            store_partials):
    """ Keeps a cache of requests we've already made and use that for
    generating results if possible.  If the user asked for a root prior
    to this call we can use it to skip a new lookup using `finder`.  A
    top-level lookup will effectively serves as a global cache. """

    hits = misses = partials = 0
    cache = TTLMapping(maxsize, maxage)

    def wrapper(*args):
        nonlocal hits, misses, partials
        radix = args[-1]
        # Attempt fast cache hit first.
        try:
            r = cache[radix]
        except KeyError:
            pass
        else:
            hits += 1
            return r
        for i in range(len(radix) - 1, -1, -1):
            partial_radix = radix[:i]
            try:
                partial = cache[partial_radix]
            except KeyError:
                continue
            try:
                r = finder(radix, partial_radix, partial)
            except:
                break  # Treat any exception as a miss.
            partials += 1
            if store_partials:
                cache[radix] = r
            return r
        misses += 1
        cache[radix] = r = inner_func(*args)
        return r

    def cache_info():
        """ Emulate lru_cache so this is a low touch replacement. """
        return HoneCacheInfo(hits, misses, maxsize, len(cache), maxage,
                             partials, finder)

    def cache_clear():
        """ Clear cache and stats. """
        nonlocal hits, misses, partials
        hits = misses = partials = 0
        cache.clear()

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear

    return functools.update_wrapper(wrapper, inner_func)


def ttl_cache(maxage, maxsize=128):
    """ A time-to-live caching decorator that follows after the style of
    lru_cache.  The `maxage` argument is time-to-live in seconds for each
    cache result.  Any cache entries over the maxage are lazily replaced. """

    def decorator(inner_func):
        wrapper = make_ttl_cache_wrapper(inner_func, maxage, maxsize)
        return functools.update_wrapper(wrapper, inner_func)
    return decorator


def make_ttl_cache_wrapper(inner_func, maxage, maxsize, typed=False):
    """ Use the function signature as a key for a ttl mapping.  Any misses
    will defer to the wrapped function and its result is stored for future
    calls. """

    hits = misses = 0
    cache = TTLMapping(maxsize, maxage)

    def wrapper(*args, **kwargs):
        nonlocal hits, misses
        key = functools._make_key(args, kwargs, typed)
        try:
            result = cache[key]
        except KeyError:
            misses += 1
            result = cache[key] = inner_func(*args, **kwargs)
        else:
            hits += 1
        return result

    def cache_info():
        """ Emulate lru_cache so this is a low touch replacement. """
        return TTLCacheInfo(hits, misses, maxsize, len(cache), maxage)

    def cache_clear():
        """ Clear cache and stats. """
        nonlocal hits, misses
        hits = misses = 0
        cache.clear()

    wrapper.cache_info = cache_info
    wrapper.cache_clear = cache_clear

    return functools.update_wrapper(wrapper, inner_func)
