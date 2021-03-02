---
layout: post
title: "Chess Engine (#0) - Setup"
categories: [chess]
tags: [cce, chess]
series: cce
thumb: assets/img/chess-startpos.jpg
---

Let's learn how to program a chess engine, from scratch, in C/C++! Specifically, we'll target [UCI (Universal Chess Interface)](https://en.wikipedia.org/wiki/Universal_Chess_Interface) so we can play with various GUIs on multiple platforms

<!--more-->

## History

[Chess](https://en.wikipedia.org/wiki/Chess) is a well known game, and has been played for hundreds of years by millions of people. For about 97% of that time, the best players of chess have all been humans. For the last 3%, that title has been held by [some sort of computer](https://en.wikipedia.org/wiki/Computer_chess), and in that time, the gap between the best human player and the best computer player has grown astronomically.

In fact, the gap has gotten so large that even world champions [refuse to play engines](https://www.dw.com/en/world-chess-champion-magnus-carlsen-the-computer-never-has-been-an-opponent/a-19186058) because it wouldn't even be close. 

For your own reading and entertainment, here are some popular computer chess programs:

  * [Deep Blue](https://en.wikipedia.org/wiki/Deep_Blue_(chess_computer)), the first non-human chess champion (the first to beat a world champion)
  * [Alpha Zero](https://en.wikipedia.org/wiki/AlphaZero#Chess), Google's (originally DeepMind's) chess program which trains from zero human knowledge
    * This is the most important development in computer chess, as it showed that humans teaching the engine actually results in **worse** performance

## Methods

There are many methods for writing a chess engine, ranging from simple to complex. There are many considerations that need to be made, which we will cover. In all cases, we will make our engine [UCI compatible](https://en.wikipedia.org/wiki/Universal_Chess_Interface), so we can use many chess GUI programs to test it. Here is a link to download the UCI interface: [https://www.shredderchess.com/download.html](https://www.shredderchess.com/download.html)

We will originally write a so-called "traditional" engine, which consists of a few parts:

  * Move generator, which generates a list of legal moves
  * Static position evaluator, which gives a score to a position showing whether white or black is winning
  * Game tree search, which uses the move generator and static position evaluator to find which moves lead to the best position, and thus which move should be played

In the future, I plan to expand this series to include machine learning, which will help with the static position evaluator, as well as move generator (the idea is to use a machine learning model to tell which moves are more promising, and try them out first)


## Setup

We will be programming this engine in C/C++, and using makefile-driven development. And, for reference, I will use links to the [Chess Programming Wiki](https://www.chessprogramming.org/), which is a great resource. I'll be calling my chess engine `cce` (Cade's Chess Engine)

### Build System

We'll use makefile to build our project. In general, our project structure will look like:

  * `src`: Contains C++ code implementing the program
  * `include`: Contains C++ header code re-used by code in `src`

The file `makefile` describes how to build our project:

```makefile
# makefile - build system for cce (Cade's Chess Engine)
#
# Just run `make` to build `cce`, which is the UCI-compatible binary
#
# @author: Cade Brown <cade@cade.site>

# -*- Programs -*-

# C++ compiler
CXX          ?= c++

CXXFLAGS     += -std=c++11
LDFLAGS      += 

# -*- Files -*-

src_CC       := $(wildcard src/*.cc)
src_HH       := $(wildcard include/*.hh)


# -*- Output -*-

# Output binary which can be ran
cce_BIN      := cce

# -*- Generated -*-

src_O        := $(patsubst %.cc,%.o,$(src_CC))


# -*- Rules -*-

.PHONY: default clean FORCE

default: $(cce_BIN)

clean: FORCE
	rm -f $(wildcard $(src_O) $(cce_BIN))

FORCE: 

$(cce_BIN): $(src_O)
	$(CXX) $(CXXFLAGS) $(LDFLAGS) $^ -o $@

%.o: %.cc $(src_HH)
	$(CXX) $(CXXFLAGS) -Iinclude -fPIC -c $< -o $@

```

### Source Code

First, we'll create a header (`include/cce.hh`), which defines datastructures, includes required headers, and defines constants. Here's all the C/C++ headers we need to include at the moment:


```c++
// in 'include/cce.h'

// C standard
#include <assert.h>
#include <stdint.h>

// Stanard library
#include <iostream>
#include <sstream>

// STL
#include <string>
#include <vector>

// Use C++ standard libary without 'std::' prefix
using namespace std;
```

And, we'll put all our code in the `cce::` namespace (but, we will have `using namespace cce` to make it less verbose).

We can define some enum constants, so our code is more readable:

```c++
// in 'include/cce.h'

/* Constants */

// Color enumeration
enum Color {
    // W: White
    WHITE    = 0,
    // B: Black
    BLACK    = 1,
};

// Piece enumeration
enum Piece {

    // K: King
    K        = 0,
    // Q: Queen
    Q        = 1,
    // B: Bishop
    B        = 2,
    // N: Knight (since K is used for King)
    N        = 3,
    // R: Rook
    R        = 4,
    // P: Pawn
    P        = 5,

};

// Number of colors
#define N_COLORS 2

// Number of pieces
#define N_PIECES 6

// FEN for the starting position
// (we'll get to this later)
#define FEN_START "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

```

We need a way to represent a tile. For example, `a1` is the position of the white queenside rook (at the start). However, we can't be referring to strings in the source code, as that will be inefficient. Instead, we can use an `int`, and store them as positions `0` through `63`, basically laying tiles out in one long row. For example:

  * `a1` is represented as `0`
  * `b1` is represented as `1`
  * `a2` is represented as `8`

In general, the pattern will be:

  * Convert both coordinates to zero-based integers. For example, `a -> 0`, `b -> 1`, `c -> 2`, etc (for the files), and `1 -> 0`, `2 -> 1`, etc (for the ranks)
  * Then, compute `8 * rank_zerobased + file_zerobased` to get the value from `0` to `63`

Here is a diagram showing the index of each tile (from white's perspective):

![assets/img/chess-tileidx.jpg](assets/img/chess-tileidx.jpg)

In code, we won't specify with tile names, but we can use the `TILE` macro to convert 2D coordinates to the 1D integer:

```c++
// in 'include/cce.h'

// Creates a position from the board, from a rank (_i) and file (_j)
// NOTE: These are 0-indexed! For example, the square 'a1' is TILE(0, 0)
// Examples:
// b3 -> TILE(b->1, 3->2) = TILE(1, 2) 
#define TILE(_i, _j) (8 * (_i) + (_j))

// Un-does the 'TILE' macro on '_val', and decomposes it into the '_i' and '_j' variables
#define UNTILE(_i, _j, _val) do { \
    int val_ = _val; \
    (_i) = val_ % 8; \
    (_j) = val_ / 8; \
} while (0)

```





Now, we need some way of representing a board. Most people would opt for an 8x8 array of tiles, containing the color and piece of each tile (or, something like `-1` for empty tiles). While this is the obvious solution, and would certainly work, we want to make a fast and efficient engine. Believe it or not, there are better ways of doing this!

We'll use [bitboards](https://www.chessprogramming.org/Bitboards), which are basically 64 bit integers which are interpreted as values of a chess board. Bitboards may be difficult to explain to people, and it may be difficult to see why we want to go through the trouble of such a thing. However, you will soon see the benefit of bitboards


  * Since there are `8*8==64` tiles on the chess board, that means each bit in a 64 bit integer can correspond to a single tile
  * Multiple bit boards are needed for a single chess board, since 1 bit is not enough to store information about each square (i.e. you need at least a few to store color and piece type)
  * Since bitboards are essentially just integers, bitwise operations can be used to create efficient algorithms for move generation and checking

In C++, we can represent a bitboard with a `uint64_t` (defined in `stdint.h`). However, we don't want to type that all over the place. So, let's make a typedef:

```c++
// in 'include/cce.h'

// cce::bb - Bitboard integer type
//
// A bitboard is a collection of 64 bits, one corresponding to each tile
//   on the board. They typically answer a question like "is a piece on tile X?",
//   and can be combined with bitwise operators
//
// Use 'ONEHOT(_i)' to create a bitboard with a single bit set
//
typedef uint64_t bb;

// Creates a bitmask from a single bit, _i, as a 1 bit, the rest being zeros
#define ONEHOT(_i) (1ULL << (_i))

```

Now, we can write `bb` where we want to specify a bitboard. Whenever you see this in the code, just remember it is an integer that has 1 bit for every tile on the chess board. You'll notice that, as I said earlier, multiple bitboards are needed for a single chess board. So, let's go ahead and define a structure for a chess board state, which we'll call `State`:


```c++
// in 'include/cce.h'
// cce::move - Simple move structure, just containing the from and to 
//
//
struct move {

    // Tile being moved from
    int from;

    // Tile being moved to
    int to;

    move(int from_=-1, int to_=-1) : from(from_), to(to_) {}

    // Returns whether the move is unintialized or out of range
    bool isbad() const { return from < 0 || to < 0 || from >= 8 || to >= 8; }

};


// cce::State - Chess board state
//
// This is like the board, except it also keeps bits storing
//   castling rights, en-passant, etc
//
struct State {
    
    // Bitboard telling which color occupies which tile
    bb color[N_COLORS];

    // Bitboard array (indexed by 'Piece::*' enum members) telling which
    //   pieces are located where on the board
    // 0==not on this tile, 1==on this tile
    bb piece[N_PIECES];

    // Which color is about to move?
    Color tomove;

    // Castling rights, whether W==white, B==black, K==Kingside, Q==Queenside
    // i.e. 'c_WK' tells whether the White king can castle Kingside
    bool c_WK, c_WQ;
    bool c_BK, c_BQ;

    // En-passant target square (i.e. the square on which it could be captured)
    // Or, -1 if there is no such square
    // This should be reset every half-move
    int ep;

    // Half-moves since last capture or pawn advance
    // Used for the fifty-move rule
    int hmclock;

    // The number of full-moves, starting at 0, and incremented after black's move
    int fullmove;

    // Initializes as empty state
    State() {
        for (int i = 0; i < N_COLORS; ++i) {
            color[i] = 0;
        }
        for (int i = 0; i < N_PIECES; ++i) {
            piece[i] = 0;
        }
        tomove = Color::WHITE;
        c_WK = c_WQ = c_BK = c_BQ = true;
        ep = -1;
        hmclock = 0;
        fullmove = 0;
    }

    // Create a new state from FEN notation
    // SEE: https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation
    static State from_FEN(const string& fen);

    // Convert to FEN notation
    // SEE: https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation
    string to_FEN() const;

    // Gets a list of valid moves (from the 'tomove's players perspective), populating 'res'
    // Clears 'res' first
    // If 'ignorepins==true', then generate moves ignoring pinned pieces
    // If 'ignorecastling==true', then generate moves ignoring castling
    void getmoves(vector<move>& res, bool ignorepins=false, bool ignorecastling=false) const;

    // Queries a tile on the board, and returns whether it is occupied
    // If it was occupied, sets 'c' and 'p' to the color and piece that occupied
    //   it, respectively
    bool query(int tile, Color& c, Piece& p) const {
        bb m = ONEHOT(tile);
        for (int i = 0; i < N_PIECES; ++i) {
            if (piece[i] & m) {
                // Found
                c = (color[Color::WHITE] & m) ? Color::WHITE : Color::BLACK;
                p = Piece(i);
                return true;
            }
        }
        // Not found
        return false;
    }

};

```

So, our structure stores a bitboard corresponding to color, and one for each game piece kind. We also store some extra information about which player's turn it is, castling rights, en-passant square (since it can only happen the move *directly* after a pawn moves 2 squares), and a half-move clock, which is used in the fifty-move rule for automatic draws.


There are also some methods here, the most important being `query`, which allows you to check whether a square is occupied, and by which piece. The basic logic is fairly obvious, we convert the tile to a mask `m`, and then check if any pieces occupy that square. If they do, then we check the color bitboard, and set `c` and `p` appropriately. If nothing was found, we return `false`.


There are also methods that deal with [FEN](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation) (converting to and from). We'll cover that next post, when we actually start writing code! See you then!



