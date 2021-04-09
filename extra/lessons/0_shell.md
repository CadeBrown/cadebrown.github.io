---
layout: post
title: "Lessons (#0) - Shell"
categories: [lessons]
tags: [lessons]
series: lessons-basics
thumb: assets/img/kata-docs-0.png
---

Let's learn how to use a shell on your computer. A [shell](https://en.wikipedia.org/wiki/Shell_(computing)) is a prompt that allows you to run programs, manage your filesystem, and run diagnostics on your computer. They will be the primary way you interface with your computer, for programming and many technical tasks, so it's important to start with the basics.

Shells are typically a REPL (Read-Evaluate-Print-Loop), which means you will see a prompt (sometimes `$`, `>`, or something else), then you enter 1 or more lines, press `Enter` (or an equivalent "submit" button), and the shell will try and do what you tell it. For example, this tutorial assumes lines that start with a `$` are entered by you, everything else is the output (unless otherwise specified)

There are different shells with different syntax, but we will focus on bash and bash-like shells. [Bash](https://en.wikipedia.org/wiki/Bash_(Unix_shell)) (Borune Again SHell) is a very popular shell included in MacOS, Linux, and most other Unix-like OSes.

The most basic explanation of the syntax of bash is as a command language. Think of each line as a "command" to do something. Each command takes "arguments", which tell it specifically what to do (the "arguments" can be any string of text, including file names, numbers, or something else).

The exact list of utilities will depend on your system and what you have installed, but there are a few common commands that are available almost everywhere:

## Commands

### `echo`: Print out text

One of the most basic commands, `echo`, 

```shell
$ echo

$ echo hello, world
hello, world
$ echo "hello, world"
hello, world
```

You'll notice that 2 of the examples give the same output (`hello, world`). One uses quotes while one does not. There is actually a subtle difference between the two invocations.

The first invocation (`echo hello, world`) is treated like this: a command `echo` with 2 arguments (`hello,` and `world`). The second (`echo "hello, world"`) uses quotation marks, which is a command `echo` with a single argument (`hello, world` is one argument). They happen to create the same output, because the `echo` command puts a space between each of its arguments, and accepts as many arguments as you want to give it. 

However, other commands won't be so lenient! So, whenever you have some text as an argument, make sure to surround it with `"`, so the shell understands what you mean, since the shell (by default) determines the list of arguments by spaces

As another aside, there are 2 types of quotes: `'` (single quotes) and `"` double quotes. The main difference is that `'` does not expand `$` variable reference (which you'll learn later in this tutorial), whereas `"` does.

### `printf`: Print out text, formatted

The next command, `printf`, is very similar to `echo`. However, there are some key differences:

  * `printf` uses a format string as the first argument, with `%` placeholders
  * `printf` does not automatically add a linebreak (you need to add one yourself if that is what you want)
  * `printf` allows formatting numbers, while `echo` just treats them as text

Here is an example:

```shell
$ printf 'hello, world\n'
```

(notice: the `\n` is called an 'escape sequence'. the 'n' means 'newline')

Here are some examples showing numbers:

```shell
$ printf 'year: %i\n' 2021
year: 2021
$ printf 'year(float): %f\n' 2021
year: 2021.000000
$ printf 'val: %i %i %i\n' 1 2 3
val: 1 2 3
$ printf 'val: %f %f %f\n' 1 2 3
val: 1.000000 2.000000 3.000000
# Notice, '.2f' tells it to only include 2 digits after the decimal point
$ printf 'val: %.2f %.2f %.2f\n' 1 2 3
val: 1.00 2.00 3.00
```


## Variables

Up until this point, we have been executing commands with text as arguments. However, we will often want to deal with variables which can change.

To assign to a variable, you can use the `=` operator:

```shell
$ NAME="YourNameHere"
```

You can re-assign to the same variable over and over, the last value assigned is the one used. You can retreive a variable's value with the `$` operator (I know, it may be confusing because we also use that symbol to denote the start of lines). The reference with `$` will be replaced with the contents of the variable (or an empty string if the variable hasn't been defined).

For example:

```shell
$ echo $NAME
YourNameHere
```



