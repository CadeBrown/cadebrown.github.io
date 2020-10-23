---
layout: post
title: "Kata (#1) - First Compiler (Tokenizing)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ckc-arch.svg
---

In this part, we begin implementing a compiler for a subset of the full Kata language. It won't be optimized, or particularly well designed, but it'll get the job done! (and technically, it is probably better called an interpreter).

<!--more-->

Eventually, we want to write the Kata compiler in Kata itself (a process known as [self hosting](https://en.wikipedia.org/wiki/Self-hosting_(compilers))). However, to do that, we would first need a Kata compiler. Of course, the only Kata compiler would be one written in Kata, and so forth. 

It's at this point that many developers (outside of programming language developers) will begin to wonder how a language ever exists in the first place. It's a classic chicken-or-egg problem, and we can't solve it by just believing [there are turtles all the way down](https://en.wikipedia.org/wiki/Turtles_all_the_way_down); we need to actually ground ourselves somewhere!

The traditional solution to this problem is called [bootstrapping](https://en.wikipedia.org/wiki/Bootstrapping_(compilers)). Specifically, we'll write a compiler for a subset of Kata in C (this is the compiler `ckc`), and use that compiler on the source for the full Kata compiler (called `kc`), which is written in Kata itself.

From that point, we'll use that compiler (`kc`) to re-compile itself so that it is more optimized. And, boom! We will have a fully working compiler. However, we're still a few steps away from that. First, we'll need to write `ckc` and ensure it works. So, let's get to it!


## `ckc` Structure

We only need to compile a subset of Kata -- we won't worry about for loops, for-each loops, try/catch blocks, a macro system, or many other features. This will simplify the compiler and reduce the workload. We will also just abort at the first error we encounter, and print a minimal error message -- normally, we would want to print diagnostics, location information, and a detailed message, but that's for the full implementation.

We'll also make it an interpreter, because (believe it or not) that will actually be easier than having to write assembly-specific ones just for this immediate compiler. Below is a helpful diagram showing the stages of our compiler we need to write:

![assets/img/kata-ckc-arch.svg](assets/img/kata-ckc-arch.svg)


Before we begin, we'll define a macro to signal a compiler error (and exit):

```c
/* in 'kc.h' */

/* Used when an error is encountered */
#define ERR(...) do { \
    fprintf(stderr, "error: " __VA_ARGS__); \
    fprintf(stderr, "\n"); \
    exit(1); \
} while (0)

```


## Tokenize (Lexer)

To transform the raw text of Kata source code into a computer-readable format, we need to implement the first stage of the 'Front End' section of the earlier diagram (Tokenize/Lexer stage). Essentially, to a computer, the source code is just a bunch of bytes -- the computer doesn't know that when we type `int x;` we really mean "declare a variable called 'x' of type 'int'". The computer only sees its ASCII/UTF8 representation: `69 6e 74 20 78 3b 0a`. They lexer won't solve this problem completely; it will essentially say to the computer "there's a word 'int', a space that I can ignore, then a word 'x', then a symbol ';'", which is closer to actually understanding it as a programing language.

This initial transformation is called tokenizing (or lexing), because it turns a string (which is just an array of bytes) into [tokens](https://en.wikipedia.org/wiki/Lexical_analysis#Token). A token is just a collection of these characters that are supposed to be together (like a word, number, or 'phrase'). 


We'll define types of tokens and operations on tokens in the `kc.h` header file (notice -- the tokens's 'pos' and 'len' are relative to the start of the source code it was tokenized from):

```c
/* in 'kc.h' */

/* Token, a group of characters that have a special meaning together */
typedef struct {
    enum {
        TOK_EOF    = 0,
        
        /* atoms */
        TOK_INT,
        TOK_FLOAT,
        TOK_STRING,
        TOK_NAME,

        /* other, random terminal symbol */
        TOK_T,

    } k;

    /* position and length (in bytes) from the start of the source code */
    int pos, len;

} tok_t;

#define TOK_MAKE(_k, _pos, _len) ((tok_t){ .k = (_k), .pos = (_pos), .len = (_len) })
#define TOK_EMPTY() TOK_MAKE(TOK_EOF, -1, -1)

/* return NUL-terminated, malloc'd string of the exact source code that 't' represents */
char* tok_str(const char* name, const char* src, tok_t t);

/* convert 't' to valid integer. must be of type 'TOK_INT' */
int tok_get_int(const char* name, const char* src, tok_t t);
/* convert 't' to valid string. must be of type 'TOK_STR' */
char* tok_get_str(const char* name, const char* src, tok_t t);


/* Return a 'malloc'd array of tokens for a given input, and set 'n' to the size */
tok_t* tokenize(const char* name, const char* src, int* n);

```

Now, we create a file, `tok.c` to contain implementations:

```c
/* tok.c - transforms string contents into an array of tokens
 *
 * @author:    Cade Brown <cade@cade.site>
 */
#include <kc.h>

char* tok_str(const char* name, const char* src, tok_t t) {
    char* r = malloc(t.len + 1);
    memcpy(r, src + t.pos, t.len);
    r[t.len] = '\0';
    return r;
}

tok_t* tokenize(const char* name, const char* src, int* n) {
    
    ERR("TODO: tokenize");

    return NULL;
}

```

And, update our `main.c` to actually call and print out the tokens it received:

```c
/* ... */ 

char* readall(const char* fname) {
    FILE* fp = fopen(fname, "r");
    if (!fp) {
        ERR("failed to open '%s'", fname);
        return NULL;
    }

    fseek(fp, 0, SEEK_END);
    long sz = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    char* r = malloc(sz + 1);

    fread(r, sz, 1, fp);
    r[sz] = '\0';

    return r;
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

    for (i = 0; i < n_tok; ++i) {
        printf("  %2i: '%.*s'\n", i, tok[i].len, src + tok[i].pos);
    }
}
```

We'll also have a test file, called `test.k`. Here's what I'm starting with:

```
/* a comment */
int x = 4;
```

To test our program, we can run:

```bash
$ make
cc -I. -c -fPIC main.c -o main.o
cc -I. tok.o main.o -o ckc
$ ./ckc test.k
compiling kata source in 'test.k'
error: TODO: tokenize
```

Now, let's actually implement the lexer! Back in `tok.c`, let's start lexing:

```c
/* return whether a character is a valid digit in a base */
static int my_isdigit(int c, int base) {
    if (base == 10) return '0' <= c && c <= '9';
    return 0;
}

/* return whether a character is a valid start of an identifier */
static int my_isname_s(int c) {
    return c == '_' || ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z');

}
/* return whether a character is a valid middle part of an identifier */
static int my_isname_m(int c) {
    return my_isname_s(c) || my_isdigit(c, 10);
}

tok_t* tokenize(const char* name, const char* src, int* n) {
    tok_t* res = NULL;
    *n = 0;
    int n_src = strlen(src);

    /* adds 'pos' through 'i' as a token to the output */
    #define ADD(_k) do { \
        int _i = (*n)++; \
        res = realloc(res, sizeof(*res) * *n); \
        res[_i] = TOK_MAKE(_k, pos, i - pos); \
        pos += i; \
    } while (0)

    /* current position of scanner, and position of token */
    int i = 0, pos = 0;
    while (i < n_src) {
        /* skip whitespace */
        while (i < n_src && src[i] == ' ' || src[i] == '\t' || src[i] == '\r' || src[i] == '\n') i++;
        if (i >= n_src) break;
        pos = i;

        /* match patterns */
        if (src[i] == '/' && src[i+1] == '/') {
            /* single line comment */
            do {
                i++;
            } while (src[i] && src[i] != '\n');
            /* skip */

        } else if (src[i] == '/' && src[i+1] == '*') {
            /* multi line comment */
            i++;
            do {
                i++;
            } while (src[i] && !(src[i] == '*' && src[i + 1] == '/'));
            
            if (src[i] == '*') {
                i++;
                i++;
            } else {
                ERR("%s: no end to comment", name);
            }
            /* skip */

        } else if (my_isdigit(src[i], 10)) {
            /* INT: \d+ */
            do {
                i++;
            } while (src[i] && my_isdigit(src[i], 10));
            ADD(TOK_INT);

        } else if (my_isname_s(src[i])) {
            /* NAME: [a-zA-Z_][a-zA-Z_0-9]* */
            do {
                i++;
            } while (src[i] && my_isname_m(src[i]));
            ADD(TOK_NAME);

        /* template for random terminal symbols */
        #define T(_str) } else if (strncmp(_str, src+i, sizeof(_str) - 1) == 0) { \
            i += sizeof(_str) - 1; \
            ADD(TOK_T); \

        /* operators/punctuation */
        T("=");
        T(";");

        } else {
            ERR("%s: unexpected character: %c", name, src[i]);
        }
    }

    ADD(TOK_EOF);
    return res;
}

```

The `my_is*` functions are similar to the [ctype library functions](https://www.tutorialspoint.com/c_standard_library/ctype_h.htm). I chose to implement them for completeness.

The format is pretty simple: 

  * Skip all whitespace at the current position
  * Check each token rule and see if the start matches
  * If we found a matching token rule, keep reading characters that match
  * Once we found a character that didn't match, we add the token and move the current position
  * If the current character did not match any of the rules, then we print an error and exit

Repeat those steps until the current position (`i`) is still a valid position in the string. Then, add an `EOF` token and return the list of tokens.

We automate some rules via the `T` macro, which creates terminal tokens (those with kind `TOK_T`) for literal matches.

Now, if we re-run our command:

```bash
$ make && ./ckc test.k
cc -I. -c -fPIC tok.c -o tok.o
cc -I. tok.o main.o -o ckc
compiling kata source in 'test.k'
tokens[6]
   0: 'int'
   1: 'x'
   2: '='
   3: '4'
   4: ';'
   5: ''
```

Voila! It looks like it's working correctly. The comments and whitespace are ignored, and `int` is all together (which proves that the lexer is not just outputing characters -- it is forming them into tokens, just like human readers do).

For completeness, I'll go ahead and add the full list of operators and punctuation:

```c
        /* ... tok.c, in 'tokenize()' */

        /* operators */
        T("++");
        T("--");

        T("=");
        T("<<=");
        T(">>=");
        T("|=");
        T("&=");
        T("^=");

        T("+=");
        T("-=");
        T("*=");
        T("/=");
        T("%=");

        T("<<");
        T(">>");

        T("<");
        T("<=");
        T(">");
        T(">=");
        T("==");
        T("!=");

        T("||");
        T("&&");
        T("??");
        T("|");
        T("&");
        T("^");

        T("+");
        T("-");
        T("*");
        T("/");
        T("%");

        T("!");
        T("~");

        /* punctuation */
        T(".");
        T(",");
        T(":");
        T(";");
        T("(");
        T(")");
        T("[");
        T("]");
        T("{");
        T("}");

        /*  */
```

And, we'll need to code up the `TOK_STRING` match, which looks like:

```
        /* ... tok.c, in 'tokenize()' */

        } else if (src[i] == '"') {
            /* STRING: "..." */
            i++;
            do {
                /* skip escape codes (allows '"' within string) */
                if (src[i] == '\\') i++;
                i++;
            } while (src[i] && src[i] != '"');
            if (src[i] == '"') {
                i++;
            } else {
                ERR("%s: no end to string", name);
            }
            ADD(TOK_STRING);
```

Running this with a new `test.k`:

```
$ cat test.k
/* a comment */
int x = 4;
// another comment
string myname = "hello, world";
$ make && ./ckc test.k
cc -I. -c -fPIC tok.c -o tok.o
cc -I. tok.o main.o -o ckc
tokens[11]
   0: 'int'
   1: 'x'
   2: '='
   3: '4'
   4: ';'
   5: 'string'
   6: 'myname'
   7: '='
   8: '"hello, world"'
   9: ';'
  10: ''
```

At this point, our lexer is already done. Some improvements we could make (and will make on the full compiler) are:

  * Allowing unicode codepoints (UTF8) as identifiers
  * Parsing floating point constants
  * Accepting hex/octal/binary constants



