---
layout: post
title: "Kata (#2) - First Compiler (ASTs)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ast-0.svg
---

Using our tokenizer/lexer created in the last post for Kata, we are now going to transform the token stream into an [Abstract Syntax Tree](https://en.wikipedia.org/wiki/Abstract_syntax_tree), via a recursive descent parser.

<!--more-->

As a refresher, here's the diagram of parts of `ckc`:

![assets/img/kata-ckc-arch.svg](assets/img/kata-ckc-arch.svg)

We've just finished the `Lexer` step, and now we will implement the `Parse` step (partially). This will transform the stream of tokens (which are essentially like 'words' to the computer) into an Abstract Syntax Tree (or, 'AST'). To use the analogy from earlier, if text is just a bunch of numbers to a computer, and tokens are logical groupings of characters into names, numbers, and puncutation, then an AST is like a human brain's understanding of a sentence. When presented with `int x;` an AST will allow the compiler to understand that the developer is declaring a variable called 'x' with a type 'int'.

So, now the question becomes: how do we transform tokens into ASTs? And indeed, this is a challenging problem at first glance. We will define a formal grammar (in [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) format), and then actually implement the parser using a [recursive descent parser](https://en.wikipedia.org/wiki/Recursive_descent_parser). I chose to use a recursive descent parser because they are straightforward to implement and are easy to modify and undsterstand. The syntax of a recursive descent parser closely mirrors the grammar it is describing.

## ASTs

I'm going to take an aside here and talk about ASTs for a moment, because you will need the ideas bouncing in your head as you write the compiler to fully appreciate them.

ASTs represents the program in a format of a tree -- that is to say a structure in which there are nodes (often shown as oval/circle shaped shapes) and each node has 0 or more children (which they point to with arrows). The top of an AST is the actual result of the program, and it will use the children to determine the result. To me, they're kind of beautiful. But, that's definitely up to personal interpretation

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

We won't be doing the actual computation (LLVM will do it for us), but we first need to challenge of transforming the token stream we created last post into this AST representation, so let's hop back into `ckc`. I just thought I'd cover ASTs so you know what they are, and hopefully begin to appreciate how useful they are


### AST Implementation

We'll be storing ASTs as a tree-like structure, where each AST holds a list of child ASTs

Our AST implementation will be:

```c++

/* Abstract Syntax Tree - represents program semantics in an abstract way
 *
 * Technically, this is kind of a mash up of a few types:
 *   * AST
 *   * DAG (Directed Acyclic Graph), because children of two seperate ASTs
 *       may be the same
 *   * Parse Tree, because it also contains information about where in the source
 *       code it was located
 */
struct AST {

    /* What kind of AST is it? */
    enum Kind {
        KIND_NONE = 0,

        /* List of statements */
        KIND_BLOCK,

        /* Constants */
        KIND_INT,
        KIND_STR,

        /* Variable */
        KIND_NAME,

        /* Attribute reference: 'L.R' */
        KIND_ATTR,

        /* Attribute pointer reference 'L->R' */
        KIND_ATTR_PTR,

        /* Function Call/Indexing Call: 'f(a, b)' or 'f[a, b]' */
        KIND_CALL,
        KIND_INDEX,

        /* Binary assignment operators */
        KIND_ASSIGN,
        KIND_BOP_AADD,
        KIND_BOP_ASUB,
        KIND_BOP_AMUL,
        KIND_BOP_ADIV,
        KIND_BOP_AMOD,
        KIND_BOP_ALSH,
        KIND_BOP_ARSH,
        KIND_BOP_AOR,
        KIND_BOP_AXOR,
        KIND_BOP_AAND,

        KIND_BOP_OROR,
        KIND_BOP_ANDAND,

        /* Binary operators */
        KIND_BOP_ADD,
        KIND_BOP_SUB,
        KIND_BOP_MUL,
        KIND_BOP_DIV,
        KIND_BOP_MOD,
        KIND_BOP_LSH,
        KIND_BOP_RSH,
        KIND_BOP_OR,
        KIND_BOP_XOR,
        KIND_BOP_AND,

        KIND_BOP_LT,
        KIND_BOP_LE,
        KIND_BOP_GT,
        KIND_BOP_GE,
        KIND_BOP_EQ,
        KIND_BOP_NE,

        /* Unary operators */
        KIND_UOP_PREINC, // ++x
        KIND_UOP_PREDEC, // --x
        KIND_UOP_PREPOS, // +x
        KIND_UOP_PRENEG, // -x
        KIND_UOP_PRESQIG, // ~x
        KIND_UOP_PRENOT, // !x
        KIND_UOP_PREAND, // &x
        KIND_UOP_PRESTAR, // *x
        KIND_UOP_POSTINC, // x++
        KIND_UOP_POSTDEC, // x--

    } kind;

    /* Token which the AST came from */
    Token tok;

    /* List of children nodes */
    vector< AST* > sub;

    AST(Token tok_, Kind kind_=Kind::KIND_BLOCK)
        : tok(tok_), kind(kind_) {}

    /* Convert to string */
    operator string() const {
        /* convert literals to strings from their tokens */
        if (kind == KIND_INT || kind == KIND_STR) return (string)tok;

        string res = "AST({";
        size_t i = 0;
        for (auto& it : sub) {
            if (i++ > 0) res += ", ";
            res += (string)*it;
        }
        return res + "}, " + to_string(kind) + ")";
    }

    /* Return a symbol representing kind of AST, or "" if it doesn't apply */
    string get_symbol();

    /* Convert to graphviz dotfile format */
    string to_dot();

};

```

It's pretty simple, allows us to create and free ASTs, as well as add children nodes. To add a child node, you will use `ast->sub.push_back(child)`

We could write traversal algorithms now, but we'll just write them for whatever application we want (since we may want special behavior). Also, take note that we aren't using any features of C++ dynamic types, which we may do in the future. For now, however, we'll keep it with a `kind`, and keep the functionality implemented when we use it.

ASTs will not have a associated type that tells the type of the result of an expression is -- we'll cover that when we do code generation (since we don't know what the types of variables are, functions, etc.).

Let's go ahead and have a file `ast.cc` for AST-related routines -- we'll make one to output [graphviz](https://graphviz.org/) code, which we can turn into diagrams (like you've seen in this code, demonstrating how to use ASTs), and another to return a simple symbol for things like operators:


```c++

/* Graphviz dotfile generator state */
struct DotGen {

    /* Current node ID */
    int id;

    /* Allocate new ID */
    int newid() {
        return id++;
    }
};

/* internal method to add an AST to the graphviz output */
static int addast(string& out, DotGen& gen, AST& self) {
    int id = gen.newid();
    vector<int> sub;
    for (auto& it : self.sub) sub.push_back(addast(out, gen, *it));

    string label = "{}";
    if (self.kind == AST::KIND_INT || self.kind == AST::KIND_STR || self.kind == AST::KIND_NAME) {
        label = (string)self.tok;
    } else label = self.get_symbol();

    string indent = (string)"    ";

    /* Add this node */
    out += indent + to_string(id) + " [label=\"" + label + "\"];\n";

    /* Add connections */
    size_t i;
    for (i = 0; i < sub.size(); ++i) {
        out += indent + to_string(id) + " -> " + to_string(sub[i]) + ";\n";
    }

    return id;
}

string AST::to_dot() {
    string res;
    res += "digraph G {\n";

    DotGen gen;
    gen.id = 0;
    addast(res, gen, *this);

    res += "}";
    return res;
}

string AST::get_symbol() {
    AST::Kind k = kind;

    /**/ if (k == AST::KIND_BLOCK) return "{}";

    else if (k == AST::KIND_ATTR) return ".";
    else if (k == AST::KIND_ATTR_PTR) return "->";
    else if (k == AST::KIND_CALL) return "()";
    else if (k == AST::KIND_INDEX) return "[]";
    else if (k == AST::KIND_ASSIGN) return "=";

    else if (k == AST::KIND_BOP_AADD) return "+=";
    else if (k == AST::KIND_BOP_ASUB) return "-=";
    else if (k == AST::KIND_BOP_AMUL) return "*=";
    else if (k == AST::KIND_BOP_ADIV) return "/=";
    else if (k == AST::KIND_BOP_AMOD) return "%=";
    else if (k == AST::KIND_BOP_ALSH) return "<<=";
    else if (k == AST::KIND_BOP_ARSH) return ">>=";
    else if (k == AST::KIND_BOP_AOR) return "|=";
    else if (k == AST::KIND_BOP_AXOR) return "^=";
    else if (k == AST::KIND_BOP_AAND) return "&=";
    
    else if (k == AST::KIND_BOP_OROR) return "||";
    else if (k == AST::KIND_BOP_ANDAND) return "&&";

    else if (k == AST::KIND_BOP_ADD) return "+";
    else if (k == AST::KIND_BOP_SUB) return "-";
    else if (k == AST::KIND_BOP_MUL) return "*";
    else if (k == AST::KIND_BOP_DIV) return "/";
    else if (k == AST::KIND_BOP_MOD) return "%";
    else if (k == AST::KIND_BOP_LSH) return "<<";
    else if (k == AST::KIND_BOP_RSH) return ">>";
    else if (k == AST::KIND_BOP_OR) return "|";
    else if (k == AST::KIND_BOP_XOR) return "^";
    else if (k == AST::KIND_BOP_AND) return "&";

    else if (k == AST::KIND_BOP_LT) return "<";
    else if (k == AST::KIND_BOP_LE) return "<=";
    else if (k == AST::KIND_BOP_GT) return ">";
    else if (k == AST::KIND_BOP_GE) return ">=";
    else if (k == AST::KIND_BOP_EQ) return "==";
    else if (k == AST::KIND_BOP_NE) return "!=";
    else if (k == AST::KIND_UOP_PREINC) return "++ (pre)";
    else if (k == AST::KIND_UOP_PREDEC) return "-- (pre)";
    else if (k == AST::KIND_UOP_PREPOS) return "+";
    else if (k == AST::KIND_UOP_PRENEG) return "-";
    else if (k == AST::KIND_UOP_PRESQIG) return "~";
    else if (k == AST::KIND_UOP_PRENOT) return "!";
    else if (k == AST::KIND_UOP_PREAND) return "&";
    else if (k == AST::KIND_UOP_PRESTAR) return "*";
    else if (k == AST::KIND_UOP_POSTINC) return "++ (post)";
    else if (k == AST::KIND_UOP_POSTDEC) return "-- (post)";
    

    /* Unknown */
    return "";

}
```

As a quick test, let's show how to create ASTs and print them out as dotfiles, changing the `main` function to:

```c++
int main(int argc, char** argv) {
    if (argc != 1 + 1) {
        fprintf(stderr, "usage: %s [file]\n", argv[0]);
        return 1;
    }
    string src_name = argv[1];
    string src = readall(src_name, tokstk.back());
    printerrors();

    vector<Token> toks = tokenize(src_name, src);

    printerrors();
    printwarnings();

    /* construct AST */
    AST* x = new AST(toks[0], AST::KIND_NAME);
    AST* y = new AST(toks[2], AST::KIND_INT);
    AST* z = new AST(toks[1], AST::KIND_BOP_ADD);
    z->sub.push_back(x);
    z->sub.push_back(y);

    cout << z->to_dot() << endl;

	return 0;
}
```

(keep in mind the `[0]`, `[2]`, and `[1]` are hardcoded for the example `xyz + 123`. in the future, we'll create it dynamically with the parser). Running this example gives:

```
$ cat ex.kata
xyz + 123
$ make && ./ckc ex.kata
digraph G {
    1 [label="xyz"];
    2 [label="123"];
    0 [label="+"];
    0 -> 1;
    0 -> 2;
}
$ make && ./ckc ex.kata | dot -Tpng -o ex.png
$ make && ./ckc ex.kata | dot -Tsvg -o ex.svg
```

(if you don't have the `dot` tool, [install it from here](https://graphviz.org/download/))

This should create an image that looks like this:

![assets/img/kata-ckc-ex.svg](assets/img/kata-ckc-ex.svg)

So, now we have a working AST implementation that we can output and diagram to debug and see the result of our parser.


### Parser Implementation

I mentioned earlier that we would use a [recursive descent parser](https://en.wikipedia.org/wiki/Recursive_descent_parser) to actually parse it. Here's the [EBNF](https://en.wikipedia.org/wiki/Extended_Backus%E2%80%93Naur_form) we'll start out with:

```
PROGRAM     : STMT*

STMT        : ';'
            | '{' STMT* '}'
            | EXPR ';'

EXPR        : ATOM

ATOM        : NAME
            | INT
            | STR
```

Where `PROGRAM`, `STMT`, `EXPR`, and `ATOM` are called "production rules" (or, "rules" from here on out), and `NAME`, `INT`, `STR` are the token types that our lexer outputs. The string constants, like `;`, `{`, and `}`, are also tokens (like `TOK_SEMI`). We refer to them in the EBNF as their string constants, but the parser will check the token types. A rule is said to "match" (or describe) a string of tokens if the tokens can be organized according to it. So, if we had the rules: `A : B B` and `B : 'c'`, then the input `cc` would match `A`, but `c` would not, since there was only 1 `c`, but there are 2 `B` rules in `A`, which must both consume a `c` token. The multiple lines describes an either-or scenario. So, if the first line doesn't match, then the second line is tried. Then repeat, until you've tried every line in the rule. If none match, then the input string does not match the symbol.

The first rule of an EBNF is special; this rule must represent the entire input (i.e. file) that it is given, so there cannot be any extra characters that aren't part of `STMT*`. If so, we should signal an error. All the rules in the grammar above tell us what are valid constructs in our language. So, an expression (called `EXPR`) is an `ATOM`, which is in turn either a `NAME`, `INT`, or `STR`. The `*` operator (like `STMT*`) means that it must be matched 0 or more times. So, `STMT*` would match ` ` (the empty string), `STMT`, `STMT STMT`, `STMT STMT STMT`, and so on. 

In the future, we'll add more complicated expression rules to allow things like operators, parentheses, and so on, but let's show the code and utilities needed to implement this much:



So, let's create a file called `parse.cc`, and define some functions in `kc.hh`:

```c++

/* Parse an entire file, and return an AST for it. Return NULL if there were errors */
AST* parse_file(vector<Token>& toks);

```


The following code shows how a recursive descent parser is implemented. Functions for each rule are defined, and calling the function attempts to match the current position in the token stream with that rule, and return an AST representing it. If it could not be done, `NULL` is returned and an error is added to the global error list. Rules that get a `NULL` from a call to another rule should clean up and return `NULL` themselves, if that was a required part of the definition of that rule.

```c++
/* Kata's EBNF: a formal specification for what tokens make up various parts of
 *   the language. 
 *
 * PROGRAM      : STMT*
 * 
 * STMT         : ';'
 *              | '{' STMT* '}'
 *              | EXPR ';'
 * 
 * EXPR         : ATOM
 * 
 * ATOM         : NAME
 *              | INT
 *              | STR
 */

/* Defines a grammar rule */
#define RULE(_name) static AST* R_##_name(vector<Token>& toks, int& toki)

/* Consume a subrule, or return NULL if it did not match */
#define SUB(_name) R_##_name(toks, toki)


/* Get current token that hasn't been consumed yet */
#define TOK toks[toki]

/* Check  */
#define DONE (toki >= toks.size() - 1)

/* Consume a token */
#define EAT() toks[toki++]

/* Forward declarations */
RULE(PROGRAM);
RULE(STMT);
RULE(EXPR);
RULE(ATOM);

RULE(STMT) {
    int s = toki; /* keep track of start in case we have to rewind */
    if (TOK.kind == Token::KIND_SEMI) {
        /* Empty, but don't return NULL since there was no problem accepting it */
        return new AST(EAT(), AST::KIND_BLOCK);
    } else if (TOK.kind == Token::KIND_LBRC) {
        AST* res = new AST(EAT(), AST::KIND_BLOCK);
        
        /* Keep parsing statements (recursively) until we hit the end of the block */
        while (!DONE && TOK.kind != Token::KIND_RBRC) {
            AST* sub = SUB(STMT);
            if (!sub) return NULL;
            res->sub.push_back(sub);
        }

        if (TOK.kind == Token::KIND_RBRC) {
            /* Found end */
            EAT();
            return res;
        } else {
            /* No end found */
            errors.push_back(Error(toks[s], "no end to block started here"));
            toki = s;
            return NULL;
        }
    } else {
        /* try: EXPR ';' */
        AST* res = SUB(EXPR);
        if (!res) {
            toki = s;
            return NULL;
        }

        if (TOK.kind == Token::KIND_SEMI) {
            /* Found end, consume and return */
            EAT();
            return res;
        } else {
            /* There was an expression, but ';' was missing */
            errors.push_back(Error(TOK, "unexpected token, expected a ';' here to end statement"));
            toki = s;
            return NULL;
        }
    }
}

RULE(EXPR) {
    return SUB(ATOM);
}


RULE(ATOM) {
    if (TOK.kind == Token::KIND_NAME) {
        return new AST(EAT(), AST::KIND_NAME);
    } else if (TOK.kind == Token::KIND_INT) {
        return new AST(EAT(), AST::KIND_INT);
    } else if (TOK.kind == Token::KIND_STR) {
        return new AST(EAT(), AST::KIND_STR);
    } else {
        return NULL;
    }
}


AST* parse_file(vector<Token>& toks) {
    /* Start at the first token, and accept the entire program */
    int toki = 0;
    return SUB(PROGRAM);
}

```

And, let's change the `main` function to this:

```c++
int main(int argc, char** argv) {
    if (argc != 1 + 1) {
        fprintf(stderr, "usage: %s [file]\n", argv[0]);
        return 1;
    }
    string src_name = argv[1];
    string src = readall(src_name, tokstk.back());
    printerrors();

    vector<Token> toks = tokenize(src_name, src);

    printwarnings();
    printerrors();

    /* parse from file */
    AST* prog = parse_file(toks);

    printwarnings();
    printerrors();

    cout << prog->to_dot() << endl;

	return 0;
}
```

Let's try running it with our current example:

```
$ cat ex.kata
xyz + 123
$ make && ./ckc ex.kata
ex.kata:1:4: error: expected a ';' here
xyz + 123
```
The problem is that we don't have any rule that accepts `+`, and we don't have `;` in our example, which is required to end a statement (and thus anything in `PROGRAM`). Let's change `ex.kata` to this:

```
xyz;
123;
{
    a;
    b;
}
c;
```

Try it again:

```
$ make && ./ckc ex.kata
digraph G {
    13 [label="xyz"];
    14 [label="123"];
    16 [label="a"];
    17 [label="b"];
    15 [label="{}"];
    15 -> 16;
    15 -> 17;
    18 [label="c"];
    12 [label="{}"];
    12 -> 13;
    12 -> 14;
    12 -> 15;
    12 -> 18;
}
```

We could check this manually, or again use the `dot` commandline:
```
$ make && ./ckc ex.kata | dot -Tpng -o ex.png
```

It should look like this:

![assets/img/kata-ckc-ex1.svg](assets/img/kata-ckc-ex1.svg)


Great! Our parser seems to be working on simple input that fits our simple grammar. You'll notice that it shows the hierarchy of blocks. This will be important when discussing scopes, the fact that it correctly handles nested blocks.

Well, now is time for congratulating yourself: You've successfully written a recursive descent parser.

We'll start implementing other rules, at which point you might diverge from copying this tutorial exactly and start making decisions about your own language, and how it should be structured.
