import ruamel.yaml
import six
import inspect

from yamlize import YamlizingError
from .round_trip_data import RoundTripData


class Yamlizable(object):

    __slots__ = ()

    def __getstate__(self):
        if hasattr(self, '__dict__'):
            d = {}
            for k, v in self.__dict__.items():
                d[k] = v
            return d
        else:
            state = []
            for cls in type(self).__mro__:
                for attr_name in cls.__slots__:
                    state.append(getattr(self, attr_name))
            return tuple(state)

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        else:
            ii = 0
            for cls in type(self).__mro__:
                for attr_name in cls.__slots__:
                    setattr(self, attr_name, state[ii])
                    ii += 1

    @classmethod
    def get_yamlizable_type(cls, type_):
        if issubclass(type_, Yamlizable):
            return type_
        else:
            return Typed(type_)

    @classmethod
    def load(cls, stream, Loader=ruamel.yaml.RoundTripLoader):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        loader = Loader(stream)
        try:
            node = loader.get_single_node()
            return cls.from_yaml(loader, node)
        finally:
            loader.dispose()

    @classmethod
    def dump(cls, data, stream=None, Dumper=ruamel.yaml.RoundTripDumper):
        # can't use ruamel.yaml.load because I need a Resolver/loader for
        # resolving non-string types
        convert_to_string = stream is None
        stream = stream or six.StringIO()
        dumper = Dumper(stream)

        try:
            dumper._serializer.open()
            root_node = cls.to_yaml(dumper, data)
            dumper.serialize(root_node)
            dumper._serializer.close()
        finally:
            try:
                dumper._emitter.dispose()
            except AttributeError:
                raise
                dumper.dispose()  # cyaml

        if convert_to_string:
            return stream.getvalue()

        return None

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        raise NotImplementedError

    @classmethod
    def to_yaml(cls, dumper, self, round_trip_data):
        raise NotImplementedError


class Typed(type):

    __types = {}

    def __new__(mcls, type_):
        if type_ not in mcls.__types:
            mcls.__types[type_] = type('Yamlizable' + type_.__name__,
                                       (Strong,), {'_Strong__type': type_})
        return mcls.__types[type_]


class Strong(Yamlizable):

    __type = None

    @classmethod
    def from_yaml(cls, loader, node, round_trip_data):
        data = loader.construct_object(node, deep=True)

        if not isinstance(data, cls.__type):
            try:
                new_value = cls.__type(data)  # to coerce to correct type
                # TODO: round trip data
                # new_value._set_round_trip_data(node)
                # loader.constructed_objects[node] = new_value
            except Exception:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(data, cls))

            if new_value != data:
                raise YamlizingError(
                    'Coerced `{}` to `{}`, but the new value `{}`'
                    ' is not equal to old `{}`.'
                    .format(type(data), type(new_value), new_value, data),
                    node)

            data = new_value

        round_trip_data[data] = RoundTripData(node)
        return data

    @classmethod
    def to_yaml(cls, dumper, data, round_trip_data):
        if not isinstance(data, cls.__type):
            try:
                data = cls.__type(data)  # to coerce to correct type
            except BaseException:
                raise YamlizingError('Failed to coerce data `{}` to type `{}`'
                                     .format(data, cls))

        node = dumper.represent_data(data)
        round_trip_data[data].apply(node)
        return node


Dynamic = Typed(object)

