---
layout: post
title: "Kata (#1) - First Compiler (Tokenizing)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-docs-0.png
---

In this part, we begin implementing the actual parts of the compiler. This will begin with [Tokenizing (AKA lexical analysis)](https://en.wikipedia.org/wiki/Lexical_analysis), which breaks source up into discrete 'words' (or tokens).


<!--more-->

## `ckc` Structure

We only need to compile a subset of Kata -- we won't worry about for loops, for-each loops, try/catch blocks, a macro system, or many other features. This will simplify the compiler and reduce the workload. We will also just abort at the first error we encounter, and print a minimal error message -- normally, we would want to print diagnostics, location information, and a detailed message, but that's for the full implementation.

We'll also make it an interpreter, because (believe it or not) that will actually be easier than having to write assembly-specific ones just for this immediate compiler. Below is a helpful diagram showing the stages of our compiler we need to write:

![assets/img/kata-ckc-arch.svg](assets/img/kata-ckc-arch.svg)


Before we begin writing any individual piece, we'll include some code that will make it easy to report compiler errors:

```c++
/* in 'kc.hh' */

/* Single 'word'/'phrase' lexed from inputs symbols */
struct Token {
    /* what kind of token was it */
    enum Kind {
        KIND_EOF = 0,

        KIND_INT,

        KIND_NAME,

        KIND_ADD,
        KIND_SUB,
        KIND_MUL,
        KIND_DIV,

        /* Catch-all describing a combination of tokens */
        KIND_MANY, 
    } kind;

    /* Position in the source code */
    int line, col;
    
    /* Always byte-wise, from the start of 'src' */
    int pos, len;

    /* References */
    const string& src_name;
    const string& src;

    Token(int line_, int col_, int pos_, int len_, const string& src_name_, const string& src_, Kind kind_=Kind::KIND_MANY) : line(line_), col(col_), pos(pos_), len(len_), src_name(src_name_), src(src_), kind(kind_) { }


    /* Return context around a string */
    string getcontext() const {
        /* no context for invalid */
        if (len == 0) return "";
        int i = pos;
        /* skip to first of line */
        while (i > 0 && src[i-1] != '\n') i--;
        int sp = i;
        i = pos;
        while (i < src.size() && src[i] != '\n') i++;

        return src.substr(sp, i - sp);
    }

    operator string() const { return src.substr(pos, len); }

};

inline Token operator+(Token& lhs, Token& rhs) {
    if (lhs.line <= rhs.line) return Token(lhs.line, lhs.col, lhs.pos, rhs.pos+rhs.len-lhs.pos, lhs.src_name, rhs.src_name);
    else return rhs + lhs;
}

/* Represents an identification, which is sometimes called a 'full' name or 'dotted' 
 *   name. Essentially, all identifiers, but it allows '.' between names too
 */
struct ID {
    vector<string> names;

    /* Return the last name */
    string last() const {
        return names[names.size() - 1];
    }

    ID(string& name) : names({name}) {}
    ID(const vector<string>& _names) : names(_names) {}
    ID() {}

    /* Convert to string, which joins the names via '.' */
    operator string() const { 
        string res = names[0];
        for (size_t i = 1; i < names.size(); ++i) {
            res += (string)"." + names[i];
        }
        return res;
    }
};

/* Compilation warnings/errors */
struct Error {

    Token tok;
    string msg;

    Error(Token tok_, const string& msg_) 
        : tok(tok_), msg(msg_) {}

    operator string() const { return tok.src_name + ":" + to_string(tok.line+1) + ":" + to_string(tok.col+1) + ": error: " + msg + "\n" + tok.getcontext(); }
};
struct Warning {

    Token tok;
    string msg;

    Warning(Token tok_, const string& msg_) 
        : tok(tok_), msg(msg_) {}

    operator string() const { return tok.src_name + ":" + to_string(tok.line+1) + ":" + to_string(tok.col+1) + ": warning: " + msg + "\n" + tok.getcontext(); }
};

/** Global Variables **/

extern vector<Error> errors;
extern vector<Warning> warnings;

/* Stack of current tokens, which is used to generate reasonable error messages, for example
 *   by taking the back of the vector
 */
extern vector<Token> tokstk;


/** Functions **/

/* Print members of 'errors' and 'warnings' to stderr, and optionally exit if there were any */
void printerrors(bool exit_if_err=true);
void printwarnings();

/* Read entire file and return as a string (use 'tokstk.back()' for default 'by') */
string readall(string fname, Token& by);

```

Let's put some of these globals in a file `main.cc`:

```c++
/* in 'main.cc'  */
namespace kc {

/* initialize the token stack with this, if an error is thrown 'outside' of a file */
static string _default_tok = "<>";
vector<Token> tokstk = { Token(0, 0, 0, 0, _default_tok, _default_tok) };

vector<Error> errors;
vector<Warning> warnings;

void printerrors(bool exit_if_err) {
    for (auto& it : errors) cerr << (string)it << endl;
    if (exit_if_err && errors.size() > 0) exit(1);

}
void printwarnings() {
    for (auto& it : warnings) cerr << (string)it << endl;
}

string readall(string fname, Token& by) {
    /* I literally laughed out loud when I googled how to do this in C++, 
     *   I guess this is the best way (although it seems like it is probably
     *   wasting memory)
     */
    ifstream fp;
    fp.open(fname);
    if (!fp.is_open()) {
        errors.push_back(Error(by, "No such file: " + fname));
        return "<INVALID FILE>";
    }
    stringstream ss;
    ss << fp.rdbuf();
    return ss.str();
}

} /* namespace kc */
```

So now, we'll have a way to add errors to a global list, and then print them out. We also have some utilitity functions. This will come in handy in the future if we try and make things like template substitution, or we want to handle multiple errors. By handling multiple errors and warnings, we can show the developer more information about multiple things they need to fix, instead of giving them a single error and requiring them to fix that and recompile before giving another.

We also define a `Token` structure that will be generated by our first stage. 


## Tokenize (Lexer)

To transform the raw text of Kata source code into a computer-readable format, we need to implement the first stage of the 'Front End' section of the earlier diagram (Tokenize/Lexer stage). Essentially, to a computer, the source code is just a bunch of bytes -- the computer doesn't know that when we type `int x;` we really mean "declare a variable called 'x' of type 'int'". The computer only sees its ASCII/UTF8 representation: `69 6e 74 20 78 3b 0a`. They lexer won't solve this problem completely; it will essentially say to the computer "there's a word 'int', a space that I can ignore, then a word 'x', then a symbol ';'", which is closer to actually understanding it as a programing language.

This initial transformation is called tokenizing (or lexing), because it turns a string (which is just an array of bytes) into [tokens](https://en.wikipedia.org/wiki/Lexical_analysis#Token). A token is just a collection of these characters that are supposed to be together (like a word, number, or 'phrase'). 

Here's an example:

![assets/img/tokenize-ex0.jpg](assets/img/tokenize-ex0.jpg)


The kinds of tokens are defined in `kc.hh`, in these lines:

```c++
    /* what kind of token was it */
    enum Kind {
        KIND_EOF = 0,

        /* Integer literal (base 10)
         * re: [0-9]+
         */
        KIND_INT,

        /* Identifier/name
         * re: [a-zA-Z_][a-zA-Z_0-9]*
         */
        KIND_NAME,

        /* operators */
        KIND_ADD,
        KIND_SUB,
        KIND_MUL,
        KIND_DIV,

        /* Catch-all describing a combination of tokens */
        KIND_MANY, 
    } kind;
```

We'll add tokens as we go, but we'd like to first implement these basic rules, and make sure we can test it out. Let's define a function called `tokenize` in our header:

```
/* Return a list of tokens (ending with 'KIND_EOF') */
vector<Token> tokenize(const string& src_name, const string& src);
```

Let's define the function in a new file `lexer.cc`:

```c++
#include <kc.hh>
using namespace kc;

namespace kc {

vector<Token> tokenize(const string& src_name, const string& src) {
    int line = 0, col = 0, pos = 0, lpos = 0, lline = 0, lcol = 0;
    #define len (pos - lpos)

    int sz = (int)src.size();
    vector<Token> toks;

    /* Generate a token, uses local variables to generate it */
    #define MAKE(_kind) Token(lline, lcol, lpos, len, src_name, src, _kind)

    /* Advance one place in the source code */
    #define ADV() { \
        if (src[pos++] == '\n') { \
            line++; \
            col = 0; \
        } else col++; \
    }

    /* Yield whether the remaining string starts with another string 
     * NOTE: If you're using pure C, you could do 'strncmp(&src[pos], _cstr, strlen(_cstr)) == 0' to perform
     *   this check. In any language, just check whether the next part of 'src' you haven't consumed yet starts
     *   with the given value
     */
    #define NEXTIS(_cstr) (src.find(_cstr, pos) == pos)

    while (pos < sz) {
        /* store start positions of this token */
        lline = line;
        lcol = col;
        lpos = pos;
        char c = src[pos];

        if (c == ' ' || c == '\t' || c == '\n') {
            /* skip whitespace */
            ADV();
        } else {
            errors.push_back(Error(MAKE(Token::KIND_MANY), (string)"unexpected character: '" + c + "'"));
            return {};
        }
    }

    toks.push_back(Token(line, col, pos, 0, src_name, src, Token::KIND_EOF));
    return toks;
}

} /* namespace kc */
```

This will skip all whitespace, but throw an error on anything else. Changing `main` function (in `main.cc`, but remeber to put this function OUTSIDE of the `namespace kc` block):

```c++
int main(int argc, char** argv) {
    if (argc != 1 + 1) {
        fprintf(stderr, "usage: %s [file]\n", argv[0]);
        return 1;
    }
    string src_name = argv[1];
    string src = readall(src_name, tokstk.back() /* default, which will be '<>' */);
    printerrors();

    vector<Token> toks = tokenize(src_name, src);

    printerrors();
    printwarnings();

    size_t ct = 0;
    for (auto& it : toks) {
        cout << ct++ << ": " << (string)it << endl;
    }

	return 0;
}
```

Let's create a simple example file, I'll call it `ex.kata`

If we compile this, we should be able to actually run it as a file:


```
$ echo "" > ex.kata
$ make && ./ckc ex.kata
0:
$ echo "xyz + 123" > ex.kata
$ make && ./ckc ex.kata
ex.kata:1:1: error: unexpected character: 'x'
```

Let's go back to `lexer.cc`, and specifically, the inner loop where we check the current character (`c`) and decide where to go from there:

```c++
while (pos < sz) {
    lline = line;
    lcol = col;
    lpos = pos;
    char c = src[pos];

    if (c == ' ' || c == '\t' || c == '\n') {
        /* skip whitespace */
        ADV();
    } else {
        errors.push_back(Error(MAKE(Token::KIND_MANY), (string)"unexpected character: '" + c + "'"));
        return {};
    }
}
```

We want to recognize names (like `xyz` in the example), integers (like `123`), and operators. So, we need to check the current character and see if it is a valid start of those. Let's define a few utility functions:

```c++
/* in 'lexer.cc' */

/* Test if a character is a valid digit in base 'b' */
static bool is_digit(int c, int b=10) {
    assert(b == 10);
    return '0' <= c && c <= '9';
}

/* Test if a character is a valid start of an identifier */
static bool is_name_s(int c) {
    return ('a' <= c && c <= 'z') || ('A' <= c && c <= 'Z') || c == '_';
}

/* Test if a character is a valid middle of an identifier */
static bool is_name_m(int c) {
    return is_name_s(c) || is_digit(c, 10);
}
```


The operators (`+`, `-`, `*`, `/` for now) will use a macro and just check if they're equal

We can then parse the name, integers, and operators like this (and we'll ignore comments):

```c++
while (pos < sz) {
    lline = line;
    lcol = col;
    lpos = pos;
    char c = src[pos];

    if (c == ' ' || c == '\t' || c == '\n') {
        /* skip whitespace */
    } else if (NEXTIS("//")) {
        /* skip until next line */
        int cur_line = line;
        while (pos < sz && line == cur_line) ADV();
        /* don't add a token for comments */

    } else if (NEXTIS("/*")) {
        /* skip until next line */
        int cur_line = line;
        while (pos < sz && !NEXTIS("*/")) ADV();
        
        /* at the end */
        if (NEXTIS("*/")) {
            ADV();
            ADV();
        } else {
            errors.push_back(Error(MAKE(Token::KIND_MANY), "No end to multiline comment started here"));
            return {};
        }
    } else if (is_digit(c, 10)) {
        do {
            ADV();
        } while (pos < sz && is_digit(src[pos], 10));

        toks.push_back(MAKE(Token::KIND_INT));
    } else if (is_name_s(c)) {
        do {
            ADV();
        } while (pos < sz && is_name_m(src[pos]));

        toks.push_back(MAKE(Token::KIND_NAME));
    }
    /* macro to generate 'else if' statements for a string constant */
    #define CASE_OP(_kind, _opstr) else if (NEXTIS(_opstr)) { \
        int _left = (int)((string)_opstr).size(); \
        while (_left-- > 0) { ADV(); } \
        toks.push_back(MAKE(_kind)); \
    }

    CASE_OP(Token::KIND_ADD, "+")
    CASE_OP(Token::KIND_SUB, "-")
    CASE_OP(Token::KIND_MUL, "*")
    CASE_OP(Token::KIND_DIV, "/")

    else {
        errors.push_back(Error(MAKE(Token::KIND_MANY), (string)"unexpected character: '" + c + "'"));
        return {};
    }
}
```

The code (in my opionion) largely speaks for itself. You keep consuming characters while they fit the current token type, and for constants you just check if the string starts with them, and emit a token if so (then, you must use `ADV()` the length of the string to skip over it). 

If we recompile and check again with our last example in `ex.kata`, we have:

```
$ make && ./ckc ex.kata
0: xyz
1: +
2: 123
3: 
```



At this point, we have transformed the incoming source code into units of tokens -- but they haven't been parsed yet. We'll need to do that next time.

I'm going to go ahead and define my operators, and a bunch of random grammar symbols. These are pretty straightforward if you understand the above, with a few exceptions. For example, you need to put operators that contain other operators before those other operators, or else you'll get some weird cases.

For example, I'm going to have the operators `++`, as well as `+`, so I need to put `++` before `+`. Otherwise, `++` will parse as 2 `+` operators instead of a single `++` operator. Here's the full `while` loop:

```c++
while (pos < sz) {
    lline = line;
    lcol = col;
    lpos = pos;
    char c = src[pos];

    if (c == ' ' || c == '\t' || c == '\n') {
        ADV();
    } else if (NEXTIS("//")) {
        /* skip until next line */
        int cur_line = line;
        while (pos < sz && line == cur_line) ADV();
        /* don't add a token for comments */

    } else if (NEXTIS("/*")) {
        /* skip until next line */
        int cur_line = line;
        while (pos < sz && !NEXTIS("*/")) ADV();
        
        /* at the end */
        if (NEXTIS("*/")) {
            ADV();
            ADV();
        } else {
            errors.push_back(Error(MAKE(Token::KIND_MANY), "No end to multiline comment started here"));
            return {};
        }

    } else if (is_digit(c, 10)) {
        do {
            ADV();
        } while (pos < sz && is_digit(src[pos], 10));

        toks.push_back(MAKE(Token::KIND_INT));
    } else if (is_name_s(c)) {
        do {
            ADV();
        } while (pos < sz && is_name_m(src[pos]));

        toks.push_back(MAKE(Token::KIND_NAME));
    } else if (c == '"') {
        ADV();
        while (pos < sz && src[pos] != '"') {
            /* we need to skip escape codes, so that 
                *   "\"" contains a single character of the quote mark
                */
            if (pos < sz && src[pos] == '\\') ADV();
            ADV();
        }
        if (src[pos] == '"') {
            ADV();
            toks.push_back(MAKE(Token::KIND_STR));
        } else {
            errors.push_back(Error(MAKE(Token::KIND_STR), "No end to string literal started here"));
            return {};
        }
    }

    #define CASE_OP(_kind, _opstr) else if (NEXTIS(_opstr)) { \
        int _left = (int)((string)_opstr).size(); \
        while (_left-- > 0) { ADV(); } \
        toks.push_back(MAKE(_kind)); \
    }

    CASE_OP(Token::KIND_OCTOTHORPE, "#")
    CASE_OP(Token::KIND_DOT, ".")
    CASE_OP(Token::KIND_COM, ",")
    CASE_OP(Token::KIND_COL, ":")
    CASE_OP(Token::KIND_SEMI, ";")
    CASE_OP(Token::KIND_LPAR, "(")
    CASE_OP(Token::KIND_RPAR, ")")
    CASE_OP(Token::KIND_LBRC, "{")
    CASE_OP(Token::KIND_RBRC, "}")
    CASE_OP(Token::KIND_LBRK, "[")
    CASE_OP(Token::KIND_RBRK, "]")
    CASE_OP(Token::KIND_LARROW, "<-")
    CASE_OP(Token::KIND_RARROW, "->")

    CASE_OP(Token::KIND_AADD, "+=")
    CASE_OP(Token::KIND_ASUB, "-=")
    CASE_OP(Token::KIND_AMUL, "*=")
    CASE_OP(Token::KIND_ADIV, "/=")
    CASE_OP(Token::KIND_AMOD, "%=")
    CASE_OP(Token::KIND_ALSH, "<<=")
    CASE_OP(Token::KIND_ARSH, ">>=")
    CASE_OP(Token::KIND_AOR, "|=")
    CASE_OP(Token::KIND_AXOR, "^=")
    CASE_OP(Token::KIND_AAND, "&=")

    CASE_OP(Token::KIND_ADDADD, "++")
    CASE_OP(Token::KIND_ADD, "+")
    CASE_OP(Token::KIND_SUBSUB, "--")
    CASE_OP(Token::KIND_SUB, "-")
    CASE_OP(Token::KIND_MUL, "*")
    CASE_OP(Token::KIND_DIV, "/")
    CASE_OP(Token::KIND_MOD, "%")
    CASE_OP(Token::KIND_LSH, "<<")
    CASE_OP(Token::KIND_RSH, ">>")
    CASE_OP(Token::KIND_OROR, "||")
    CASE_OP(Token::KIND_OR, "|")
    CASE_OP(Token::KIND_XOR, "^")
    CASE_OP(Token::KIND_ANDAND, "&&")
    CASE_OP(Token::KIND_AND, "&")
    
    CASE_OP(Token::KIND_LT, "<")
    CASE_OP(Token::KIND_LE, "<=")
    CASE_OP(Token::KIND_GT, ">")
    CASE_OP(Token::KIND_GE, ">=")
    CASE_OP(Token::KIND_EQ, "==")
    CASE_OP(Token::KIND_NE, "!=")

    CASE_OP(Token::KIND_ASSIGN, "=")

    CASE_OP(Token::KIND_NOT, "!")
    CASE_OP(Token::KIND_SQIG, "~")

    else {
        errors.push_back(Error(MAKE(Token::KIND_MANY), (string)"unexpected character: '" + c + "'"));
        return {};
    }
}
```



