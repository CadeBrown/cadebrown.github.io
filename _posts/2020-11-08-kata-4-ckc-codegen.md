---
layout: post
title: "Kata (#4) - First Compiler (Code Generation with LLVM)"
categories: [plt]
tags: [plt]
series: kata
thumb: assets/img/kata-ast-0.svg
---

Since we have operators, function calls, and the basics being parsed, we can start actually generating code from the resulting AST. We'll be implementing it seperately than the parser.

<!--more-->

Many tutorials will generate code in exact conjunction with the grammar rules -- but this tutorial will treat them as completely seperate processes, seperated in the diagram below:

![assets/img/kata-ckc-arch.svg](assets/img/kata-ckc-arch.svg)

Eventually, we may add more stages to this architecture, and support other results of code generation (for example, perhaps we'd like transpilation to C/C++). For now, we'll keep things simply and just directly translate to LLVM IR.


Up until now, ASTs have been very abstract -- they don't include things like declarations, type specifications, or even resolution of variables. During this part (code generation), we have to actually resolve all of that.

Before we get started, we'll need to include some code in our header to allow us to hash `std::pair` and `std::vector`, which is required by `std::unordered_map`:

```c++

/* Allows hashing a pair of any kind and vectors, used for hash tables */
namespace std {
    template <typename U, typename V>
    struct hash< pair<U, V> > {
        size_t operator()(const pair<U, V>& p) const {
            return hash<U>{}(p.first) ^ hash<V>{}(p.second);
        }
    };
    template <typename T>
    struct hash< vector<T> > {
        size_t operator()(const vector<T>& p) const {
            size_t res = 5183;
            for (const T& it : p) res = ((res << 13) + (res << 5)) ^ hash<T>{}(it);
            return res;
        }
    };
}

```

Make sure to put this code *outside* of the `namespace kc`, since it needs to be defined in the `std::` namespace, and not `kc::std::`


### Type System

We need a type system for Kata. We'll expand on it as we go, but here will be the basics:

  * Integer types, support for different bit widths, and support for signed/unsigned types
    * `si8`, `ui8`, `si64`, etc.
    * `bool` is a 1 bit integer (although it may take up 1 byte in memory)
    * C++ Type: `IntType`
  * Floating point types, using [IEEE 754 format](https://en.wikipedia.org/wiki/IEEE_754)
    * `ieee32`, `ieee64`, etc.
    * C++ Type: `IeeeType`
  * Pointer types, which represent a memory location of another object of another type. Syntax is a bit different than C
    * `&int`, `&&char`, etc.
    * C++ Type: `PointerType`
  * Function types, which represent a transformation/application
    * `(int,int)->int` signals a function, taking 2 `int` arguments, and returning an `int`
    * C++ Type: `FunctionType`
  * Alias types, which are equivalent to the type they are aliasing, but may print another name in errors. Useful for more readable code
    * `int` is an alias to `si32`
    * `double` is an alias to `ieee64`
    * C++ Type: `AliasType`

We'll define these as subclasses an as abstract type, called `kc::Type`. Note that we'll also be generating LLVM code, which has its own type system (indeed, it has names like `llvm::FunctionType` that are similar to ours -- I use `llvm::` before any LLVM type). However, we need our own, since LLVM's type system is low level, and won't have support for all the features we would like. However, we'll write a converter which takes a `kc::Type*` and returns the corresponding `llvm::Type*` used in the generated IR.

Every `kc::Type` object will have a name (which will be printed in error messages, and used in other types which reference it). Furthermore, we'll want to cache the types, so that we only create specific types once. We'll define these subtypes to each have their own cache, and instead of creating a type via `new SubType()`, we'll use a static function `SubType::get(...)`, that will first check the cache of existing types, and only create the type if it is the first time it is requested.

So, for example, to get a 32 bit signed integer, we'd use: `IntType::get(32, true)`

Here's the code for the 5 types we've specified so far:

```c++
/* Represents a type in Kata. This is an abstract base type and cannot be instantiated -- use
 *   a subtype's 'get' method (such as `IntType::get()`, `IeeeType::get()`, etc)
 */
struct Type {

    /* Printable name */
    string name;

    /* The size of the type, in bytes */
    int size;

    /* Virtual destructor, so that type hierarchy is used for subtypes */
    virtual ~Type() {};

    /* De-alias, return the base type which is not an alias type */
    Type* dealias();

};

struct IntType : public Type {

    /* Number of bits the integer has 
     * Defined for 1 and 8*i
     */
    int bits;

    /* If true, the type is signed. unsigned otherwise */
    bool sgn;

    static unordered_map< pair<int/*bits*/, bool/*sgn*/>, IntType* > cache;

    static IntType* get(int bits=32, bool sgn=true) {
        assert((bits == 1 || bits % 8 == 0) && "only integers which are either 1 bit (boolean), or multiples of 8 bits are legal");

        /* Attempt to find in the cache */
        pair<int, bool> key = make_pair(bits, sgn);
        auto it = cache.find(key);
        if (it != cache.end()) return cache[key];

        /* Make new type */
        IntType* res = new IntType();

        res->name = bits == 1 ? "bool" : ((sgn ? "si" : "ui") + to_string(bits));
        res->size = (bits + 7) / 8;
        res->bits = bits;
        res->sgn = sgn;

        return cache[key] = res;
    }
};

struct IeeeType : public Type {

    /* Total number of bits in the type 
     * Defined for 8, 16, 32, 64, 128, and 128+32*i
     */
    int bits;

    static unordered_map< int/*bits*/, IeeeType* > cache;

    static IeeeType* get(int bits=32) {
        if (bits < 128) {
            if (bits == 8 || bits == 16 || bits == 32 || bits == 64) {
                /* okay */
            } else {
                /* bad */
                assert(false && "for bit sizes <128, must be a valid IEEE specified bit length");
            }
        } else {
            assert((bits - 128) % 32 == 0 && "for bit sizes >=128, must be a multiple of 32");
        }
        /* Attempt to find in the cache */
        int key = bits;
        auto it = cache.find(key);
        if (it != cache.end()) return cache[key];

        /* Make new type */
        IeeeType* res = new IeeeType();

        res->name = (string)"ieee" + to_string(bits);
        res->size = (bits + 7) / 8;
        res->bits = bits;

        return cache[key] = res;
    }
};

struct PointerType : public Type {

    /* The type pointed to */
    Type* of;

    static unordered_map< Type* /*of*/, PointerType* > cache;

    static PointerType* get(Type* of) {
        /* Attempt to find in the cache */
        Type* key = of;
        auto it = cache.find(key);
        if (it != cache.end()) return cache[key];

        /* Make new type */
        PointerType* res = new PointerType();

        res->name = (string)"&" + of->name;
        res->size = sizeof(void*) /* if cross compiling, you should find another way to specify! */;
        res->of = of;

        return cache[key] = res;
    }
};

struct FunctionType : public Type {

    /* Return type of the function */
    Type* rtype;

    /* Parameter types of the function */
    vector<Type*> ptypes;

    static unordered_map< pair< Type* /*rtype*/, vector<Type*>/*ptypes*/ >, FunctionType* > cache;

    static FunctionType* get(Type* rtype, const vector<Type*>& ptypes) {

        /* Attempt to find in the cache */
        pair< Type*, vector<Type*> > key = make_pair(rtype, ptypes);
        auto it = cache.find(key);
        if (it != cache.end()) return cache[key];

        /* Make new type */
        FunctionType* res = new FunctionType();

        res->name = "(";
        for (size_t i = 0; i < ptypes.size(); ++i) {
            if (i > 0) res->name += ",";
            res->name += ptypes[i]->name;
        }
        res->name += ")->";
        res->name += rtype->name;
        res->size = sizeof(void(*)()); /* is really a function pointer */
        res->rtype = rtype;
        res->ptypes = ptypes;

        return cache[key] = res;
    }
};

struct AliasType : public Type {

    /* The type being aliased */
    Type* of;

    static unordered_map< pair<string/*name*/, Type* /*of*/>, AliasType* > cache;

    static AliasType* get(Type* of, const string& name) {
        /* Attempt to find in the cache */
        pair<string, Type*> key = make_pair(name, of);
        auto it = cache.find(key);
        if (it != cache.end()) return cache[key];

        /* Make new type */
        AliasType* res = new AliasType();
    
        res->name = name;
        res->size = of->size;
        res->of = of;

        return cache[key] = res;
    }
};

```

Eventually, we'll add a `StructType`, which can have members, but for right now, this will be enough to get some working examples going.

We'll need to add a definition of the `cache` maps for each type as well as the `dealias()` function in `main.cc`:

```c++

/* type caches */
unordered_map< pair<int, bool>, IntType* > IntType::cache;
unordered_map< int, IeeeType* > IeeeType::cache;
unordered_map< pair<string, Type*>, AliasType* > AliasType::cache;
unordered_map< Type*, PointerType* > PointerType::cache;
unordered_map< pair< Type*, vector<Type*> >, FunctionType* > FunctionType::cache;

Type* Type::dealias() {
    Type* res = this;
    while (AliasType* base = dynamic_cast<AliasType*>(base)) res = base->of;
    return res;
}

```


### LLVM

In our main header, we'll also need to include LLVM's headers, which define the API we'll use to build [LLVM IR](https://llvm.org/devmtg/2017-06/1-Davis-Chisnall-LLVM-2017.pdf). This tutorial will explicity prefix LLVM types with `llvm::`, and *not* use `using namespace llvm;`, for clarity and to avoid naming conflicts.

```c++

/* LLVM API */
#include "llvm/Support/raw_ostream.h"
#include "llvm/ADT/APFloat.h"
#include "llvm/Target/TargetMachine.h"
#include "llvm/ExecutionEngine/ExecutionEngine.h"

#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Function.h"
#include "llvm/IR/BasicBlock.h"
#include "llvm/IR/Type.h"
#include "llvm/IR/DerivedTypes.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/Constants.h"
#include "llvm/IR/Verifier.h"
#include "llvm/IR/PassManager.h"

```

We may add more headers in the future, but this is what we're using currently. Let's also add a function of our own, which converts an program in AST format to an `llvm::Module`: 

```c++

/* Generate an LLVM module representing an AST for a program, returns NULL if failure */
unique_ptr<llvm::Module> gen_llvm(llvm::LLVMContext& ctx, AST* prog);

```

We'll keep all the LLVM-specific code in the file `gen_llvm.cc`. I think this is good practice, since we may want to implement a `x86` compiler, or some specific architecture, or allow for building without LLVM entirely. Also, it's best to limit the surface area between LLVM and our compiler, since we'll need to re-invent things like type systems, modules, and so forth independently -- if we use LLVM all over the place, we might find ourselves limited to LLVM's constructs, which are admittedly lower level than the language we are creating.




