import unittest

import numpy

from yamlize import Object, YamlizingError, Attribute


class PositivePoint(Object):

    x = Attribute(type=float)

    @x.validator
    def x(self, x):
        if x < 0.0:
            raise ValueError('Cannot set PositivePoint.x to {}'.format(x))

    y = Attribute(type=float, validator=lambda self, y: y > 0)


class TestDataValidation(unittest.TestCase):

    def test_assign_properties(self):
        p = PositivePoint()
        p.x = 99
        with self.assertRaises(ValueError):
            p.x = -1.0
        p.y = 1e99
        with self.assertRaises(ValueError):
            p.x = -1.0e-99

    def test_numpy_cool(self):
        p = PositivePoint()
        p.x = numpy.float64(10)

        # this should not result in an error.
        PositivePoint.dump(p)

    def test_load_properties(self):
        with self.assertRaises(YamlizingError):
            PositivePoint.load(u'{x: -0.0000001, y: 1.0}')

        with self.assertRaises(YamlizingError):
            PositivePoint.load(u'{x: 0.0000001, y: -0.00001}')

    def test_from_yaml(self):

        class PositivePoint2(Object):
            x = Attribute(type=float)
            y = Attribute(type=float)

            @classmethod
            def from_yaml(cls, loader, node, round_trip_data=None):
                # from_yaml.__func__ is the unbound class method
                self = Object.from_yaml.__func__(PositivePoint2, loader, node, round_trip_data)

                if self.x < 0.0 or self.y < 0.0:
                    raise YamlizingError('Point x and y values must be positive', node)

                return self

        with self.assertRaises(YamlizingError):
            PositivePoint2.load(u'{ x: -0.0000001, y: 1.0}') # doctest: +IGNORE_EXCEPTION_DETAIL


class Person(Object):

    first = Attribute(type=str)

    last = Attribute(type=str)

    full = Attribute(type=str)


if __name__ == '__main__':
    unittest.main()

