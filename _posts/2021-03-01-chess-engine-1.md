---
layout: post
title: "Chess Engine (#1) - FEN, UCI"
categories: [chess]
tags: [cce, chess]
series: cce
thumb: assets/img/chess-sicdef.jpg
---

This installment will focus on parsing [FEN](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation), outputting FEN, and starting to interact with [UCI (Universal Chess Interface)](https://en.wikipedia.org/wiki/Universal_Chess_Interface)

<!--more-->

## Utils

We will need a few utility functions, which I defined in `include/cce.h` and have placed in `src/util.cc`:

```c++
// in 'include/cce.h'

/* Utilities */

// Returns a string representing the algebraic name for a tile
const string& tile_name(int tile);

// Returns a string representing a specific color and piece
// White are uppercase, black are lowercase
const string& cp_name(Color c, Piece p);
```

```c++
// in 'src/util.cc'

// Internal array of square names
static string i_tile_names[] = {
    "a1", "b1", "c1", "d1", "e1", "f1", "g1", "h1",
    "a2", "b2", "c2", "d2", "e2", "f2", "g2", "h2",
    "a3", "b3", "c3", "d3", "e3", "f3", "g3", "h3",
    "a4", "b4", "c4", "d4", "e4", "f4", "g4", "h4",
    "a5", "b5", "c5", "d5", "e5", "f5", "g5", "h5",
    "a6", "b6", "c6", "d6", "e6", "f6", "g6", "h6",
    "a7", "b7", "c7", "d7", "e7", "f7", "g7", "h7",
    "a8", "b8", "c8", "d8", "e8", "f8", "g8", "h8",
};


// Internal array of color-piece names
static string i_cp_names[][N_PIECES] = {
    {"K", "Q", "B", "N", "R", "P"},
    {"k", "q", "b", "n", "r", "p"},
};

const string& tile_name(int tile) {
    assert(0 <= tile && tile < 64);
    return i_tile_names[tile];
}

const string& cp_name(Color c, Piece p) {
    assert(0 <= c < 2);
    assert(0 <= p < N_PIECES);
    return i_cp_names[c][p];
}

```

These functions are fairly straightforward, and allow our output functions to be more readable.

## FEN

[FEN](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation) is a notation for a game state. Notably, it does not include the entire history of moves, but rather the bare essentials of the information required to play the game at a given position. This will be how we communicate, through text, about positions.

In `src/State.cc`, we will need to implement FEN reading and writing, through the `State::from_FEN` and `State::to_FEN` methods:

```c++
// in 'src/State.cc'

State State::from_FEN(const string& fen) {
    State r;
    for (int i = 0; i < N_COLORS; ++i) {
        r.color[i] = 0;
    }
    for (int i = 0; i < N_PIECES; ++i) {
        r.piece[i] = 0;
    }

    // Position in the string
    int pos = 0;

    // Input pieces on the board
    for (int j = 7; j >= 0; --j) {

        // File position
        int i = 0;

        // Keep going until '/' is hit (rank seperator), or we run out of input, or go out
        //   of range
        while (pos < fen.size() && fen[pos] != '/' && i < 8) {
            char chr = fen[pos];
            pos++;

            Color c;
            Piece p;

            // Check whether empty spaces, or a piece located on the relevant square
            if ('0' <= chr && chr <= '9') {
                // Skip these squares
                i += chr - '0';
                continue;

            } else if (chr == 'K') {
                c = Color::WHITE;
                p = Piece::K;   
            } else if (chr == 'Q') {
                c = Color::WHITE;
                p = Piece::Q;
            } else if (chr == 'B') {
                c = Color::WHITE;
                p = Piece::B;
            } else if (chr == 'N') {
                c = Color::WHITE;
                p = Piece::N;
            } else if (chr == 'R') {
                c = Color::WHITE;
                p = Piece::R;
            } else if (chr == 'P') {
                c = Color::WHITE;
                p = Piece::P;
            } else if (chr == 'k') {
                c = Color::BLACK;
                p = Piece::K;   
            } else if (chr == 'q') {
                c = Color::BLACK;
                p = Piece::Q;
            } else if (chr == 'b') {
                c = Color::BLACK;
                p = Piece::B;
            } else if (chr == 'n') {
                c = Color::BLACK;
                p = Piece::N;
            } else if (chr == 'r') {
                c = Color::BLACK;
                p = Piece::R;
            } else if (chr == 'p') {
                c = Color::BLACK;
                p = Piece::P;
            }
            
            // Create mask of the position where we should insert the piece
            bb m = ONEHOT(TILE(i, j));
            // Set color
            r.color[c] |= m;
            // Make sure the correct bit is set for this piece
            r.piece[p] |= m;
            
            // Advance position
            i++;
        }

        // Skip seperator
        if (j >= 0 + 1) {
            assert(fen[pos] == '/');
            pos++;
        }
    }

    // Parse active color
    assert(fen[pos] == ' ');
    pos++;

    if (fen[pos] == 'w') {
        r.tomove = Color::WHITE;
    } else if (fen[pos] == 'b') {
        r.tomove = Color::BLACK;
    } else {
        // Error, ignore for now
    }
    pos++;

    // Parse castling availability
    assert(fen[pos] == ' ');
    pos++;
    r.c_WK = r.c_WQ = r.c_BK = r.c_BQ = false;

    while (pos < fen.size() && fen[pos] != ' ') {
        char chr = fen[pos];
        pos++;
        if (chr == '-') {
            break;
        } else if (chr == 'K') {
            r.c_WK = true;
        } else if (chr == 'Q') {
            r.c_WQ = true;
        } else if (chr == 'k') {
            r.c_BK = true;
        } else if (chr == 'q') {
            r.c_BQ = true;
        } else {
            // Error, ignore for now
        }
    }

    // Parse en passant target square
    assert(fen[pos] == ' ');
    pos++;

    if (fen[pos] == '-') {
        // No en-passant square
        r.ep = -1;
        pos++;
    } else {
        // Get position
        // Right now, assumes input is correct
        char c0 = fen[pos];
        pos++;
        char c1 = fen[pos];
        pos++;

        // Construct from offsets
        r.ep = TILE(c0 - 'a', c1 - '1');
    }

    // Parse half move clock
    assert(fen[pos] == ' ');
    pos++;

    // Get integer portion
    int spos = pos;
    int slen = 0;
    while (spos + slen < fen.size() && fen[spos + slen] != ' ') {
        slen++;
        pos++;
    }
    r.hmclock = stoi(fen.substr(spos, slen));

    assert(fen[pos] == ' ');
    pos++;

    // Parse full move number
    // Subtract one due to 0-based indexing
    r.fullmove = stoi(fen.substr(pos)) - 1;

    return r;
}

string State::to_FEN() const {
    string r;

    // Output pieces on the board, rank-by-rank
    for (int j = 7; j >= 0; --j) {
        if (j < 7) r += '/';
        // Keep track of empty squares, and we put a digit representing how many
        //   are empty
        int empty = 0;

        // For query output
        Color c;
        Piece p;

        for (int i = 0; i < 8; ++i) {
            if (query(TILE(i, j), c, p)) {
                // Found piece on this tile

                // Dump seperator, if there were empty tiles
                if (empty > 0) r += to_string(empty);
                empty = 0;

                // Now, output the color and piece name
                r += cp_name(c, p);
            } else {
                // Empty tile
                empty++;
            }
        }
        // Dump seperator, if there were empty tiles
        if (empty > 0) r += to_string(empty);
    }

    // Output active color
    r += ' ';
    if (tomove == Color::WHITE) {
        r += 'w';
    } else {
        r += 'b';
    }

    // Castling rights
    r += ' ';
    if (c_WK || c_WQ || c_BK || c_BQ) {
        if (c_WK) r += 'K';
        if (c_WQ) r += 'Q';
        if (c_BK) r += 'k';
        if (c_BQ) r += 'q';
    } else {
        r += '-';
    }

    // En-passant target square
    r += ' ';
    if (ep < 0) {
        r += '-';
    } else {
        r += tile_name(ep);
    }

    // Half-move clock
    r += ' ';
    r += to_string(hmclock);


    // Full-move number
    r += ' ';

    // +1, since it is 1 indexed
    r += to_string(fullmove + 1);


    return r;
}

```

The code is fairly straightforward and linear, although it is terse. You can read the Wikipedia article linked on FEN, and see how the code maps directly to it.

Here are some example FEN strings:

Starting position in FEN:

```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

![assets/img/chess-startpos.jpg](assets/img/chess-startpos.jpg)


The Sicilian Defense in FEN:

```
rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2
```

![assets/img/chess-sicdef.jpg](assets/img/chess-sicdef.jpg)

We store these in `test/`. You should store FEN records in `.fen` files. For example, the two FEN strings are available in `test/startpos.fen` and `test/siciliandefense.fen`


## UCI

[UCI (Universal Chess Interface)](https://en.wikipedia.org/wiki/Universal_Chess_Interface) has been mentioned in this series, but we haven't written any code for it. In this section, we will actually implement (or rather, start to implement) the UCI protocol, and hook up our engine to a chess GUI!

Here's another nice page which explains the UCI interface: [http://wbec-ridderkerk.nl/html/UCIProtocol.html](http://wbec-ridderkerk.nl/html/UCIProtocol.html)


First, we will need to define an `Engine` structure, which is empty for the time being:

```c++
// in 'include/cce.hh'

// cce::Engine - Chess engine implementation
//
//
struct Engine {


};

```

And, we'll create `main.cc`, which will be an entry point for our program:


```c++
// in 'src/main.c'

// Accept UCI commands and feed them to 'eng'
static void do_uci(Engine& eng) {
    // TODO...
}

int main(int argc, char** argv) {
    // Create engine, do UCI
    Engine eng;
    do_uci(eng);
}

```


Now, let's compile and run:

```shell
$ make
g++ -std=c++11 -Iinclude -fPIC -c src/main.cc -o src/main.o
g++ -std=c++11 -Iinclude -fPIC -c src/util.cc -o src/util.o
g++ -std=c++11 -Iinclude -fPIC -c src/Engine.cc -o src/Engine.o
g++ -std=c++11 -Iinclude -fPIC -c src/State.cc -o src/State.o
g++ -std=c++11  src/main.o src/util.o src/Engine.o src/State.o -o cce
$ ./cce
asdf
Expected 'uci' as first command, but got 'asdf'
$ ./cce
uci
```


Now, let's actually handle some UCI commands:

```c++
// in 'src/main.c'


// Splits 'line' into arguments (on spaces), populating 'args'
static void splitargs(const string& line, vector<string>& args) {
    args.clear();

    // Spluts on spaces
    stringstream ss(line);
    string part;
    while (getline(ss, part, ' ')) {
        args.push_back(part);
    }
}


// Accept UCI commands and feed them to 'eng'
static void do_uci(Engine& eng) {
    string line;
    vector<string> args;

    // send some information
    cout << "id name cce 0.1" << endl;
    cout << "id author Cade Brown" << endl;

    cout << "uciok" << endl;

    while (getline(cin, line)) {
        splitargs(line, args);
        if (args.size() == 0) continue;

        // Handle UCI command here
        if (args[0] == "debug") {
            if (args.size() == 2) {
                // Ignore for now, but in the future enable debugging
            } else {
                cerr << "Command 'debug' expected 2 arguments " << endl;
            }
        } else if (args[0] == "uci") {
            // Ignore, as we're always UCI
        } else if (args[0] == "quit") {
            // Quit the entire program
            return;
        } else if (args[0] == "isready") {
            // Just a check-up, always return 'readyok'
            cout << "readyok" << endl;
        } else if (args[0] == "setoption") {
            // Ignore for now
            // Sets an option in a dictionary
        } else if (args[0] == "register") {
            // Ignore for now
        } else if (args[0] == "ucinewgame") {
            // Ignore for now
        } else if (args[0] == "position") {
            if (args.size() < 2) {
                cerr << "Command 'position' expected 2 arguments or more" << endl;
            } else {
                string fen = "";
                if (args[1] == "startpos") {
                    // We need to start from initial position
                    fen = FEN_START;
                } else if (args[1] == "fen") {
                    if (args.size() < 3) {
                        cerr << "Command 'position fen' expected at least 3 arguments giving FEN string" << endl;
                    } else {
                        // Initialize from a FEN string (from remaining arguments)
                        for (int i = 2; i < args.size(); ++i) {
                            if (i > 2) fen.push_back(' ');
                            fen += args[i];
                        }
                    }
                } else {
                    cerr << "Command 'position' expected second argument to be 'startpos' or 'fen'" << endl;
                }
                if (fen.size() > 0) {
                    // Was successful, now set the engine to analyze this position
                    State s = State::from_FEN(fen);

                    // For now, just print it out again
                    cout << "parsed: " << s.to_FEN() << endl;
                }
            }

        } else if (args[0] == "go") {
            // TODO: Start computing

        } else if (args[0] == "stop") {
            // TODO: Stop computing

        } else {
            cerr << "Unknown command: '" << args[0] << "'" << endl;
        }
    }
}
```

The code basically just reads the input line-by-line, and we have blocks that can handle each command. We are choosing to ignore some for right now, but we can always go back and implement it later. We also don't fully implement the `go` command, which can be complicated. There is `go infinite`, as well as `go` with a time increment. Eventually, we will parse all of those and use that information, but for right now this should be fine

Let's test out a few commands (what you should input is shown with `>` starting the line):

```shell
$ make
g++ -std=c++11 -g -Iinclude -fPIC -c src/main.cc -o src/main.o
g++ -std=c++11 -g -Iinclude -fPIC -c src/util.cc -o src/util.o
g++ -std=c++11 -g -Iinclude -fPIC -c src/Engine.cc -o src/Engine.o
g++ -std=c++11 -g -Iinclude -fPIC -c src/State.cc -o src/State.o
g++ -std=c++11 -g  src/main.o src/util.o src/Engine.o src/State.o -o cce
$ ./cce
> uci
> position startpos
parsed: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
> go
```

And, voila, it works! Important to note is the fact that we typed `position startpos`, which then parsed `FEN_START`, and then output it back. Since it is equivalent, we can see that our FEN reader/writer is working for this test case at least. We can also specify different FEN with the `position fen` command:

```shell
$ ./cce
id name cce 0.1
id author Cade Brown
uciok
> uci
> position fen rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2
parsed: rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2
```

It works again! We can be pretty confident it works, but we can implement a rigorous test suite as well. We won't do that now though.

### Multithreading

Here's a catch with UCI: We need to *always* be able to take input, even while we are calculating. So, that means we can't just accept the `go` command, calculate the best move, and wait for a `stop` command, because there could be input in the meantime from the GUI! We don't want to freeze up the GUI, so we need to make our interface multithreaded.


We need to include C++ threading support:

```c++
// in 'cce.hh'

// Multithreading support
#include <mutex>
#include <thread>
```


And modify our structures, adding more features:


```c++
// in 'include/cce.h'

// cce::move - Simple move structure, just containing the from and to 
// (updated from last time, for LAN)
//
struct move {

    // Tile being moved from
    int from;

    // Tile being moved to
    int to;

    move(int from_=-1, int to_=-1) : from(from_), to(to_) {}

    // Returns whether the move is unintialized or out of range
    bool isbad() const { return from < 0 || to < 0 || from >= 8 || to >= 8; }

    // Return long algebraic notation
    string LAN() const { return isbad() ? "0000" : tile_name(from) + tile_name(to); }

};


// cce::Engine - Chess engine implementation
//
//
struct Engine {

    // Lock required to read/write variables on this engine
    mutex lock;

    // Computing thread which runs the number crunching
    thread thd_compute;

    // The current best move for the starting position
    // NOTE: Check 'isbad()' to see if it is uninitialized
    move best_move;

    // Current state the engine is analyzing
    State state;

    // Set the current state the engine should analyze
    void setstate(const State& state_);

    // Start computing the current position
    void go();

    // Stop computing the current position
    void stop();

};

```

Now, in `src/Engine.cc`, we need to implement the three functions:

```c++
void Engine::setstate(const State& state_) {
    lock.lock();

    state = state_;

    // Initialize to bad moves
    best_move = move();

    lock.unlock();
}

void Engine::go() {
    lock.lock();
    
    // TODO: Launch thread to do logic here

    lock.unlock();
}

void Engine::stop() {
    lock.lock();

    // TODO: Kill thread here
    
    // For now, just output 'e2e4'
    best_move = move(TILE(4, 1), TILE(4, 3));

    lock.unlock();
}
```

Let's hop back in `src/main.cc` and update our UCI interface:

```c++
// in 'src/main.cc'
// Accept UCI commands and feed them to 'eng'
static void do_uci(Engine& eng) {
    string line;
    vector<string> args;

    // send some information
    cout << "id name cce 0.1" << endl;
    cout << "id author Cade Brown" << endl;

    cout << "uciok" << endl;

    while (getline(cin, line)) {
        splitargs(line, args);
        if (args.size() == 0) continue;

        // Handle UCI command here
        if (args[0] == "debug") {
            if (args.size() == 2) {
                // Ignore for now, but in the future enable debugging
            } else {
                cerr << "Command 'debug' expected 2 arguments " << endl;
            }
        } else if (args[0] == "uci") {
            // Ignore, as we're always UCI
        } else if (args[0] == "quit") {
            // Quit the entire program
            return;
        } else if (args[0] == "isready") {
            // Just a check-up, always return 'readyok'
            cout << "readyok" << endl;
        } else if (args[0] == "setoption") {
            // Ignore for now
            // Sets an option in a dictionary
        } else if (args[0] == "register") {
            // Ignore for now
        } else if (args[0] == "ucinewgame") {
            // Ignore for now
        } else if (args[0] == "position") {
            if (args.size() < 2) {
                cerr << "Command 'position' expected 2 arguments or more" << endl;
            } else {
                string fen = "";
                if (args[1] == "startpos") {
                    // We need to start from initial position
                    fen = FEN_START;
                } else if (args[1] == "fen") {
                    if (args.size() < 3) {
                        cerr << "Command 'position fen' expected at least 3 arguments giving FEN string" << endl;
                    } else {
                        // Initialize from a FEN string (from remaining arguments)
                        for (int i = 2; i < args.size(); ++i) {
                            if (i > 2) fen.push_back(' ');
                            fen += args[i];
                        }
                    }
                } else {
                    cerr << "Command 'position' expected second argument to be 'startpos' or 'fen'" << endl;
                }
                if (fen.size() > 0) {
                    // Was successful, now set the engine to analyze this position
                    State s = State::from_FEN(fen);

                    // Set state for the engine
                    eng.setstate(s);
                }
            }

        } else if (args[0] == "go") {
            // Start computing
            eng.go();
            
            // TODO: We need to have it go until we've gone to the correct depth
            // For now, just stop the engine immediately and return e2e4
            eng.stop();

            // Print out best move (we need to lock it to avoid undefined behaviour)
            eng.lock.lock();
            cout << "bestmove " << eng.best_move.LAN() << endl;
            eng.lock.unlock();

        } else if (args[0] == "stop") {
            // Stop computing
            eng.stop();

            // Print out best move (we need to lock it to avoid undefined behaviour)
            eng.lock.lock();
            cout << "bestmove " << eng.best_move.LAN() << endl;
            eng.lock.unlock();

        } else {
            cerr << "Unknown command: '" << args[0] << "'" << endl;
        }
    }
}
```


Now, we can run and test:

```shell
$ ./cce
> uci
> position startpos
> go
bestmove e2e4
```

Right now, it is just hardcoded to output that move, but it does work as the UCI interface!

## Tester

To avoid manually entering `uci` and our commands, let's make a tester. We'll write it in Python, and call it `test/bestmove.py`. Its job will be to take a FEN record, and an engine, and print the best move the engine outputs:

```python
#!/usr/bin/env python3
""" test/bestmove.py - Tester to print the best move in a position

Examples:

$ test/bestmove.py test/startpos.fen

@author: Cade Brown <cade@cade.site>
"""

import os
import signal
import subprocess
import argparse
import time

parser = argparse.ArgumentParser(description='Find best move in a given position')

parser.add_argument('pos', help='Position or file to use')
parser.add_argument('--engine', default='./cce', help='Chess engine to use')
parser.add_argument('--time', default=1.0, type=float, help='Time to think')
parser.add_argument('--debug', action='store_true', help='Debug switch, which causes all output to be printed')

args = parser.parse_args()


# Get FEN string
fen = None
if args.pos.endswith('.fen'):
    # .fen file, read it in
    with open(args.pos) as fp:
        fen = fp.read()

else:
    # Assume it is FEN itself
    fen = args.pos

# Launch chess engine
proc = subprocess.Popen([args.engine], stdout=subprocess.PIPE, stdin=subprocess.PIPE, encoding='utf-8', bufsize=0)

# Run UCI command
def run(cmd):
    print('>', cmd)
    proc.stdin.write(cmd)
    proc.stdin.write('\n')


# Now, initialize the engine
run('uci')

# Set up a position
run('ucinewgame')
run('position fen ' + fen)

# Let the engine think
run('go')
time.sleep(args.time)
run('stop')

# Iterate over output
for line in proc.stdout:
    line = line.replace('\n', '')
    
    # Print all output in debug mode
    if args.debug:
        print(line)

    # Check for the 'bestmove' output
    if line.startswith('bestmove'):
        # If given, print the best move (in long algebraic notation)
        print ('best:', line.split(' ')[1])
        break

os.kill(proc.pid, signal.SIGTERM)
```


We can test it with `stockfish` (you will have to install it). For example:

```shell
$ ./test/bestmove.py test/startpos.fen --engine stockfish
> uci
> ucinewgame
> position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
> go
> stop
best: e2e4
```
(note: You may get different results for different `--time` options and there is some randomness involved, due to different speeds and versions of stockfish)

Here's what stockfish thinks of the sicilian given 30 seconds:


```shell
$ ./test/bestmove.py test/siciliandefense.fen --engine stockfish --time 30
> uci
> ucinewgame
> position fen rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6 0 2
> go
> stop
best: g1f3
```

Our example runs:

```shell
./test/bestmove.py test/startpos.fen --engine ./cce 
> uci
> ucinewgame
> position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
> go
> stop
best: e2e4
```

Of course, this is still pre-programmed, but we show that we can use it like stockfish already!

## GUI

Here's a list of popular UCI-compatible chess GUIs: [https://www.chessprogramming.org/UCI#GUIs](https://www.chessprogramming.org/UCI#GUIs). Make sure to pick one that works on your operating system. I'll be using [SCID](http://scid.sourceforge.net/), which supports arbitrary UCI programs

You should be able to google "how to add engine to <program>", and find out. For example, I added it to SCID, and now if I rotate the board and click `Play -> Serious Game`, it performs the first move:

![assets/img/chess-g0.jpg](assets/img/chess-g0.jpg)

After this part, you should have a UCI-compatible chess interface that always plays `e4`. If you try and play any other move, however, the program will not output another move, since `e4` is no longer a valid move. We'll fix that next time, when we look at move generation.

