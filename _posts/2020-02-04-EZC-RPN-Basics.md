---
title: "EZC & RPN Basics"
layout: post
categories:
  - RPN
  - languages
tags:
  - content
image:
  feature: ezc_0.jpg
---

This post is about [Polish Notation](https://en.wikipedia.org/wiki/Polish_notation), [Reverse Polish Notation (RPN)](https://en.wikipedia.org/wiki/Reverse_Polish_notation), and my programming language [EZC](http://chemicaldevelopment.us/ezc). It is a programming language that is written in RPN syntax, and generally short syntax. Although most people have difficulty understanding at first, it makes some thing simpler, and some things more beautiful. For example, there are no parentheses required in EZC.

It is also entirely stack based (i.e. everything happens on the stack). Read on to find out more!

<!--more-->

For people who don't have any experience, let me explain.

## Infix Notation (i.e. the standard)

Let's say you want to write an expression, say `2 * (x + 3)`. The way (most) people write this is in what's called "infix" notation, because the operator (such as `+`, `*` in our example) is in between the numbers/variables it applies to. Most people are accustomed to this format of writing formulas & equations, for a number of reasons. There is also what's called operator precedence, or, commonly called `PEMDAS`. So, you look through the input and apply the highest precedence operators first. Parentheses override any precedence, so always compute the inside of parentheses first.

This seems all good, what's the problem?

Well, this format is actually extremely inefficient for computing results. Why? Well, for starters, since the one operand comes before the operator and one comes after, you can't do anything until you've scanned the entire expression. Furthermore, you have to go back and forth looking over and over again at different left and right sides, determining their precedence and thus order. Also, there are some computations which are not even possible without using parentheses. For example, the one I gave (`2 * (x + 3)`) can not be written like `2 * x + 3`, because that is not the same result. So, you need parentheses to express some computatations.

## Comes In PN (Polish Notation)

What's one solution to this? polish notation (also called prefix notation). Some may be familiar with the LISP programming language, or LISP-like syntax. This is effectively polish notation. Now, LISP still requires a lot of parentheses (somewhat famously), but they wouldn't be strictly neccessary in many scenarios.

Prefix notation is just moving the operator from *in*between the values, to before them (i.e. *pre*fixing them)

Take the following equations in infix notation:

* `2 * (x + 3)`
* `1 + 2 + 3 + 4`
* `1 + 2/3 + 4*5/(3 + 4)`

And translate them to pre-fix notation:

* `*(2, +(x, 3))`
* `+(1, +(2, +(3, 4)))`
* `+(1, +(/(2, 3), /(*(4, 5), +(3, 4))))`

Notice how they are effectively functions (i.e. `+` is called with `x, 3` as arguments in the first example), and you'd write it just like you would `f(x)` or `f(x, y)`, but `f` is `+` instead

Since all functions take a constant number of arguments (all take `2` each), we can omit the parentheses, and they become:

* `* 2 + x 3`
* `+ 1 + 2 + 3 4`
* `+ 1 + / 2 3 / * 4 5 + 3 4`

Readable? No? Well, think of it this way: just scan left to right. If the first thing you read is a number, that should be the only thing you read. Otherwise, it should be an operator. If its an operator, you need to repeat this step twice more, reading from the next character, which may itself require children, or children of children.

I have a metaphor that may help explain it:

### Family Trees

In fact, we can consider this a kind of tree. Just imagine each operation being a node in the tree. Some nodes are terminal (i.e. constants, like `5`), and some have children (i.e. the node `+ 3 5` has two children, `3` and `5`), and some may have many generations of children `+ 2 * * 3 4 5`, which is `2+3*4*5` in infix, has the first node `+` with children `2` and `* * 3 4 5`, which itself has children `* 3 4` and `5`, which the first one has children `3` and `4`).

In other words, each operation node has 2 children, and what kind of operator it is tells it what to do with its children. So, the `+` nodes know to add their children, `*` node multiplies theirs, etc.

Reading in and computing an expression starts with the oldest generation of people, and each generation either giving their parents their constant value (if they are just a number), or asking both of their children for a value, then applying their rule to those values, and giving their parents the result.

Consider the expression `* 2 + x 3`. Let's call the first node (the `*` node) the top or "grandparent" node, the `+` node and `2` node "parent" nodes, and `x` and `3` "children" nodes. The "family" tree might look like:

![AST 0]({{site.baseurl}}/images/ast_0.jpg)

The tree on the right side has green arrows indicating when the child had to compute or look up a value, rather than just being a constant.

If we want the result, we first ask the grandparent (`*`) for a value. Since this node is not terminal (i.e. has children), it asks the parents (`2` and `+` for values). `2` responds immediately with `2`, but `+` has to ask its children (`x` and `3`). In this case, we don't know what `x` is, but in a running program, we would then look up what value `x` is, and return that. Let's say that `x=11` for this example.

Now, we go back upwards. `+` now knows its children are `11` and `3`, and so it adds them, and tells its parent `*` that its value is `14`. `*`, now knowing that its children are `2` and `14`, multiplies them, and in turn tells us the final result of `28`.

Now, going back to computing in textual format. We can construct a given tree by first reading a token from the input (i.e. either an operator or a constant). If its a constant, we are done, and just return a simple tree with a single node. Otherwise, we skip the operator, then recursively try and construct 2 more trees, starting directly after the operator. These 2 trees become the children of an operator node.

Then, after the operator reads 2 values, and apply whatever operation to them (i.e. add, subtract, etc).

How do you read a value? Well the same way you can construct a tree! If the next value is a number, just return it, otherwise read the operation, and read 2 more values, etc.

Each time this function that "reads" a value from input is called, the upper level function knows it can now read the next value, just like how the information flows upwards in the family tree diagram

In pseudocode (or, equivalently, Python), we could write this as:

```python

# method to evaluate polish notation input, as a stream of tokens
# i.e. tokens should be a list of numbers, operators, etc
# use str.split() to process the examples
def run_PN(tokens):
  # take the next token out
  cur = tokens[0]
  del tokens[0]
  # compute operators
  if cur == "+":
    return run_PN(tokens) + run_PN(tokens)
  elif cur == "-":
    return run_PN(tokens) - run_PN(tokens)
  elif cur == "*":
    return run_PN(tokens) * run_PN(tokens)
  elif cur == "/":
    return run_PN(tokens) / run_PN(tokens)
  else:
    # just assume it is a float value
    return float(cur)


# print a simple example
print (run_PN("* 2 + 4 5".split()))

# a little more complicated example from above, with
#   an error check with the correct result
print (run_PN("+ 1 + / 2 3 / * 4 5 + 3 4".split()), "should be", (1 + 2/3 + 4*5/(3 + 4)))

```

And voila! You're computing in polish notation!

## Reverse Polish Notation (RPN), or more correctly, `Notation Polish Reversed`

Okay, so if this is the first you've been told about or learned about different ways of writing equations, your head is already spinning. That's okay, but things are about to get a little bit crazier...

Whats even better than polish notation? Reverse Polish Notation!

The problem (I have at least) with polish notation is that it still _delays_ computation until all of the input has finished reading. I.e. we don't know what the result of the `*` node will be, until we know its children. It seems like there is some fundamental law of expression parsing that requires this. After all, both infix and polish notation require this, and it makes sense that you can't know a node until you know all of its children, right?

Well, sort of. The next step in notation we will take is RPN. RPN is like polish notation, but instead of the operator coming before its operands, it comes afterwards. It looks very odd to most people, so don't worry if it doesn't make a lot of sense

For example, we saw that:

`2 * (x + 3)` became `* 2 + x 3` in PN.

In RPN, it becomes `2 x 3 + *`. oh great, another syntax!! I'm so excited Cade, please go on!

Okay, if you insist...

RPN, as its name might suggest, works like polish notation, but reversed. But, how does it know its children, if they come before it? Do we need to parse it backwards? If so, that seems less efficient?

And the answer is no, we don't, and it will actually end up being more efficient

### Enter The Magic Stack

If you like computer science, you'll undoubtedly know what a [Stack](https://en.wikibooks.org/wiki/Data_Structures/Stacks_and_Queues) is. Its just something you can push values on, and pop them back off.

The beauty of RPN is that it doesn't require trees to operate, just a stack. And its implementation is dead simple:

* If the current token is a number, push it on the stack
* If the current token is an operator, pop 2 numbers off the stack, apply the operator, and push the result back on

At the end, the result is on the top of the stack, so just pop it off!

In Python, the implementation is simple:

```python
# evaluate RPN
def run_RPN(toks):
  # set up the execution stack
  stk = []
  # just iterate through all tokens
  for tok in toks:
    # check for operators, then pop off results,
    #   and push back on the result
    if tok == "+":
      b = stk.pop(); a = stk.pop()
      stk.append(a + b)
    elif tok == "-":
      b = stk.pop(); a = stk.pop()
      stk.append(a - b)
    elif tok == "*":
      b = stk.pop(); a = stk.pop()
      stk.append(a * b)
    elif tok == "/":
      b = stk.pop(); a = stk.pop()
      stk.append(a / b)
    else:
      # assume it is a number and push it on
      stk.append(float(tok))
  return stk.pop()

# compute a simple example
print (run_RPN("2 4 5 + *".split()))

```

Note that there is no recursion in this code, it is just an iterative loop through the tokens.

Also, note that we pop them off in reverse order, that's because if we write `a b +`, we mean (in infix) `a + b`, but since we write `a` first, then `b`, that means the stack will look like:

```
# grows this way ->
| a b
```

So, when we pop the values back off, we should pop them in reverse order, since `b` is on top (although, for the `+` operator, it doesn't matter since `a+b == b+a`)

Our example of `2 x 3 + *` would be ran like this:

```
# start with empty stack
|
# encounter '2', so put it on:
| 2
# encounter 'x', look it up (we said that x=11)
| 2 11
# encounter '3', so put it on:
| 2 11 3
# encounter '+', so pop off 2 numbers
| 2
# and push on their sum
| 2 14
# encounter '*', so pop off 2 numbers
|
# push back on their product
| 28
```

And voila! Our answer is revealed

# EZC


Now, we can start talking about [EZC](https://chemicaldevelopment.us/ezc)! (If you haven't ran off, that is)

EZC is basically an entire programming language based directly off the concepts of RPN & Stack-based computing:

* Data first, operations last
* `push` and `pop` are the fundamental operations

If you want to follow along, please follow the [EZC installation guide](https://chemicaldevelopment.us/ezc/#/installing) to get it running on your system. It currently supports Linux (including Raspberry Pis), MacOS, and maybe mingw/cygwin on Windows, although this is not regularly tested

EZC is written, typically into `.ezc` files, much like other programming languages. You can write constants (including integer, floating point, and strings), operators (like `+`, `-`, and `*`), and call functions with the `!` operator

## 'Hello World'

Here's the classic "Hello World" example
```c
"Hello World" print!
```

Running this is as simple as `ec ./hello_world.ezc`, and the output gives:


```bash
$ ec ./hello_world.ezc
Hello World
```

`"Hello World"` is simply a string constant, and actually, `print` is as well.

The `!` operator pops off a single argument (in this case, that argument was `print`), and tries to find a function by that name. the `print` function is a built-in that itself pops 1 item off the stack, and prints it





