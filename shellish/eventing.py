"""
A very simple event framework that can be used to more dynamically mixin
behavior for shellish activity.
"""


class Eventer(object):
    """ Very simple event mix-in. """

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance._events = {}
        return instance

    def add_events(self, adding):
        """ Setup events for this instance.  Just a list of strings. """
        for x in adding:
            self._events.setdefault(x, [])

    def add_listener(self, event, callback, single=False, priority=1):
        """ Add a callback to an event list so it will be run at this event's
        firing. If single is True, the event is auto-removed after the first
        invocation. Priority can be used to jump ahead or behind other
        callback invocations."""
        event_stack = self._events[event]
        event_stack.append({
            "callback": callback,
            "single": single,
            "priority": priority
        })
        event_stack.sort(key=lambda x: x['priority'])

    def remove_listener(self, event, callback, single=None, priority=None):
        """ Remove the event listener matching the same signature used for
        adding it.  This will remove AT MOST one entry meeting the signature
        requirements. """
        event_stack = self._events[event]
        for x in event_stack:
            if x['callback'] == callback and \
               (single is None or x['single'] == single) and \
               (priority is None or x['priority'] == priority):
                event_stack.remove(x)
                break
        else:
            raise KeyError('Listener not found for "%s": %s' % (event,
                           callback))

    def fire_event(self, event, *args, **kwargs):
        """ Execute the listeners for this event passing any arguments
        along. """
        remove = []
        event_stack = self._events[event]
        for x in event_stack:
            x['callback'](*args, **kwargs)
            if x['single']:
                remove.append(x)
        for x in remove:
            event_stack.remove(x)
