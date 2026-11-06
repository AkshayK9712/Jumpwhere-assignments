import math


class Shape:
    """Base class for all shapes."""

    def __init__(self, name):
        self.name = name

    def area(self):
        raise NotImplementedError("Subclasses must override area()")


class Circle(Shape):
    def __init__(self, radius):
        super().__init__("Circle")
        self._radius = radius

    def area(self):
        return math.pi * self._radius ** 2


class Rectangle(Shape):
    def __init__(self, width, height):
        super().__init__("Rectangle")
        self._width = width
        self._height = height

    def area(self):
        return self._width * self._height


class Triangle(Shape):
    def __init__(self, base, height):
        super().__init__("Triangle")
        self._base = base
        self._height = height

    def area(self):
        return 0.5 * self._base * self._height


def print_shape_areas(shapes):
    """Polymorphism: works on any Shape without type checks."""
    for shape in shapes:
        print(f"{shape.name}: area = {shape.area():.2f}")


if __name__ == "__main__":
    shapes = [
        Circle(5),
        Rectangle(4, 6),
        Triangle(3, 8),
    ]
    print_shape_areas(shapes)