---
layout: post
title: "Kata (#2) - First Compiler (Parsing)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ast-0.svg
---

Using our tokenizer/lexer created in the last post for Kata, we are now going to parse the token stream into an [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree), via a recursive descent parser.

<!--more-->

As a refresher, here's the diagram of parts of `ckc`:

![assets/img/kata-ckc-arch.svg](assets/img/kata-ckc-arch.svg)

We've just finished the `Tokenize` step, and now we will implement the `Parse` step. This will transform the stream of tokens (which are essentially like 'words' to the computer) into an Abstract Syntax Tree (or, 'AST'). To use the analogy from earlier, if text is just a bunch of numbers to a computer, and tokens are logical groupings of characters into names, numbers, and puncutation, then an AST is like a human brain's understanding of a sentence. When presented with `int x;` it understands that you are declaring a variable called 'x' with a type 'int'.

So, now the question becomes: how do we transform tokens into ASTs? And indeed, this is a challenging problem at first glance. The EBNF we described earlier in the series tells us which sequences of tokens match a program -- those which match the `program` production rule. But, we need to find out if a given sequence of tokens fits that rule.

How do we do this? Well, we assume that it is, and we parse the AST using a [recursive descent parser](https://en.wikipedia.org/wiki/Recursive_descent_parser). I chose to use a recursive descent parser because they are straightforward to implement and are easy to modify and undsterstand. The syntax of a recursive descent parser closely mirrors the grammar it is describing.

## ASTs

I'm going to take an aside here and talk about ASTs for a moment, because you will need the ideas bouncing in your head as you write the compiler to fully appreciate them.

For basic expressions, AST represents the program in a format of a tree -- that is to say a structure in which there are nodes (often shown as oval/circle shaped shapes) and each node has 0 or more children (which they point to with arrows). The top of an AST is the actual result of the program, and it will use the children to determine the result. To me, they're kind of beautiful. But, also, I'm a nerd, so you should take that with a grain of salt. 

Let's take a somewhat simple expression and analyze it. Note that this syntax isn't Kata specific, it's just a math expression: `x * (1 + y) + f(x, y, 2)`. I haven't told you what `x`, `y`, or `f` are, but you can recognize the expression as valid (`x`, `y` are probably numbers, and `f` is a function). If I gave you more information, you could tell me the result.

For example, if I told you: `x = 1, y = 2, f(a, b, c) = a + b + c`, you could easily reduce the expression as follows:

```
  x * (1 + y) + f(x, y, 2)
= 1 * (1 + 2) + ((1) + (2) + (2))
= 1 * 3 + (5)
= 3 + 5
= 8
```

You may not have realized it, but you just parsed the expression, and followed [order of operation (commonly called PEMDAS)](https://en.wikipedia.org/wiki/Order_of_operations) to evaluate it. Essentially, we are going to program a computer to do this automatically.

If you think about it, try and draw a tree where each 'node' is either an operator that has children which are its operands, or are constants, or are a variable name (like `x`). Function calls will have their arguments as their children. You should end up with something that looks like the below:

![assets/img/kata-ast-0.svg](assets/img/kata-ast-0.svg)

If you already have an expression in this format, evaluating it is as follows (starting at the top node):

  1. If the current node is a constant, return this value
  2. If the current node is a variable, look up and return the value for the given name
  3. If the current node is an operator, repeat these steps for each of its children, and then apply the operator with the children's values and return that value
  4. If the current node is a function, repeat these steps for each of its children, and then apply/call the function itself with a list of the values returned by the children, and return the result from the function call
In abstract programming terms, we could define a function `eval(ast)`, that works like this:

```
func eval(ast) {
    if ast.kind == CONSTANT, return ast.value
    else if ast.kind == VARIABLE, return lookup(ast.name)
    else if ast.kind == OPERATOR {
        if ast.operator == '+', return eval(ast.children[0]) + eval(ast.children[1])
        else if ast.operator == '*', return eval(ast.children[0]) * eval(ast.children[1])
        else {
            error('unknown operator')
        }
    } else if ast.kind == FUNCTION {
        args = [] 
        for child in ast.children {
            args.push(eval(ast))
        }
        function = lookup(ast.name) # find the function it references
        return function(args)
    }
}

```

This is what we as humans already do when we encounter an expression, we just have internalized it and became so good we don't think about it. Let's look at how to apply this to our AST above. In the diagrams below, grey means that that node is currently figuring out its value. Green means that it has already found its value. Arrows downwards represents a recursive call to that node. Arrows upwards mean it returns that value from the recursive call.

Remember that `f(a, b, c) := a + b + c`

First, we run `eval(top)`. This call triggers two recursive calls to each of the children, and turns the top node grey, since it is trying to figure out its value (but needs its children first):

![assets/img/kata-ast-eval-0.svg](assets/img/kata-ast-eval-0.svg)

Evaluating all the children causes more recursive calls. At this point, no nodes have returned their value yet.

![assets/img/kata-ast-eval-1.svg](assets/img/kata-ast-eval-1.svg)


Now, some of the children called with `eval()` are either variables or constants, so they will start returning back upwards (and setting their color to green to indicate they are done):

![assets/img/kata-ast-eval-2.svg](assets/img/kata-ast-eval-2.svg)


Now, all of the leaf nodes have found their values, and the right hand side is done:

![assets/img/kata-ast-eval-3.svg](assets/img/kata-ast-eval-3.svg)

Now, there's only one path of unresolved `eval()` calls. So, those quickly get bubbled up, leaving us with the top node knowing both of its children (which have values `3` and `5`):

![assets/img/kata-ast-eval-4.svg](assets/img/kata-ast-eval-4.svg)

The only thing left to do is now evaluate `3 + 5` which is easy to do. And, with that completed, we have the result: `8`. 


Whew! That was quite an example, but hopefully the diagrams made it easier to understand. A few interesting properties of evaluating ASTs like this are:

  1. Children of a node will turn green (i.e. calculate their value) before the parent
  2. Parentheses are irrelevant at this point
  3. It has been demonstrated that this method will work for computer evaluation (which is needed for the compiler)

We'll write the evaluator in a later part, but we first need to challenge of transforming the token stream we created last post into this AST representation, so let's hop back into `ckc`. I just thought I'd cover ASTs so you know what they are, and hopefully begin to appreciate how useful they are

### AST Implementation

Our AST implementation will be quite simple:


```c

/* ... in 'kc.h' */

/* Abstract Syntax Tree (AST) representing a program which is understandable by a computer */
typedef struct ast_s* ast;
struct ast_s {
    enum {
        /* atoms */
        AST_INT,
        AST_FLOAT,
        AST_STRING,
        AST_NAME,

        /* misc. operations */
        AST_CALL,
        AST_SUBSCRIPT,
        AST_ATTR,

        /* binary operators */
        AST_BOP_ASSIGN,
        /* ... */
        AST_BOP_MOD,

        /* unary prefix operators */
        AST_UOP_INC,
        /* ... */
        AST_UOP_TYPEOF,

        /* unary postfix operators */
        AST_UOP_INC_POST,
        AST_UOP_DEC_POST,

        /* definitions */
        AST_DEF_FUNC,
        AST_DEF_STRUCT,
        AST_DEF_ENUM,

        /* variable declarations */
        AST_DECL,

        /* misc. statements */
        AST_BLOCK,
        AST_IF,
        AST_WHILE,
        AST_FOR,
        AST_RETURN,

    } k;

    /* children of the AST */
    int n_sub;
    ast* sub;

    /* string value (if not-NULL) */
    char* val_s;

    /* integer value */
    intptr_t val_i;

    /* extra information (used per backend, 'struct EXTRA' is defined in the code
     *   generator) */
    struct EXTRA* extra;

};

/* Create a new AST */
ast ast_new(int k);

/* Push a child of an AST */
ast ast_push(ast self, ast sub);

/* Free an AST (and its children) */
void ast_free(ast self);

/* Returns string name for AST kind */
const char* ast_k_name(int k);

```

```c
/* ast.c - implementation of Abstract Syntax Trees
 *
 * @author:    Cade Brown <cade@cade.site>
 */
#include <kc.h>

ast ast_new(int k) {
    ast self = malloc(sizeof(*self));

    self->k = k;

    self->extra = NULL;
    self->val_s = NULL;
    self->n_sub = 0;
    self->sub = NULL;

    return self;
}

ast ast_push(ast self, ast sub) {
    int i = self->n_sub++;
    self->sub = realloc(self->sub, sizeof(*self->sub) * self->n_sub);
    self->sub[i] = sub;
}

void ast_free(ast self) {
    int i;
    for (i = 0; i < self->n_sub; ++i) {
        ast_free(self->sub[i]);
    }
    free(self->sub);
    free(self->val_s);
}

const char* ast_k_name(int k) {
/* stringify the enum constant, and then add '4' to skip over the 'AST_' prefix (4 characters) */
#define _K(_k) else if (k == _k) return (#_k) + 4;
    if (0) {}
    _K(AST_INT)
    /* ... */
    _K(AST_RETURN)

    else {
        return "<unknown>";
    }
}

```

It's pretty simple, allows us to create and free ASTs, as well as add children nodes. We could write traversal algorithms now, but we'll just write them for whatever application we want (since we may want special behavior). 


We use `ast_push(self, child)` to add `child` to the list of sub-nodes for `self`.

We use `intptr_t` for the integral value, since that will be the largest (native) integer size we really need to deal with.

You'll notice we have also added `struct EXTRA* extra;` as a member. We haven't defined what `struct EXTRA` is yet, because we may want it to be different per backend or per application. So, we just default to setting it to `NULL` and don't touch it after that.

If we are to construct our earlier example, we can do it programmatically (in `main`):

```c
char* newstr(int len, const char* val) {
    if (len < 0) len = strlen(val);

    char* r = malloc(len + 1);
    memcpy(r, val, len);
    r[len] = '\0';

    return r;
}

/* pretty-print an AST, with indentation levels per depth */
void ast_pprint(int n_stk, ast p) {
    int i;
    for (i = 0; i < n_stk; ++i) printf("  ");

    printf("%s ", ast_k_name(p->k));
    if (p->n_sub == 0) {
        if (p->val_s) {
            printf("%s", p->val_s);
        } else {
            printf("%lli", (long long int)p->val_i);
        }
        printf("\n");

    } else {
        printf("[%i]\n", p->k, p->n_sub);
        for (i = 0; i < p->n_sub; ++i) {
            /* recursively call with more depth */
            ast_pprint(n_stk+1, p->sub[i]);
        }
    }
}

int main(int argc, char** argv) {
    if (argc != 1 + 1) {
        fprintf(stderr, "usage: %s [file]\n", argv[0]);
        return 1;
    }
    int i;

    char* file = argv[1];
    char* src = readall(file);

    fprintf(stderr, "compiling kata source in '%s'\n", file);

    int n_tok;
    tok_t* tok = tokenize(file, src, &n_tok);

    printf("tokens[%i]\n", n_tok);
    for (i = 0; i < n_tok; ++i) {
        printf("  %2i: '%.*s'\n", i, tok[i].len, src + tok[i].pos);
    }

    ast x = ast_new(AST_NAME);
    x->val_s = newstr(1, "x");
    ast y = ast_new(AST_NAME);
    y->val_s = newstr(1, "y");
    ast f = ast_new(AST_NAME);
    f->val_s = newstr(1, "f");
    ast v1 = ast_new(AST_INT);
    v1->val_i = 1;
    ast v2 = ast_new(AST_INT);
    v2->val_i = 2;

    /* top = 'x * (1 + y) + f(x, y, 2)' */
    ast top = ast_new(AST_BOP_ADD);
    /* top.L = 'x * (1 + y)' */
    ast topL = ast_new(AST_BOP_MUL);
    /* top.L.R = '1 + y' */
    ast topLR = ast_new(AST_BOP_ADD);
    /* top.R = 'f(x, y, 2)' */
    ast topR = ast_new(AST_CALL);

    ast_push(top, topL);
    ast_push(top, topR);
    ast_push(topL, x);
    ast_push(topL, topLR);

    ast_push(topLR, v1);
    ast_push(topLR, y);

    /* small modification: a function call has 'sub[0]' be the function object its calling, 
         the rest are the arguments */
    ast_push(topR, f);
    ast_push(topR, x);
    ast_push(topR, y);
    ast_push(topR, v2);

    ast_pprint(0, top);

}
```

When we print it out using `ast_pprint()`, we get the following output (indentation shows which are parents and children)

```
BOP_ADD [2]
  BOP_MUL [2]
    NAME x
    BOP_ADD [2]
      INT 1
      NAME y
  CALL [4]
    NAME f
    NAME x
    NAME y
    INT 2
```

So, we've successfully gotten an AST implementation working! Now, we need to construct them from the list of tokens instead of hard coding it.


### Parser Implementation

I mentioned earlier that we would use a [recursive descent parser](https://en.wikipedia.org/wiki/Recursive_descent_parser) to actually parse it. So, let's create a file called `parse.c`, and define some functions in `kc.h`:

```c

/* Return an AST representing an entire program. 'name' and 'src' are just
 *   for message purposes
 */
ast parse_prog(const char* name, const char* src, int n_tok, tok_t* tok);

```


```c
/* parse.c - transforms array of tokens into an AST
 *
 * @author:    Cade Brown <cade@cade.site>
 */
#include <kc.h>

/* Defines a grammar rule */
#define RULE(_name) static ast R_##_name(const char* name, const char* src, int* _toki, tok_t* tok)

/* Sub rule, when one rule must use another one in its definition */
#define SUB(_name) R_##_name(name, src, _toki, tok)


/* Forward Declaration */
RULE(program);

ast parse_prog(const char* name, const char* src, int n_tok, tok_t* tok) {
    int toki = 0;
    int* _toki = &toki;
    ast res = SUB(program);
    return res; 
}

/* Helpful macros for token index, current token, comparison, etc */
#define toki (*_toki)
#define CUR (tok[toki])
#define NEXT (tok[toki+1])
#define EAT() (tok[toki++])
#define EQ(_tok, _str) ((_tok).len == (sizeof(_str) - 1) && strncmp(src+(_tok).pos, _str, (_tok).len) == 0)
#define STR(_tok) newstr((_tok).len, src+(_tok).pos)

RULE(program) {
    ERR("%s: invalid program", name);
    return NULL;
}

```

And, we will call this function in `main`:

```c
    /* ... 
    printf("tokens[%i]\n", n_tok);
    for (i = 0; i < n_tok; ++i) {
        printf("  %2i: '%.*s'\n", i, tok[i].len, src + tok[i].pos);
    }
    */

    /* Parse and print AST */
    ast prog = parse_prog(file, src, n_tok, tok);
    ast_pprint(0, prog);
```

If we re-run, we should get:

```
$ make && ./ckc test.k
cc -I. -c -fPIC main.c -o main.o
cc -I. tok.o main.o parse.o ast.o -o ckc
compiling kata source in 'test.k'
error: test.k: invalid program
```

Great! Our error reporting is working. Now, let's define the rules of the parser, according to the EBNF.

### Rules

I'll explain again: rules for a grammar are ways to write a syntactical element. Given a rule like `dotname = NAME ('.' NAME)*`, we can deduce that a `dotname` can be any `NAME`, with any number (0 or more) named attributes afterwards. So, here are some valid dotnames: `Name`, `MyName`, `My_name`, as well as `My.Name`, `A.Very.Long.Name`. Examples that aren't valid dotnames are: `My.1` (`1` is not a valid `NAME`), `My.` (does not end with a `NAME`). 

A function implmenting a rule should return the AST it produces, or `NULL` if it doesn't match. And, if a rule doesn't match, we shouldn't always throw an error. Take, for example, the definition of a statement: `stmt =  ... | decl ';' | expr ';'`. If we have the following code:

```
myname;
```

The initial parse for `decl` will find that `myname` is (syntactically) correct to be parsed as a `type` (and match the first half of `decl = type NAME`). However, the next token is `;`, which is not a valid `NAME`, and thus the rule for `decl` fails, meaning that `myname;` is not a valid declaration. However, the next possible match for `stmt` (`expr ';'`) will match, since `myname` is a valid expression. Thus, if we had thrown an error of `invalid declaration`, then the entire parser would halt and throw an error, when really we just want to go to the next valid completion of `stmt`. Therefore, instead of throwing an error, the `decl` rule must return NULL and not consume any input.

Here's how we'll parse `decl` (keep in mind the `RULE()` macro defines the correct function signature for a rule, so we don't have boilerplate all over our code):

```c
/* decl           = type NAME ('=' expr)? */
RULE(decl) {
    int s = toki;
    ast type = SUB(type);
    if (!type) {
        toki = s;
        return NULL;
    }

    ast NAME = SUB(NAME);
    if (!NAME) {
        toki = s;
        ast_free(type);
        return NULL;
    }

    ast res = ast_new(AST_DECL);
    ast_push(res, type);

    /* ('=' expr)? */
    if (EQ(CUR, "=")) {
        EAT();
        ast target = ast_new(AST_BOP_ASSIGN);
        ast_push(target, NAME);
        ast_push(res, target);
        ast val = SUB(expr);
        if (!val) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        ast_push(target, val);

    } else {
        ast_push(res, NAME);
    }

    return res;
}
```

You should notice that we use the `SUB()` macro to fill in other rules which are a part of the `decl` rule. If those return NULL, then we abandon the attempt to parse `decl`, rewind to the start position (which was captured with `s = toki`, i.e. the token index before any input was consumed), free anything allocated thus far, and return NULL.


We can fill in rules we haven't defined with:

```
RULE(expr) {
    return NULL;
}
```

And we can implement them later. Let's go ahead and implement the minimal amount of rules to match the following text: `int x;`:

```c
/* parse.c - transforms array of tokens into an AST
 *
 * @author:    Cade Brown <cade@cade.site>
 */
#include <kc.h>

/* Defines a grammar rule */
#define RULE(_name) static ast R_##_name(const char* name, const char* src, int* _toki, tok_t* tok)

/* Sub rule, when one rule must use another one in its definition */
#define SUB(_name) R_##_name(name, src, _toki, tok)


/* Forward Declaration */
RULE(program);

ast parse_prog(const char* name, const char* src, int n_tok, tok_t* tok) {
    int toki = 0;
    int* _toki = &toki;
    ast res = SUB(program);
    return res; 
}

/* Helpful macros for token index, current token, comparison, etc */
#define toki (*_toki)
#define CUR (tok[toki])
#define NEXT (tok[toki+1])
#define EAT() (tok[toki++])
#define EQ(_tok, _str) (strncmp(src+(_tok).pos, _str, (_tok).len) == 0)
#define STR(_tok) newstr((_tok).len, src+(_tok).pos)


RULE(NAME) {
    if (CUR.k != TOK_NAME) return NULL;
    ast res = ast_new(AST_NAME);
    res->val_s = STR(CUR);
    EAT();
    return res;
}

/* dotname        = NAME ('.' NAME)* */
RULE(dotname) {
    if (CUR.k != TOK_NAME) return NULL;
    ast res = ast_new(AST_NAME);
    res->val_s = STR(CUR);
    EAT();

    while (EQ(CUR, ".") && NEXT.k == TOK_NAME) {
        int s = toki;
        EAT();
        ast lhs = res, rhs = ast_new(AST_NAME);
        rhs->val_s = STR(CUR);
        EAT();
        res = ast_new(AST_ATTR);
        ast_push(res, lhs);
        ast_push(res, rhs);
    }

    return res;
}

RULE(expr) {
    return NULL;
}

/* '&' type | type '[' args ']' | 'typeof' E7 | dotname */
RULE(type) {
    int s = toki;
    ast res = NULL;
    if (EQ(CUR, "&")) {
        EAT();
        ast of = SUB(type);
        if (!of) {
            toki = s;
            return NULL;
        }
        res = ast_new(AST_UOP_AND);
        ast_push(res, of);
    } else {
        res = SUB(dotname);
    }

    return res;
}

/* decl           = type NAME ('=' expr)? */
RULE(decl) {
    int s = toki;
    ast type = SUB(type);
    if (!type) {
        toki = s;
        return NULL;
    }

    ast NAME = SUB(NAME);
    if (!NAME) {
        toki = s;
        ast_free(type);
        return NULL;
    }

    ast res = ast_new(AST_DECL);
    ast_push(res, type);

    /* ('=' expr)? */
    if (EQ(CUR, "=")) {
        EAT();
        ast target = ast_new(AST_BOP_ASSIGN);
        ast_push(target, NAME);
        ast_push(res, target);
        ast val = SUB(expr);
        if (!val) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        ast_push(target, val);

    } else {
        ast_push(res, NAME);
    }

    return res;
}


RULE(program) {
    ast res = ast_new(AST_BLOCK);
    while (CUR.k != TOK_EOF) {
        ast sub = SUB(decl);
        if (!sub) {
            ast_free(res);
            res = NULL;
            break;
        }
        ast_push(res, sub);
        if (!EQ(CUR, ";")) {
            ast_free(res);
            res = NULL;
            break;
        }
        EAT();
    }

    if (!res) {
        ERR("%s: invalid program", name);
    }
    return res;
}

```

If we run and compile, with the new `test.k`, we will get the following:

```
$ cat test.k
/* a comment */
int x;
$ make && ./ckc test.k
cc -I. -c -fPIC parse.c -o parse.o
cc -I. tok.o main.o parse.o ast.o -o ckc
compiling kata source in 'test.k'
BLOCK [1]
  DECL [2]
    NAME int
    NAME x
```

Wow! It's working. Notice that no error was reported, and the AST was printed as we expect. Let's try with a different program:

```
$ cat test.k
/* a comment */
int x;
random text
$ ./ckc test.k
compiling kata source in 'test.k'
error: test.k: invalid program
```

It would be nice to have a nicer error message like `error: test.k(L3,C0): unexpected 'random'`, but that isn't important for this initial implementation, we'll add that when we fully implement it.

Well, now is time for congratulating yourself: You've successfully written a recursive descent parser. The hardest part of the parser is already done. Now, we just need to implement the rest of the rules, which we'll cover next time.



