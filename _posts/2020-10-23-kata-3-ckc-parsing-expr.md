---
layout: post
title: "Kata (#3) - First Compiler (Parsing Expressions)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ast-0.svg
---

In this post, we'll go further and parse even more constructs. We won't parse every construct, but we will parse enough to start running some examples.

<!--more-->

Fair warning, this installment has a lot of code. It's mainly just implementing the parser like a human would. The rules are basically just "I see a token X here, then a token Y, so this makes up rule Z". It's fairly straightforward, and each rule returns an AST (so they are combined recursively as each others children).

Here's what we'll need to compile by the end of this installment:

```
/* test.k */
main(int argc, &&char argv) : int {
    printf("hello, world");
    return 0;
}
```

We need to go ahead and implement `atom`, which is a primitive literal, or a variable reference:

```c
/* atom           = INT | FLOAT | STRING | NAME */
RULE(atom) {
    ast res = NULL;
    if (CUR.k == TOK_INT) {
        tok_t t = EAT();
        long long int val;
        char* vstr = STR(t);
        sscanf(vstr, "%lli", &val);
        free(vstr);
        res = ast_new(AST_INT);
        res->val_i = val;
    } else if (CUR.k == TOK_NAME) {
        return SUB(NAME);
    } else if (CUR.k == TOK_STRING) {
        tok_t t = EAT();
        res = ast_new(AST_STRING);
        /* taking off 2 and adding 1 is for the actual quotes '"' */
        res->val_s = newstr(t.len - 2, src + t.pos + 1);
    }
    return res;
}
```

Now, we can define the statement rule parser (which allows `{ ... }`, `expr;`, etc.):

```c
/* stmt           = '{' stmt* '}' | stmt_if | stmt_while | stmt_dowhile | stmt_for | stmt_foreach | stmt_trycatch | ';' | 'return' expr? ';' | decl ';' | expr ';' */
RULE(stmt) {
    int s = toki;
    ast res = NULL;
    if (EQ(CUR, "{")) {
        EAT();
        res = ast_new(AST_BLOCK);
        while (!EQ(CUR, "}")) {
            ast sub = SUB(stmt);
            if (!sub) {
                toki = s;
                ast_free(res);
                return NULL;
            }
            ast_push(res, sub);
        }
        if (!EQ(CUR, "}")) {
            toki = s;
            ast_free(res);
            return NULL;
        }
    } else if (EQ(CUR, ";")) {
        /* empty statement */
        EAT();
        res = ast_new(AST_BLOCK);

    } else if (EQ(CUR, "return")) {
        EAT();
        res = ast_new(AST_RETURN);

        if (EQ(CUR, ";")) {
            /* return void */
            EAT();
        } else {
            ast sub = SUB(expr);
            if (!sub) {
                ast_free(res);
                toki = s;
                return NULL;
            }
            ast_push(res, sub);

            if (!EQ(CUR, ";")) {
                ast_free(res);
                toki = s;
                return NULL;
            }
            EAT();
        }

    } else {
        /* try 'decl' then 'expr' */
        res = SUB(decl);
        if (res) {
            if (EQ(CUR, ";")) {
                EAT();
                return res;
            } else {
                ast_free(res);
                res = NULL;
                toki = s;
            }
        }
        res = SUB(expr);
        if (res) {
            if (EQ(CUR, ";")) {
                EAT();
                return res;
            } else {
                ast_free(res);
                res = NULL;
                toki = s;
            }
        }
    }

    return res;
}
```

(obviously, we'll need to go back and implement 'if', 'while', 'for', and other statements in the future)

Now, we need to add a function definition parser:

```c
/* def_func       = mod* NAME '(' decl? (',' decl)* ')' (':' type)? '{' stmt* '}' */
RULE(def_func) {
    int s = toki;
    ast NAME = SUB(NAME);
    if (!NAME) return NULL;
    ast res = ast_new(AST_DEF_FUNC);
    ast_push(res, NAME);

    if (!EQ(CUR, "(")) {
        toki = s;
        ast_free(res);
        return NULL;
    }
    EAT();
    
    /* Parse parameters inside '()' */
    while (!EQ(CUR, ")")) {
        ast decl = SUB(decl);
        if (!decl) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        
        ast_push(res, decl);

        if (EQ(CUR, ",")) {
            EAT();
        } else break;
    }

    if (!EQ(CUR, ")")) {
        toki = s;
        ast_free(res);
        return NULL;
    }
    EAT();

    /* parse ': <rtype>', which is optional */
    if (EQ(CUR, ":")) {
        EAT();
        ast rtype = SUB(type);
        if (!rtype) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        ast_push(res, rtype);
    } else {
        /* return VOID by default */
        ast v_void = ast_new(AST_NAME);
        v_void->val_s = newstr(4, "void");
        ast_push(res, v_void);
    }

    ast body = ast_new(AST_BLOCK);
    ast_push(res, body);

    /* { <body> } */

    if (!EQ(CUR, "{")) {
        toki = s;
        ast_free(res);
        return NULL;
    }
    EAT();
    
    while (!EQ(CUR, "}")) {
        ast sub = SUB(stmt);
        if (!sub) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        ast_push(body, sub);
    }

    if (!EQ(CUR, "}")) {
        toki = s;
        ast_free(res);
        return NULL;
    }
    EAT();
    
    return res;
}

```


And, finally, we need to update the top-level rule describing the entire program:

```c
/* progam         = (import | def_struct | def_enum | def_func | mod* moredecl ';')* */
RULE(program) {
    ast res = ast_new(AST_BLOCK);
    while (CUR.k != TOK_EOF) {
        int s = toki;
        ast sub = NULL;

        /* def_func */
        sub = SUB(def_func);
        if (sub) {
            ast_push(res, sub);
            continue;
        }

        /* decl; */
        sub = SUB(decl);
        if (sub) {
            if (EQ(CUR, ";")) {
                EAT();
                ast_push(res, sub);
                continue;
            } else {
                toki = s;
                ast_free(sub);
                sub = NULL;
            }
        }

        /* no matches */
        if (!sub) {
            ast_free(res);
            res = NULL;
            break;
        }
    }

    if (!res) {
        ERR("%s: invalid program", name);
    } else if (CUR.k != TOK_EOF) {
        ERR("%s: invalid program, extra tokens", name);
    }
    return res;
}
```

At this point, you should probably check your work. It's easy to forget an `EAT()` somewhere and it messes up your whole parser. Let's try the following example:

```
$ cat test.k
/* test.k */
main() {
    int x;
}
$ make && ./ckc test.k
cc -I. -c -fPIC parse.c -o parse.o
cc -I. tok.o main.o parse.o ast.o -o ckc
compiling kata source in 'test.k'
BLOCK [1]
  DEF_FUNC [3]
    NAME main
    NAME void
    BLOCK [1]
      DECL [2]
        NAME int
        NAME x
```

If everything went correctly, your output should look like mine. As you can see, we only declare `x` inside the function, and it is indeed inside the `BLOCK` that is within the `DEF_FUNC`

Now, let's try to test our `main` signature we expect: `main(int argc, &&char argv)`:

```
$ cat test.k
/* test.k */
main(int argc, &&char argv) {
    int x;
}
$ make && ./ckc test.k
compiling kata source in 'test.k'
error: test.k: invalid program
```

Huh, that's weird. Let's see what's happening. Uncomment some lines in `main` to print out the tokens:

```c

/* ... in main.c */
    printf("tokens[%i]\n", n_tok);
    for (i = 0; i < n_tok; ++i) {
        printf("  %2i: '%.*s'\n", i, tok[i].len, src + tok[i].pos);
    }

```

And re-run:
```
$ cat test.k
/* test.k */
main(int argc, &&char argv) {
    int x;
}
$ make && ./ckc test.k
cc -I. -c -fPIC main.c -o main.o
cc -I. tok.o main.o parse.o ast.o -o ckc
compiling kata source in 'test.k'
tokens[15]
   0: 'main'
   1: '('
   2: 'int'
   3: 'argc'
   4: ','
   5: '&&'
   6: 'char'
   7: 'argv'
   8: ')'
   9: '{'
  10: 'int'
  11: 'x'
  12: ';'
  13: '}'
  14: ''
error: test.k: invalid program
```

Notice number `5`, the token is read as `&&`. Our rule for `type` is:

```
type           = '&' type | ...
```

Logically speaking, we should be able to replace `type` itself with `'&' type`, so the following should also be a formulation:

```
type           = '&' ('&' type) | ...
               = '&' '&' type | ...
```

However, since we tokenize `&&` as a single token, it will no longer match two consecutive `&` tokens in a rule. Indeed, if we add spaces between them and recompile it works just fine:


```
$ cat test.k
/* test.k */
main(int argc, & &char argv) {
    int x;
}
$ make ckc && ./ckc test.k
make: 'ckc' is up to date.
compiling kata source in 'test.k'
tokens[16]
   0: 'main'
   1: '('
   2: 'int'
   3: 'argc'
   4: ','
   5: '&'
   6: '&'
   7: 'char'
   8: 'argv'
   9: ')'
  10: '{'
  11: 'int'
  12: 'x'
  13: ';'
  14: '}'
  15: ''
BLOCK [1]
  DEF_FUNC [5]
    NAME main
    DECL [2]
      NAME int
      NAME argc
    DECL [2]
      UOP_AND [1]
        UOP_AND [1]
          NAME char
      NAME argv
    NAME void
    BLOCK [1]
      DECL [2]
        NAME int
        NAME x
```

Now, `5` and `6` are both `&` tokens, and so our rule works. And, it parses correctly, seeing as the `DECL` nodes within the `DEF_FUNC` node contain `int argc` and a doubly-nested `UOP_AND` (aka `&`) type of `char` (i.e. `& & char`).

So, what should we do about this? Should we not accept `&&` as a token? And instead require them all to be `&`. No, for our language, it will be fine to augment the `type` rule to include this special case:

```
type           = '&&' type | '&' type | type '[' args ']' | 'typeof' E7 | dotname
```

This won't affect expressions, because you cannot take the address of an intermediate result of an address (i.e. `&&x` is not valid, since `x` is a variable, it has an address, but `&x` does not have a set address, because it is a temporary value).

So, we will augment the `type` parsing rule like so:

```
/* '&&' type | '&' type | type '[' args ']' | 'typeof' E7 | dotname */
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
    } else if (EQ(CUR, "&&")) {
        /* handle double address type */
        EAT();
        ast of = SUB(type);
        if (!of) {
            toki = s;
            return NULL;
        }
        ast tmp = ast_new(AST_UOP_AND);
        ast_push(tmp, of);
        res = ast_new(AST_UOP_AND);
        ast_push(res, tmp);
        
    } else {
        res = SUB(dotname);
    }

    return res;
}
```

Now, if we re-compile and run with the non-spaced input:

```
$ cat test.k
/* test.k */
main(int argc, &&char argv) {
    int x;
}
$ make ckc && ./ckc test.k
compiling kata source in 'test.k'
tokens[15]
   0: 'main'
   1: '('
   2: 'int'
   3: 'argc'
   4: ','
   5: '&&'
   6: 'char'
   7: 'argv'
   8: ')'
   9: '{'
  10: 'int'
  11: 'x'
  12: ';'
  13: '}'
  14: ''
BLOCK [1]
  DEF_FUNC [5]
    NAME main
    DECL [2]
      NAME int
      NAME argc
    DECL [2]
      UOP_AND [1]
        UOP_AND [1]
          NAME char
      NAME argv
    NAME void
    BLOCK [1]
      DECL [2]
        NAME int
        NAME x
```

You'll notice that even though token `5` is `&&`, the parser correctly parses it as when we manually added spaces to seperate the `&`s

## Expressions


Let's talk about the expression rules. I'm going to post the expression EBNF here just once and reference it throughout this section:

```
expr           = E0
E0             = assign ('=' | '<<=' | '>>=' | '|=' | '&=' | '^=' | '+=' | '-='  | '*=' | '/=' | '%=') E0 | E1
E1             = E2 (('||' | '&&' | '??') E2)*
E2             = E3 (('<' | '<=' | '>' | '>=' | '==' | '!=') E3)*
E3             = E4 (('|' | '&' | '^') E4)*
E4             = E5 (('<<' | '>>') E5)*
E5             = E6 (('+' | '-') E6)*
E6             = E7 (('*' | '/' | '%') E7)*
E7             = ('++' | '--' | '!' | '&' | '*' | '~' | '-' | 'sizeof' | 'typeof')  E7 | E8
E8             = E9 ('.' NAME)* ('++' | '--')*
E9             = ('(' expr ')' | atom) ('(' args ')' | '[' args ']')*

atom           = INT | FLOAT | STRING | NAME
```

This defines an expression grammar that respects operator precedence (i.e. PEMDAS). The lowest precedence operators are in `E0`, and highest are in `E8`, and the rest are in between.

All operators in `E0` through `E6` are binary operators. `E7` are unary prefix (i.e. come before the value), and `E8` are unary postfix (i.e. come after the value). This means that all binary operators have lower precedence than any unary operators, and that unary prefix operators have lower precedence than unary postfix operators do.

Note that the `. NAME` (dot operator) is an exception; it's really the highest precedence (other than `()`) operator, but it's not an arithmetic operator.

To implement these rules are very similar, so I'll just show a few here:


### Binary Operators

```c
/* ... */

/* E6             = E7 (('*' | '/' | '%') E7)* */
RULE(E6) {
    int s = toki;
    ast res = SUB(E7);
    if (!res) {
        toki = s;
        return NULL;
    }

    while (EQ(CUR, "*") || EQ(CUR, "/") || EQ(CUR, "%")) {
        tok_t t = EAT();
        ast lhs = res;
        ast rhs = SUB(E7);
        if (!rhs) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        int k = 0;
        /**/ if (EQ(t, "*")) k = AST_BOP_MUL;
        else if (EQ(t, "/")) k = AST_BOP_DIV;
        else if (EQ(t, "%")) k = AST_BOP_MOD;

        res = ast_new(k);
        ast_push(res, lhs);
        ast_push(res, rhs);
    }

    return res;
}

/* E5             = E6 (('+' | '-') E6)* */
RULE(E5) {
    int s = toki;
    ast res = SUB(E6);
    if (!res) {
        toki = s;
        return NULL;
    }

    while (EQ(CUR, "+") || EQ(CUR, "-")) {
        tok_t t = EAT();
        ast lhs = res;
        ast rhs = SUB(E6);
        if (!rhs) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        int k = 0;
        /**/ if (EQ(t, "+")) k = AST_BOP_ADD;
        else if (EQ(t, "-")) k = AST_BOP_SUB;

        res = ast_new(k);
        ast_push(res, lhs);
        ast_push(res, rhs);
    }

    return res;
}
/*
 ...
*/


/* E0             = assign ('=' | '<<=' | '>>=' | '|=' | '&=' | '^=' | '+=' | '-='  | '*=' | '/=' | '%=') E0 | E1 */
RULE(E0) {
    int s = toki;
    ast res = SUB(E1);
    if (!res) {
        toki = s;
        return NULL;
    }

    /* we only support direct assignment, not augmented operator assignments; that'll be for the full version! */
    while (EQ(CUR, "=")) {
        tok_t t = EAT();
        ast lhs = res;
        ast rhs = SUB(E0);
        if (!rhs) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        int k = 0;
        /**/ if (EQ(t, "=")) k = AST_BOP_ASSIGN;

        res = ast_new(k);
        ast_push(res, lhs);
        ast_push(res, rhs);
    }

    return res;
}

/* expr           = E0 */
RULE(expr) {
    return SUB(E0);
}
```

Hopefully you can see the pattern. You immediately try to accept the next level:

```
RULE(E0) {
    int s = toki;
    ast res = SUB(E1);
```

Then, while the next character is a valid operator for the current precedence level, you take it off, determine its AST kind, and then recursively call either the same rule you're in (if you are right associative, which only `=` is), or the next highest rule (if you are left associative, like most binary operators are).

You can copy and paste the functions and just add more `EQ(CUR, <op>)`, and set the `k = AST_BOP_<kind>` correctly for each operator.

Let's take a minute and appreciate why this works. Take, for example, rule `E5`. Inside the rule, it only ever contains `SUB(E6)` as a recursive call, and only matches `"+"` and `"-"` directly (i.e. it will never call back up to `E4`). Then, `E6` will only ever recursively call `SUB(E7)` and match the operators `"*"`, `"/"`, and `"%"` directly. And this is true for any of the binary operators. If we have a table:

|---|---|
|E0|=|
|E1|\|\|, &&, ??|
|E2|<, <=, >, >=, ==, !=|
|E3|\|, &, ^|
|E4|<<, >>|
|E5|+, -|
|E6|*, /, %|

I cann tell you that a given entry (say, `E3`) will never consume directly or recursively anything above it (so, `E2`, `E1`, or `E0`). Therefore, those above it know that no rule it calls will take the operators it cares about, and so it lets all the higher precedence operators parse their values out first, before it goes. Each rule can do this, because again, it knows nothing it calls will accidentally consume the operator it cares about, since its children are higher precedence and only care about higher precedence operators.

There is technically an exception to this: within `()`, when it calls `SUB(expr)`, it will start back at the top and so that rule may match something higher. However, this is because `()` override any precedence, and therefore that's completely okay and does not disrupt the flow (since, if you have `A + (B + C)`, the `A + ` will never match the right hand `C`; that would be ill-formed to jump across parenthesis like that).

### Unary Operators

We'll (finally) implement unary operators, as well as function calls/index/subscripting:


```c
/* E9             = ('(' expr ')' | atom) ('(' args ')' | '[' args ']')* */
RULE(E9) {
    int s = toki;
    ast res = NULL;
    if (EQ(CUR, "(")) {
        EAT();

        res = SUB(expr);
        if (!res) {
            toki = s;
            return NULL;
        }

        if (!EQ(CUR, ")")) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        EAT();
    } else {
        res = SUB(atom);
    }

    if (!res) {
        toki = s;
        return NULL;
    }

    /* now, parse function call/indexing (optional) */

    while (EQ(CUR, "(") || EQ(CUR, "[")) {
        int k = 0;
        /**/ if (EQ(CUR, "(")) k = AST_CALL;
        else if (EQ(CUR, "[")) k = AST_SUBSCRIPT;
        EAT();
        ast lhs = res;
        res = ast_new(k);
        ast_push(res, lhs);

        while (!(EQ(CUR, ")") || EQ(CUR, "]"))) {
            ast sub = SUB(expr);
            if (!sub) {
                toki = s;
                ast_free(res);
                return NULL;
            }

            ast_push(res, sub);

            if (EQ(CUR, ",")) {
                EAT();
            } else break;
        }

        if (!((EQ(CUR, ")") && k == AST_CALL) || (EQ(CUR, "]") && k == AST_SUBSCRIPT))) {
            toki = s;
            ast_free(res);
            return NULL;
        }
        EAT();
    }

    return res;
}

/* E8             = E9 ('.' NAME)* ('++' | '--')* */
RULE(E8) {
    int s = toki;
    ast res = SUB(E9);
    if (!res) return NULL;

    while (EQ(CUR, ".") && NEXT.k == TOK_NAME) {
        EAT();
        ast attr = SUB(NAME);
        assert(attr != NULL);
        ast lhs = res;
        res = ast_new(AST_ATTR);
        ast_push(res, lhs);
        ast_push(res, attr);
    }

    /* unary postfix */
    while (EQ(CUR, "++") || EQ(CUR, "--")) {
        int k = 0;
        /**/ if (EQ(CUR, "++")) k = AST_UOP_INC_POST;
        else if (EQ(CUR, "--")) k = AST_UOP_DEC_POST;
        EAT();

        ast lhs = res;
        res = ast_new(k);
        ast_push(res, lhs);
    }

    return res;
}

/* E7             = ('++' | '--' | '!' | '&' | '*' | '~' | '-' | 'sizeof' | 'typeof')  E7 | E8 */
RULE(E7) {
    int s = toki;
    ast res = NULL;
    int k = 0;
    /* unary prefix operators */
    /**/ if (EQ(CUR, "++")) k = AST_UOP_INC;
    else if (EQ(CUR, "--")) k = AST_UOP_DEC;
    else if (EQ(CUR, "!")) k = AST_UOP_NOT;
    else if (EQ(CUR, "&")) k = AST_UOP_AND;
    else if (EQ(CUR, "*")) k = AST_UOP_STAR;
    else if (EQ(CUR, "~")) k = AST_UOP_SQIG;
    else if (EQ(CUR, "-")) k = AST_UOP_NEG;
    else if (EQ(CUR, "sizeof")) k = AST_UOP_SIZEOF;
    else if (EQ(CUR, "typeof")) k = AST_UOP_TYPEOF;

    if (k) {
        /* recurse */
        EAT();
        ast sub = SUB(E7);
        if (sub) {
            res = ast_new(k);
            ast_push(res, sub);
        }
    } else {
        res = SUB(E8);
    }

    if (!res) toki = s;
    return res;
}
```

Hopefully this code illustrates how you can parse these rules. This has been a very code-heavy post, because there's not much to explain other than we are just implementing order of operations. Let's run it on the code example given at the beginning of this post:

```
$ cat test.k
/* test.k */
main(int argc, &&char argv) : int {
    printf("hello, world");
    return 0;
}
$ make ckc && ./ckc test.k
cc -I. -c -fPIC parse.c -o parse.o
cc -I. tok.o main.o parse.o ast.o -o ckc
compiling kata source in 'test.k'
tokens[22]
   0: 'main'
   1: '('
   2: 'int'
   3: 'argc'
   4: ','
   5: '&&'
   6: 'char'
   7: 'argv'
   8: ')'
   9: ':'
  10: 'int'
  11: '{'
  12: 'printf'
  13: '('
  14: '"hello, world"'
  15: ')'
  16: ';'
  17: 'return'
  18: '0'
  19: ';'
  20: '}'
  21: ''
BLOCK [1]
  DEF_FUNC [5]
    NAME main
    DECL [2]
      NAME int
      NAME argc
    DECL [2]
      UOP_AND [1]
        UOP_AND [1]
          NAME char
      NAME argv
    NAME int
    BLOCK [2]
      CALL [2]
        NAME printf
        STRING hello, world
      RETURN [1]
        INT 0
```


That's a lot of output (you can remove the token printing in `main.c` if you want to), but you can clearly see the body of main contains:

```
    BLOCK [2]
      CALL [2]
        NAME printf
        STRING hello, world
      RETURN [1]
        INT 0
```

Remember, a function call has children `[func, arg0, arg1, arg2, ...]`, so this result is perfectly fine! 

Well, I apologize for the huge code explosion on this post. This is mainly for reference if you get stuck; you can easily check the code I've posted here and see where yours differs if you have problems.



