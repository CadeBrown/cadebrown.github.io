---
layout: post
title: "Chess Engine (#4) - Searching for the best move"
categories: [chess]
tags: [cce, chess]
series: cce
thumb: assets/img/chess-g1.jpg
---

The time has come to make a formidable opponent! And the only way to do that is to make our opponent smarter. How do we do that? We search for the best move, and then play that move!

Easier said than done...


<!--more-->

## Methods

There are [tons of methods](https://www.chessprogramming.org/Search) for searching for good moves. So, this series is going to cover a few of them.

We're going to start simple, and expand from there. We'll go back and forth from our searching functionality, back to our evaluation function specified earlier in the series (we'll need more complicated evaluation functions to truly tell the best position, and thus, the best move). For now, we'll keep our current evaluation function to get started



## 0. Win Material with depth==1

Our first algorithm will simply generate all legal moves, play them out, and choose the one that gives us the best advantage (in terms of our evaluation function). We'll call this method `cce::Engine::findbest1`, and we won't use any multithreading yet (we're keeping it simple!)

Let's add it in `cce.h`:


```c++
// Needed header
#include <algorithm>

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

    // The evaluation for 'best_move'
    eval best_ev;

    // Current state the engine is analyzing
    State state;

    // Set the current state the engine should analyze
    void setstate(const State& state_);

    // Start computing the current position
    void go();

    // Stop computing the current position
    void stop();


    // Static evaluation method, which does not recurse or check move combinations
    eval eval_static(const State& s);

    // Find the best move, by using the evaluation function with a single move depth
    pair<move, eval> findbest1(const State& s);

};

```

And here's the implementation:

```c++
pair<move, eval> Engine::findbest1(const State& s) {
    // Find legal moves
    vector<move> moves;
    s.getmoves(moves);
    // Return NULL move
    if (moves.size() == 0) return {move(), eval()};

    // Best index
    int bi = -1;
    eval be = eval();
    for (int i = 0; i < moves.size(); ++i) {
        // Try applying the move
        State ns = s;
        ns.apply(moves[i]);
        eval ev = eval_static(ns);
        if (bi < 0) {
            bi = i;
            be = ev;
        } else if (s.tomove == Color::WHITE) {
            if (eval::cmp(ev, be) > 0) {
                bi = i;
                be = ev;
            }
        } else if (s.tomove == Color::BLACK) {
            if (eval::cmp(ev, be) < 0) {
                bi = i;
                be = ev;
            }
        }
    }

    return {moves[bi], be};
}

```

So, this bot will favor material and castling rights, and only look one move ahead. If we play it we get an interesting bot that will take anything it can get. Before we do that we need to hook it up in `Engine.cc`:

```c++

void Engine::go() {
    lock.lock();
    
    // TODO: Launch thread to do logic here
//    cout << "info depth 1 seldepth 1 multipv 1 score cp 114 nodes 20 nps 20000 tbhits 0 time 1 pv e2e3" << endl;

    // Pick random move
    best_move = findbest1(state).first;

    //for (int i = 0; i < moves.size(); ++i) {
    //    cout << moves[i].LAN() << endl;
    //}

    lock.unlock();
}
```

Here's a game (I'm playing white, my bot is playing black):

![assets/img/chess-g6.gif](assets/img/chess-g6.gif)

Obviously, the bot is not great at all. It gives up its queen because it thinks it is winning a knight. But, since it is only looking one move ahead, it doesn't understand that the knight is defended, and since the queen is worth more than the knight, its a bad trade.

We're going to fix that with the [Minimax](https://en.wikipedia.org/wiki/Minimax) algorithm. Basically, we will view the tree of all possible moves, and choose the best move at each depth, showing "optimal" play. Eventually, we'll use our original best move finder as a basecase. The idea is that the deeper we go, the better our play will be. Keep in mind, however, that a good search also needs a good evaluation function. So, we'll need to improve that to see better play as well.

Keep in mind that this is a brute force approach, which checks every single move, and every response, and so on for a given depth. It will take extremely long, and will check even the worst moves all the way through. In the future, we will try and "prune" out bad moves early and spend less time. Additionally, we will eventually use multiple threads to speed up the process of checking most moves.


```c++
// in 'cce.hh'

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

    // The evaluation for 'best_move'
    eval best_ev;

    // Current state the engine is analyzing
    State state;

    // Set the current state the engine should analyze
    void setstate(const State& state_);

    // Start computing the current position
    void go();

    // Stop computing the current position
    void stop();


    // Static evaluation method, which does not recurse or check move combinations
    eval eval_static(const State& s);

    // Find the best move, by using the evaluation function with a single move depth
    pair<move, eval> findbest1(const State& s);

    // Find the best move with a given depth, brute force search
    pair<move, eval> findbestN(const State& s, int dep=1);

};

```

And, in `Engine.cc`:

```c++
void Engine::go() {
    lock.lock();
    
    // TODO: Launch thread to do logic here
//    cout << "info depth 1 seldepth 1 multipv 1 score cp 114 nodes 20 nps 20000 tbhits 0 time 1 pv e2e3" << endl;

    // Pick random move, with a depth of 2
    best_move = findbestN(state, 2).first;

    //for (int i = 0; i < moves.size(); ++i) {
    //    cout << moves[i].LAN() << endl;
    //}

    lock.unlock();
}

/// ...

pair<move, eval> Engine::findbestN(const State& s, int dep) {
    // Base case to end recursion
    if (dep <= 1) return findbest1(s);

    // Otherwise, let's search through all possible moves
    vector<move> moves;
    s.getmoves(moves);
    if (moves.size() == 0) {
        // Need to handle ended games
        int status;
        s.is_done(status);

        return pair<move, eval>(move(), eval(INFINITY * status, 0));
    }

    // Best index
    int bi = -1;
    eval be = eval();
    for (int i = 0; i < moves.size(); ++i) {
        State ns = s;
        ns.apply(moves[i]);

        // Find best move in new position
        pair<move, eval> bm = findbestN(ns, dep-1);
        if (bi < 0) {
            bi = i;
            be = bm.second;
        } else if (s.tomove == Color::WHITE) {
            if (eval::cmp(bm.second, be) > 0) {
                bi = i;
                be = bm.second;
            }
        } else if (s.tomove == Color::BLACK) {
            if (eval::cmp(bm.second, be) < 0) {
                bi = i;
                be = bm.second;
            }
        }
    }
    
    return {moves[bi], be};
}

```

Although this does work, it's very slow! On my machine, cce can play with a depth of 3, using 2 or 3 seconds per move, With a depth of 4, it takes about 30-45 seconds per move, and above that it takes at least 3 minutes per move. Eventually, it will take a minute or so per move, and this will be fine, but we would expect better play than we are getting now:


## Better Evaluation

The last thing we're going to do in this section is update our evaluation function to include positional awareness. What this means is that it won't only favor material, but also things like position of pieces, attackers and defenders, and checking the opponents king. It will also favor having more moves, and having the next move (i.e. having tempo). Let's update our static evaluation:

```c++


// Scores for each piece
#define SCORE_Q (9.0)
#define SCORE_B (3.15)
#define SCORE_N (3.0)
#define SCORE_R (5.0)
#define SCORE_P (1.0)


// Scores for castling rights
#define SCORE_CK (0.4)
#define SCORE_CQ (0.3)

// Score for having the next move
#define SCORE_TOMOVE (0.15)

// Score per available move
#define SCORE_PERMOVE (0.1)

// Score for checking the enemy king
#define SCORE_CHECK (0.5)

// Constant for having any piece in a position
#define ADD_INPOS (0.13)

// Multiplier for having a piece in a position
#define MULT_INPOS (0.03)


// Moving to a position multiplier
#define MULT_TOPOS (0.08)

// Database of center values
static float db_centerval[64] = {
     0.33, 0.40, 0.46, 0.49, 0.49, 0.46, 0.40, 0.33 ,
     0.40, 0.49, 0.59, 0.65, 0.65, 0.59, 0.49, 0.40 ,
     0.46, 0.59, 0.73, 0.83, 0.83, 0.73, 0.59, 0.46 ,
     0.49, 0.65, 0.83, 0.96, 0.96, 0.83, 0.65, 0.49 ,
     0.49, 0.65, 0.83, 0.96, 0.96, 0.83, 0.65, 0.49 ,
     0.46, 0.59, 0.73, 0.83, 0.83, 0.73, 0.59, 0.46 ,
     0.40, 0.49, 0.59, 0.65, 0.65, 0.59, 0.49, 0.40 ,
     0.33, 0.40, 0.46, 0.49, 0.49, 0.46, 0.40, 0.33 ,
};


// Attack and defense score for a list of moves
static float my_adscore(const Engine& eng, const State& s, const vector<move>& moves) {
    
    // Count number of legal moves to a given square
    int numto[64];
    for (int i = 0; i < 64; ++i) numto[i] = 0;

    float res = 0.0f;

    // Add up moves to the center (which is being able to "defend" that square)
    for (int i = 0; i < moves.size(); ++i) {
        // Compute extra score based on number of defenders
        // 0.3f is just a magic constant... expirement with this!
        float numbonus = numto[moves[i].to] * 0.3f;

        // Add the center value and the bonus
        res += MULT_TOPOS * db_centerval[moves[i].to] * (1 + numbonus);
        numto[moves[i].to]++;
    }

    // Also, bonus points of the enemy king is attacked
    Color other = s.tomove == Color::WHITE ? Color::BLACK : Color::WHITE;

    int ntiles;
    int tiles[64];
    ntiles = bbtiles(s.piece[Piece::K] & s.color[other], tiles);
    assert(ntiles == 1); // Must have one king!

    if (s.is_attacked(tiles[0])) {
        // Other king is attacked
        res += SCORE_CHECK;
    }

    return res;
}

// Calculate a score for a particular color
static float my_score(const Engine& eng, const State& s, Color c) {
    // Positions of each piece
    int ntiles;
    int tiles[64];

    // Total material score for this color
    float mat = 0.0f;

    // Attacking/defending score
    float ads = 0.0f;

    // Positional score
    float pos = 0.0f;

    ntiles = bbtiles(s.color[c] & s.piece[Piece::Q], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_Q;
        pos += (SCORE_Q * MULT_INPOS + ADD_INPOS) * db_centerval[tiles[i]];
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::B], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_B;
        pos += (SCORE_B * MULT_INPOS + ADD_INPOS) * db_centerval[tiles[i]];
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::N], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_N;
        pos += (SCORE_N * MULT_INPOS + ADD_INPOS) * db_centerval[tiles[i]];
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::R], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_R;
        pos += (SCORE_R * MULT_INPOS + ADD_INPOS) * db_centerval[tiles[i]];
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::P], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_P;
        pos += (SCORE_P * MULT_INPOS + ADD_INPOS) * db_centerval[tiles[i]];
    }

    // Castling rights
    if (c == Color::WHITE) {
        if (s.c_WK) mat += SCORE_CK;
        if (s.c_WQ) mat += SCORE_CQ;
    } else {
        if (s.c_BK) mat += SCORE_CK;
        if (s.c_BQ) mat += SCORE_CQ;
    }


    if (s.tomove == c) {
        vector<move> moves;
        s.getmoves(moves);

        pos += SCORE_PERMOVE * moves.size();

        // Compute attacking and defining score
        ads += my_adscore(eng, s, moves);

    } else {
        // Generate a list of moves if the tomove was different
        State ns = s;
        ns.tomove = c;

        vector<move> moves;
        ns.getmoves(moves);

        pos += SCORE_PERMOVE * moves.size();

        // Compute attacking and defining score
        ads += my_adscore(eng, ns, moves);
    }

    // Misc. score
    float misc = 0.0f;
    if (s.tomove == c) {
        misc += SCORE_TOMOVE;
    }

    // Sum all parts of the score
    return mat + pos + ads + misc;
}

eval Engine::eval_static(const State& s) {

    // Check if the game is over
    int status;
    if (s.is_done(status)) {
        if (status == 0) {
            // Draw
            return eval::draw();
        } else {
            // Checkmate (in zero)
            return eval(status * INFINITY, 0);
        }
    }

    // Calculate score for each side
    float sW = my_score(*this, s, Color::WHITE), sB = my_score(*this, s, Color::BLACK);

    // Return the difference of the scores, so >0 means white is winning
    return eval(sW - sB);
}

```

And, our chess engine is working! The main problem is the speed... It's not fast enough! Next time, we'll look at faster move generation, and be able to actually start having a "deep" engine


