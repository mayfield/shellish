"""
A very simple event framework that can be used to more dynamically mixin
behavior for shellish activity.
"""


class Eventer(object):
    """ Very simple event MixIn. """

    class_events = {
        'init': []
    }

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.events = {}
        cls.fire_class_event('init', instance)
        return instance

    @staticmethod
    def _add_events(events, adding):
        """ Add events to an events object. """
        for x in adding:
            events.setdefault(x, [])

    def add_events(self, events):
        """ Setup events for this instance.  Just a list of strings. """
        return self._add_events(self.events, events)

    @classmethod
    def add_class_events(cls, events):
        """ Setup events for this class.  Just a list of strings. """
        return cls._add_events(cls.class_events, events)

    @staticmethod
    def _add_listener(events, event, callback, single=False, priority=None):
        event_stack = events[event]
        if priority is None:
            try:
                priority = event_stack[-1]['priority'] + 1
            except IndexError:
                priority = 1
        event_stack.append({
            "callback": callback,
            "single": single,
            "priority": priority
        })
        event_stack.sort(key=lambda x: x['priority'])

    def add_listener(self, *args, **kwargs):
        return self._add_listener(self.events, *args, **kwargs)

    @classmethod
    def add_class_listener(cls, *args, **kwargs):
        return cls._add_listener(cls.class_events, *args, **kwargs)

    @staticmethod
    def _remove_listener(events, event, callback, single=None, priority=None):
        """ Remove the event listener matching the signature used for adding
        it.  This will remove at most one entry meeting the signature
        requirements. """
        event_stack = events[event]
        for x in event_stack:
            if x['callback'] == callback and \
               (single is None or x['single'] == single) and \
               (priority is None or x['priority'] == priority):
                event_stack.remove(x)
                break
        else:
            raise KeyError('Listener not found for "%s": %s'  % (event,
                           callback))

    def remove_listener(self, *args, **kwargs):
        return self._remove_listener(self.events, *args, **kwargs)

    @classmethod
    def remove_class_listener(cls, *args, **kwargs):
        return cls._remove_listener(cls.class_events, *args, **kwargs)

    @staticmethod
    def _fire_event(events, event, *args, **kwargs):
        """ Execute the listeners for this event passing any arguments
        along. """
        remove = []
        event_stack = events[event]
        for x in event_stack:
            x['callback'](*args, **kwargs)
            if x['single']:
                remove.append(x)
        for x in remove:
            event_stack.remove(x)

    def fire_event(self, *args, **kwargs):
        return self._fire_event(self.events, *args, **kwargs)

    @classmethod
    def fire_class_event(cls, *args, **kwargs):
        return cls._fire_event(cls.class_events, *args, **kwargs)
