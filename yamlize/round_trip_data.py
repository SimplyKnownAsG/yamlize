

class _AnchorNode(object):
    # TODO: replace with ruamel.yaml.comments.Anchor

    __slots__ = ('value', )

    def __init__(self, value):
        self.value = value


class RoundTripData(object):

    __slots__ = ('_rtd', '_kids_rtd', '_name_order', '_merge_parents',
                 '_complete_inheritance')  # couldn't use private variables with six

    def __init__(self, node):
        self._rtd = {}
        self._kids_rtd = {}
        self._name_order = []
        self._merge_parents = []
        self._complete_inheritance = False

        if node is not None:
            for key in dir(node):
                if key.startswith('__') or key in {'value', 'id', 'start_mark', 'end_mark'}:
                    continue

                attr = getattr(node, key)

                if callable(attr) or attr is None:
                    continue

                self._rtd[key] = attr

    def __str__(self):
        msg = 'RoundTripData:'
        msg += '\n    name_order: {}'.format(', '.join(self._name_order))
        msg += '\n    rtd: {{{}}}'.format(', '.join('{}: {}'.format(k, v)
                                                    for k, v in self._rtd.items()))
        return msg

    def __reduce__(self):
        """
        Used for pickling, results in a loss of data.

        Some objects from ruamel.yaml do not appear to be pickleable.
        """
        return (RoundTripData, (None,))

    def __bool__(self):
        return len(self._rtd) > 0

    __nonzero__ = __bool__

    def apply(self, node):
        for key, val in self._rtd.items():
            if key == 'anchor':
                val = _AnchorNode(val)
            setattr(node, key, val)

    def __get_key(self, key):
        try:
            return hash(key)
        except TypeError:
            return type(key), id(key)

    def __setitem__(self, key, rtd):
        # don't bother storing if there wasn't any data
        if rtd:
            self._kids_rtd[self.__get_key(key)] = rtd

    def __getitem__(self, key):
        return self._kids_rtd.get(self.__get_key(key), RoundTripData(None))

