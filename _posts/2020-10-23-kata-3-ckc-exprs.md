---
layout: post
title: "Kata (#3) - First Compiler (Parsing Expressions)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ast-0.svg
---

We finally start parsing the cool stuff: operators, precedence, function calls, etc. We're sticking with expressions at this point (not adding things like `if`), but we'll get to those soon.

<!--more-->

### Rules

I'll explain again: rules for a grammar are ways to write a syntactical element. Given a rule like `DOTNAME = NAME ('.' NAME)*`, we can deduce that a `DOTNAME` can be any `NAME`, with any number (0 or more) named attributes afterwards. So, here are some valid dotnames: `Name`, `MyName`, `My_name`, as well as `My.Name`, `A.Very.Long.Name`. Examples that aren't valid dotnames are: `My.1` (`1` is not a valid `NAME`), `My.` (does not end with a `NAME`). 

I'm sure you're familiar with PEMDAS, as I explained in this series. The question for us now is writing a set of rules to parse expressions correctly, while respecting precedence. This will be difficult for most people, even programmers, because it is so embedded in our minds from doing it so often, that we do not often critically think about how we do it. But, for a computer, we must be exact in telling it how to parse the program.

Here are the precedences of different operators in Kata. You are free to choose your own, of course, but I think these make the most sense (in order from least to highest precedence):

|Operator Precdence Chart|
|`=`, `+=`, ... (all assignments)|
|`||` (conditional or)|
|`&&` (conditional and)|
|`|` (bitwise inclusive or)|
|`^` (bitwise exclusive or)|
|`&` (bitwise and)|
|`<` (less than), `>` (greater than), `<=` (less than or equal to), `==` (equal to), `!=` (not equal to)|
|`<<` (bitwise shift left), `>>` (bitwise shift right)|
|`+` (addition), `-` (subtraction)|
|`*` (multiplication), `/` (division), `%` (modulo)|
|`++` (prefix increment), `--` (prefix decrement), `+`, `-`, `~`, `!`, `&`, `*`, `typeof`, `sizeof`|
|`.` (attribute), `->` (attribute via pointer), `++` (postfix increment), `--` (postfix decrement), function call, index operation|


Obviously, using `()` will overrule any specific precedences. In addition, the assignment operators are right-associative, which means that `a = b = c` is implicitly parsed the same as `a = (b = c)` (right associative means the parentheses are on the right hand side by default). By contrast, the other binary operators are left-associative, for example with `+`, we have that `a + b + c` is parsed the same as `(a + b) + c`. This will make a slighy difference in those rules.

So, we need to write a set of rules that enforces this. One way to do this is via a set of rules in order of precedence


### Implementing The Rules


Looking at the chart of precedence, when we parse, we need to try and frame the problem more exactly: what grammar rules should we recursively call? For example, at the very bottom, the answer will be none, since we will use the `ATOM` rule, which is non-recursive, and takes a single token. However, all the other levels of precedence must recursively call the rule below it. So, the `+`/`-` rule should recursively call the `*`/`/`/`%` rule and consume `+`/`-` tokens in between them.

When you think about it, this is kind of how humans do it: we try and find products in between sum (`+`) symbols. So, our grammar will resemble this. I'm going to go ahead and define 1 rule per level of operator precedence

|Rule|Operator(s)|
|E0|`=`, assignments|
|E1|`||`|
|E2|`&&`|
|E3|`|`|
|E4|`^`|
|E5|`&`|
|E6|`<`, `>`, `<=`, `>=`, `==`, `!=`|
|E7|`<<`, `>>`|
|E8|`+`, `-`|
|E9|`*`, `/`, `%`|
|E10|`++`, `--`, `+`, `-`, `~`, `!`, `&`, `*`, `typeof`, `sizeof` (unary)|
|E11|`.`, `->`, `++`, `--`, function call, index operation|


If we use the logic of "rule below us, seperated by our symbol", we can start to derive rules like the following:

#### Binary Operators

```
E8          : E8 '+' E9
            | E8 '-' E9 
            | E9
```

We add an extra rule that allows each rule to decay to the rule under it. This means that if that operator is not used in the expression, it doesn't stop the parser, and the rule is effectively skipped.

There's a small problem with this rule though, and that is the fact that it is [left recursive](https://en.wikipedia.org/wiki/Left_recursion). Some parsers can handle this natively, but our hand-written recursive-descent parser cannot handle this. Think about why this is a problem: if `E8` recursively calls `E8` before any tokens are consumed, then nothing has changed, then it will again recursively call itself, and so forth until a stack overflow, and will never make any progress parsing the result. This is not good at all!


There's a solution though, and the solution is to not recursively call a rule from itself, before a token is processed. We can effectively rewrite/refactor the rule as:

```
E8          : E9 ( '+' E9 | '-' E9 )*
```

(in EBNF, like regex, `|` means it can match either side)

This way, it does not recursively call itself, and this will make the code easier to implement. We'll keep the formal grammar as the first example, but this is closer to what our code will actually end up resembling.

The rules for all other left-associative binary operators is very similar. But, let's look at the right-associative (assignment) operators:


```
E0          : E1 '=' E0
            | E1 '+=' E0
            | E1 '-=' E0
            | E1 '*=' E0
            | ...
            | E1
```

Although this rule is recursive, (`E0`'s definition contains `E0`), it is not left-recursive, because there is always a token consumed before `E0` appears in the definition. So, a recursive call will always have consumed a token before recursion and thus will not cause problems. So, we don't have to refactor this grammar rule at all.


#### Unary Operators

These will cause special attention, because some potentially have left recursion. Let's define `E10`:

```
E10         : '++' E10
            | '--' E10
            | '+' E10
            | '-' E10
            | '~' E10
            | '!' E10
            | '&' E10
            | '*' E10
            | 'typeof' E10
            | 'sizeof' E10
            | E11
```

No left recursion here! This is because all the operators are prefix operators, and thus will consume a token before any recursive call

Let's try `E11` (I'm including the `()` rule here, since it is the highest precedence rule):

Note that the rule dealing with parentheses accepts any `EXPR`, since `()` override any specific precedence

```
E11         : '(' EXPR ')'
            | E11 '.' NAME
            | E11 '->' NAME
            | E11 '++'
            | E11 '--'
            | E11 '(' ARGS ')'
            | E11 '[' ARGS ']'
            | ATOM
```

Obviously, most of these rules are left recursive -- so we'll apply similar refactoring to it:


```
E11         : ( '(' EXPR ')' | ATOM ) ( '.' NAME | '->' NAME | '++' | '--' | '(' ARGS ')' | '[' ARGS ']' )*
```

Remember, `(` and `)` outside of quotation marks are just syntactical grouping showing parts of the grammar.

We factored it, so that now there is no recursive calls, but it still represents the grammar fully. This rule will, again, resemble the actual parsing algorithm closer, but we'll keep the full, unfactored form as part of the formal specification.


As a side note, if we were to use a LR parsing algorithm (which are common in parser generators), we would have the exact opposite problem -- those handlers can handle left recursion, but using right recursion is not recommended, due to the parsing algorithms using a stack which will use a lot more memory in right recursive grammars as opposed to left recursive ones.


Combining all the new rules (which are basically just copies of the existing rules, with different operators), gives us our current working grammar:

```
PROGRAM     : STMT*

STMT        : ';'
            | '{' STMT* '}'
            | EXPR ';'

EXPR        : E0

E0          : E1 '=' E0
            | E1 '+=' E0
            | E1 '-=' E0
            | E1 '*=' E0
            | E1 '/=' E0
            | E1 '%=' E0
            | E1 '<<=' E0
            | E1 '>>=' E0
            | E1 '|=' E0
            | E1 '^=' E0
            | E1 '&=' E0
            | E1

E1          : E1 '||' E2
            | E2

E2          : E2 '&&' E3
            | E3

E3          : E3 '|' E4
            | E4

E4          : E4 '^' E5
            | E5

E5          : E5 '&' E6
            | E6

E6          : E6 '<' E7
            | E6 '<=' E7
            | E6 '>' E7
            | E6 '>=' E7
            | E6 '==' E7
            | E6 '!=' E7
            | E7

E7          : E7 '<<' E8
            | E7 '>>' E8 
            | E8

E8          : E8 '+' E9
            | E8 '-' E9 
            | E9

E9          : E9 '*' E10
            | E9 '/' E10
            | E9 '%' E10
            | E10

E10         : '++' E10
            | '--' E10
            | '+' E10
            | '-' E10
            | '~' E10
            | '!' E10
            | '&' E10
            | '*' E10
            | 'typeof' E10
            | 'sizeof' E10
            | E11

E11         : '(' EXPR ')'
            | E11 '.' NAME
            | E11 '->' NAME
            | E11 '++'
            | E11 '--'
            | E11 '(' ARGS ')'
            | E11 '[' ARGS ']'
            | ATOM

ARGS        : EXPR (',' EXPR)*
            |

ATOM        : NAME
            | INT
            | STR

```

This may seem monumental, but the code for most of the expression levels will be very similar

The `ARGS` rule is simply for ease of use within function calls and index operations, and won't be a rule in the code -- we'll just manually parse arguments within rule `E11`, as I show later

### Implementing Rules

#### Assignment Operators (right associative)

Right-associative operators will recursively call themselves. And, we'll use a macro because otherwise the code becomes a bit awkward and repetitive for this one.

```c++
RULE(E0) {
    int s = toki;
    unique_ptr<AST> res = SUB(E1);
    if (!res) {
        toki = s;
        return NULL;
    }

    /* Macro to generate cases for specific types */
    #define E0_CASE(_tokk, _astk) else if (TOK.kind == _tokk) { \
        Token t = EAT(); \
        unique_ptr<AST> lhs = move(res), rhs = SUB(E0); /* Since it is right associative, we should have a right-recursive call */ \
        if (!rhs) { \
            errors.push_back(Error(t, "expected an expression to assign from after here")); \
            toki = s; \
            return NULL; \
        } \
        res = make_unique<AST>(t, _astk); \
        res->sub.push_back(move(lhs)); \
        res->sub.push_back(move(rhs)); \
    }

    if (false) {}
    E0_CASE(Token::KIND_ASSIGN, AST::KIND_ASSIGN)
    E0_CASE(Token::KIND_AADD, AST::KIND_BOP_AADD)
    E0_CASE(Token::KIND_ASUB, AST::KIND_BOP_ASUB)
    E0_CASE(Token::KIND_AMUL, AST::KIND_BOP_AMUL)
    E0_CASE(Token::KIND_ADIV, AST::KIND_BOP_ADIV)
    E0_CASE(Token::KIND_AMOD, AST::KIND_BOP_AMOD)
    E0_CASE(Token::KIND_ALSH, AST::KIND_BOP_ALSH)
    E0_CASE(Token::KIND_ARSH, AST::KIND_BOP_ARSH)
    E0_CASE(Token::KIND_AOR, AST::KIND_BOP_AOR)
    E0_CASE(Token::KIND_AXOR, AST::KIND_BOP_AXOR)
    E0_CASE(Token::KIND_AAND, AST::KIND_BOP_AAND)

    return res;

    #undef E0_CASE
}
```

Fairly straightforward, and since it is recursive and right associative, we can have things like `x = y = z;`. Just make sure you track your `make_unique`, `SUB`, and `move` calls with unique pointers. If you're getting weird errors that are hard to read but contain "unique" in the error message, chances are that you've forgotten a `move` somewhere.


#### Binary Operators (left associative)

Rules for `E1` through `E9` are basically the same, here it is for `+`/`-` (rule `E8`):

```c++
RULE(E8) {
    int s = toki;
    unique_ptr<AST> res = SUB(E9);
    if (!res) {
        toki = s;
        return NULL;
    }

    while (true) {
        AST::Kind k = AST::KIND_NONE;
        /**/ if (TOK.kind == Token::KIND_ADD) k = AST::KIND_BOP_ADD;
        else if (TOK.kind == Token::KIND_SUB) k = AST::KIND_BOP_SUB;
        else break; /* not valid */

        /* Skip token */
        Token t = EAT();
        unique_ptr<AST> lhs = move(res), rhs = SUB(E2);
        if (!rhs) {
            toki = s;
            return NULL;
        }

        /* Build tree up another level */
        res = make_unique<AST>(t, k);
        res->sub.push_back(move(lhs));
        res->sub.push_back(move(rhs));
    }

    return res;
}
```

You can see that we start by capturing the starting token index (`s = toki`), and then attempting to parse the rule corresponding to higher level operators.

Then, the next token should be either `+`/`-` (the operators of this level), or any operators of lower precedence. If it is the exact precedence, then we should consume the token (since it is our job as `E8` to parse `+`/`-`), or go ahead and break and return what we've built so far. Since we know we were called recursively, we don't have to handle lower precedence operators -- the rule calling us (`E7`) has that job, and so on up to `E0`. So, in that case, we should stop parsing our operators, and exit the `while` loop, returning the current result.


You notice that if we accept an operator, but that there was an error, we delete our current result, and rewind to the start, and return `NULL` signaling we did not match. This is because if any sub expressions fail, we cannot match, and it should signal a syntax error.

Again, the code is very similar for all `E1` through `E9`, just substitute out other `Token::` and `AST::` kinds, as well as the `SUB()` calls to refer to the next operator group.


#### Unary Operators (and tightly-binding attributes)

If you've understood the other rules, this rule should make sense, albeit more complex. Essentially, we check and see if there's a unary prefix operator. If not, we just return the next rule (`E11`). Otherwise, we consume the token, recursively call the rule, and return the unary operator applied to that. Since we consume a token before recursion, we are guaranteed to make progress, and we won't cause problems with infinite recursion.

```c++
RULE(E10) {
    int s = toki;
    AST::Kind k = AST::KIND_NONE;
    
    /* Unary prefix operators go here */
    /**/ if (TOK.kind == Token::KIND_ADDADD) k = AST::KIND_UOP_PREINC;
    else if (TOK.kind == Token::KIND_SUBSUB) k = AST::KIND_UOP_PREDEC;
    else if (TOK.kind == Token::KIND_ADD) k = AST::KIND_UOP_PREPOS;
    else if (TOK.kind == Token::KIND_SUB) k = AST::KIND_UOP_PRENEG;
    else if (TOK.kind == Token::KIND_SQIG) k = AST::KIND_UOP_PRESQIG;
    else if (TOK.kind == Token::KIND_NOT) k = AST::KIND_UOP_PRENOT;
    else if (TOK.kind == Token::KIND_AND) k = AST::KIND_UOP_PREAND;
    else if (TOK.kind == Token::KIND_MUL) k = AST::KIND_UOP_PRESTAR;

    if (k == AST::KIND_NONE) {
        /* Nothing to do (no unary prefix operator), just return E11 */
        return SUB(E11);
    } else {
        /* Recursively get operand of unary operator */
        Token t = EAT();
        unique_ptr<AST> sub = SUB(E10);
        if (!sub) {
            toki = s;
            return NULL;
        }

        unique_ptr<AST> res = make_unique<AST>(t, k);
        res->sub.push_back(move(sub));
        return res;
    }
}
```

This rule below is the most difficult to understand, so I've included a lot of comments to help (also, look at the factored form mentioned earlier). Like most others, it starts by parsing a value (which is either `ATOM` or `'(' EXPR ')'`), and then parsing operators that come on the right hand side until no more exist. All the while, replacing the result with the new construct applied to the previous result. 

After parsing the value, it also looks for function calls (`(` directly afterwards), and indexing operations (`[` directly afterwards), and continues until the next token doesn't signal anything we need to parse in this rule.

```c++
RULE(E11) {
    /* This one's a bit tricky, we basically start with the left hand side, 
     *   and continually build on it while there is token representing a function call, index operation, or unary postfix operator.
     */
    int s = toki;
    unique_ptr<AST> res = NULL;

    /* First, we find the base value, which is either any expression in '()', or an ATOM */
    if (TOK.kind == Token::KIND_LPAR) {
        /* '(' EXPR ')' */
        EAT();
        res = SUB(EXPR);
        if (!res) {
            toki = s;
            return NULL;
        }
        /* Ensure we ended with a correct symbol as well */
        if (TOK.kind != Token::KIND_RPAR) {
            errors.push_back(Error(TOK, "expected ')' to end parenthetical expression"));
            return NULL;
        }
        EAT();
    } else {
        /* ATOM */
        res = SUB(ATOM);
        if (!res) {
            toki = s;
            return NULL;
        }
    }

    /* Now, parse right hand side components added on to the base component */
    while (true) {
        if (TOK.kind == Token::KIND_DOT) {
            /* Attribute */
            Token t = EAT();
            if (TOK.kind == Token::KIND_NAME) {
                /* found: '.' NAME */
                unique_ptr<AST> lhs = move(res), rhs = make_unique<AST>(TOK, AST::KIND_NAME);
                res = make_unique<AST>(t, AST::KIND_ATTR);
                res->sub.push_back(move(lhs));
                res->sub.push_back(move(rhs));
                EAT();
            } else {
                errors.push_back(Error(t, "expected a name/identifier after '.' for an attribute"));
                toki = s;
                return NULL;
            }
        } else if (TOK.kind == Token::KIND_RARROW) {
            /* Attribute (from pointer) */
            Token t = EAT();
            if (TOK.kind == Token::KIND_NAME) {
                /* found: '->' NAME */
                unique_ptr<AST> lhs = move(res), rhs = make_unique<AST>(TOK, AST::KIND_NAME);
                res = make_unique<AST>(t, AST::KIND_ATTR_PTR);
                res->sub.push_back(move(lhs));
                res->sub.push_back(move(rhs));
                EAT();
            } else {
                errors.push_back(Error(t, "expected a name/identifier after '->' for an attribute"));
                toki = s;
                return NULL;
            }

        /* Unary postfix operators go here */
        } else if (TOK.kind == Token::KIND_ADDADD) {
            unique_ptr<AST> of = move(res);
            res = make_unique<AST>(EAT(), AST::KIND_UOP_POSTINC);
            res->sub.push_back(move(of));
        } else if (TOK.kind == Token::KIND_SUBSUB) {
            unique_ptr<AST> of = move(res);
            res = make_unique<AST>(EAT(), AST::KIND_UOP_POSTDEC);
            res->sub.push_back(move(of));
        /* Function call goes here */
        } else if (TOK.kind == Token::KIND_LPAR) {
            Token t = EAT();
            unique_ptr<AST> lhs = move(res);
            res = make_unique<AST>(t, AST::KIND_CALL);
            res->sub.push_back(move(lhs));

            /* Add ARGS */
            while (TOK.kind != Token::KIND_RPAR) {
                unique_ptr<AST> sub = SUB(EXPR);
                if (!sub) break;
                res->sub.push_back(move(sub));

                if (TOK.kind == Token::KIND_COM) {
                    /* skip comma */
                    EAT();
                } else break; /* must be end */
            }

            if (TOK.kind == Token::KIND_RPAR) {
                EAT();
            } else {
                errors.push_back(Error(t, "expected ')' to end function call started here"));
                toki = s;
                return NULL;
            }

        /* Indexing goes here */
        } else if (TOK.kind == Token::KIND_LBRK) {
            Token t = EAT();
            unique_ptr<AST> lhs = move(res);
            res = make_unique<AST>(t, AST::KIND_INDEX);
            res->sub.push_back(move(lhs));

            /* Add ARGS */
            while (TOK.kind != Token::KIND_RPAR) {
                unique_ptr<AST> sub = SUB(EXPR);
                if (!sub) break;
                res->sub.push_back(move(sub));

                if (TOK.kind == Token::KIND_COM) {
                    /* skip comma */
                    EAT();
                } else break; /* must be end */
            }

            if (TOK.kind == Token::KIND_RBRK) {
                EAT();
            } else {
                errors.push_back(Error(t, "expected ']' to end index operation started here"));
                toki = s;
                return NULL;
            }
        } else break; /* out of constructs */
    }

    return res;
}
```

You'll notice that an AST representing a function call (such as `f(a, b)`) will have the function object being called as the first element of the resulting AST, and the rest of the arguments appended afterwards (in this example, `sub` contains `{f, a, b}`). This may seem unintuitive, but it is the best way to represent it, since the function can be an arbitrary expression as well, and not just a name. So, we need support for a function of any expression type, and thus it must be an AST as a child. So, remember this when reading the output -- function call ASTs have the function as their first child


If you want to improve error messages, think of common mistakes, or ways the parser could fail (for example, do you want to emit a warning if an expression such as `a + ;` is given? You could detect that in rule `E8`, after you accept a token, but the recursive call for the right side fails -- you could print an error message). I've kept the error messages minimal, but still descriptive, and only in places that are definitely failures.

#### Final Touches

Remeber to also change the `EXPR` rule to just `E0`:

```c++
RULE(EXPR) {
    return SUB(E0);
}
```

Finally, let's run on a more complicated example. Still, we don't have things like `if`, `while`, or functions, nor do we have declarations. But, we can see that at least the syntax is being recognized:

Here's the example:

```
x = y = 1 * 2 + 3 << 4 >> 5;
f(a, b, c);
{
    A[B] = &C;
    A[B][C, D][E](F, G)++;
    {
        {
            
        }
    }
}
```

Running this should give a picture like the following:

![assets/img/kata-ckc-ex2.svg](assets/img/kata-ckc-ex2.svg)

Wow! This is a complicated tree, and hopefully you can work it out manually that it is correct. Let's also try giving it incorrect formulations:


```
f(;
```

We get the output:

```
$ make && ./ckc ex.kata
ex.kata:1:2: error: expected ')' to end function call started here
f(;
```
Let's add a finishing touch: `AST::getcontext()` should return another line, which adds `^` and `~` detailing the token that caused the error, for example the output should read:

```
$ make && ./ckc ex.kata
ex.kata:1:2: error: expected ')' to end function call started here
f(;
 ^
```

And, while we're at it, let's also add colors. In `kc.hh` add:

```c++
/** Colors **/

/* Comment to disable colors */
#define KC_USE_COLORS

#if defined(KC_USE_COLORS)

#define KC_COLOR_UNDERLINE "\x1b[4m"
#define KC_COLOR_RESET "\x1b[0m"
#define KC_COLOR_BOLD "\x1b[1m"

#define KC_COLOR_GREEN "\x1b[32m"
#define KC_COLOR_BLUE "\x1b[34m"
#define KC_COLOR_CYAN "\x1b[36m"
#define KC_COLOR_RED "\x1b[31m"
#define KC_COLOR_YELLOW "\x1b[43m"

#define KC_COLOR_ERROR KC_COLOR_BOLD KC_COLOR_RED
#define KC_COLOR_WARN KC_COLOR_BOLD KC_COLOR_YELLOW

#else
#define KC_COLOR_UNDERLINE ""
#define KC_COLOR_RESET ""
#define KC_COLOR_BOLD ""

#define KC_COLOR_GREEN ""
#define KC_COLOR_BLUE ""
#define KC_COLOR_CYAN ""
#define KC_COLOR_RED ""
#define KC_COLOR_YELLOW ""

#define KC_COLOR_ERROR KC_COLOR_BOLD KC_COLOR_RED
#define KC_COLOR_WARN KC_COLOR_BOLD KC_COLOR_YELLOW

#endif

```

These are common [ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code). You can always comment the `#define` line to disable colors in your compiler



Now, we want to make the context for a token accept an (optional) color for the token, which should colorize just the token (and the arrow pointing to it) with that color. The method becomes a little more complicated, but it will be worth it

Down further, let's add the relevant code in `AST::getcontext()`:


```c++
/* Return context around a string */
string getcontext(string color="") const {
    /* no context for invalid */
    if (len == 0) return "";

    string res = "";
    int i = pos;
    /* skip to first of line */
    while (i > 0 && src[i-1] != '\n') i--;

    /* add part before the token */
    res += src.substr(i, pos-i);
    res += color;
    /* add token */
    res += (string)*this;
    res += KC_COLOR_RESET;
    /* add rest of line */
    i = pos + len;
    while (i < src.size() && src[i] != '\n') i++;
    res += src.substr(pos+len, i-(pos+len));

    /* add next line pointing to the token */
    res += "\n";
    for (i = 0; i < col; ++i) res += " ";
    res += color;
    res += "^";
    /* trailing part of the arrow, if it is multiple characters long */
    for (i = 0; i < len - 1; ++i) res += "~";
    res += KC_COLOR_RESET;

    return res;
}
```

And finally, in `Error` and `Warning`'s string conversions:


```
struct Error {
    /* ... */
    operator string() const { return tok.src_name + ":" + to_string(tok.line+1) + ":" + to_string(tok.col+1) + ": " KC_COLOR_ERROR "error:" KC_COLOR_RESET " " + msg + "\n" + tok.getcontext(KC_COLOR_ERROR); }
};
struct Warning {
    /* ... */
    operator string() const { return tok.src_name + ":" + to_string(tok.line+1) + ":" + to_string(tok.col+1) + ": " KC_COLOR_WARN "warning:" KC_COLOR_RESET " " + msg + "\n" + tok.getcontext(KC_COLOR_WARN); }
};
```

Now, running the example:

```
f(;
```

Gives the output:


```
ex.kata:1:2: error: expected ')' to end function call started here
f(;
 ^
```

On my terminal (GNOME terminal), it looks like this:

![assets/img/kata-err-0.png](assets/img/kata-err-0.png)

Fairly professional, eh? These touches will make your program seem much more usable, and will help developers quickly see the problems with their code.


Let's try the code:


```
my name is cade
```

We get the message:

![assets/img/kata-err-1.png](assets/img/kata-err-1.png)


Now, we know that the colors work, as well as the `^~~~` pointing to the offending token.


### Wrapping Up

At this point, you've got a working expression and nested `{}` block parser, which can output to graphviz, and be visualized. We still haven't done any real compiling yet -- but that's okay. What we've got so far is already pretty impressive. At this point, you should play around with your compiler, make sure it supports expressions that you want it to, and make sure precedence is working -- test out examples, do them manually, and make sure the resulting AST matches what you expect. If it doesn't, you'll need to debug your grammar.


See you next time!


