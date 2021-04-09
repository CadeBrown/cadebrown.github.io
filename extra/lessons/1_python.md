---
layout: post
title: "Lessons (#1) - Python"
categories: [lessons]
tags: [lessons]
series: lessons-basics
thumb: assets/img/kata-docs-0.png
---

Let's learn how to read, write, and run Python code. [Python](https://www.python.org/) is a dynamic programming language which, like bash, is very popular and widely available. It's also very general, and can be used to accomplish tasks from automation, math, machine learning, GUI apps, and more.

Knowing Python is one of the most important things in today's world, since so many things are either written in Python, or use it as a tool.

Like the shell, Python can be used as a REPL (Read-Evaluate-Print-Loop). The prompt for Python is `>>>` (and `...` as a secondary prompt). Some examples here will be given as REPL, and some will be given as a file (you can tell which is which by whether the example starts with `>>>`).

However, Python is not quite as lenient as the shell. String messages must always be enclosed in quotes (although, in Python, `'` and `"` are identical, they have no semantic differences).

Instead of issuing commands like `command arg0 arg1 arg2`, you instead call functions in Python. You do this with `()`. For example, `command(arg0, arg1, arg2)`. Additionally, unlike in the shell where everything is assumed to be textual data, Python introduces the concept of objects, types, variables, and modules. We will get into these later but the main thing to remember is that Python is more advanced and more nuanced.


## OOP/Types

[Object Oriented Programming (OOP)](https://en.wikipedia.org/wiki/Object-oriented_programming) is a way of programming (think of "oil painting is a way of painting") that uses the notion of "objects" that have data attached to them. To go further with the painting analogy, there are reasons to prefer oil painting over water color and vice-versa. However, some may say that oil painting is easier to paint a lot of scenes realistically (i.e. that water color is very hard to do some things in).

Python is an OOP language, and is a "Pure OOP" language in that *everything* is an object in Python (even a number, string, module, etc). This means that things like storage containers can store numbers with strings with modules with your custom object, and can treat everything like an object. 

Python is also [duck-typed](https://en.wikipedia.org/wiki/Duck_typing), which means if objects behave a certain way, they can be lumped together with other objects that behave like that. For example, objects that overload the `+` operator can be treated like numbers and added. This will be more important once you already understand the language, and you will see why it is useful


## Builtins

There are a ton of [builtin functions in Python](https://docs.python.org/3/library/functions.html). For example, the `print` function is similar to the `echo` command in bash. 

For example, here is the `hello, world` program in Python:

```python
print("hello, world")
```

(note: the `print` function adds spaces between its arguments and a newline after)

The most useful builtins are:

  * `str(obj)`: Turns an object into a string
  * `repr(obj)`: Turns an object into a "representation" string (which often has more info than `str(obj)`)
  * `int(obj)`: Turns an object into an integer
  * `float(obj)`: Turns an object into a floating point number
  * `list(obj)`: Turns an object into a list of objects. You can also use `[]` to create lists, which we will get to later
  * `input(prompt='')`: Reads a line of input from whoever is running the program
  * `type(obj)`: Gives the type of the object
  * `isinstance(obj, tp)`: Returns a boolean telling whether `obj` is of type `tp` (i.e. whether it is an instance of that type)
