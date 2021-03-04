---
layout: post
title: "Chess Engine (#3) - Position Evaluation"
categories: [chess]
tags: [cce, chess]
series: cce
thumb: assets/img/chess-g1.jpg
---

In this part of the series, we will focus on [position evaluation](https://www.chessprogramming.org/Evaluation), which is a hueristic about how "good" or "bad" a position looks for white or black.

<!--more-->

What exactly is an evaluation? Well, it should behave like a number that tells us the relative strength of each side. For consistency, we will define this measurement as the number of pawns that white is ahead. We will add more measurements in the future to get a more exact metric that more accurately shows the relative strength of a position

Let's start by defining a structure that will work as an evaluation. We could use a `float` or `double`, but there is a slight complication: We want to be able to distinguish between forced checkmate (i.e. one side can checkmate the other side in `N` moves no matter what the defense is). And, we want to be able to score faster forced checkmates before longer ones. This will make more sense when we start searching for good moves -- the "best" moves in a position are those that bring checkmate the quickest, so we need to be able to distinguish between different length forced checkmates.

In our main header, let's define `struct eval` to be an evaluation score for a board:

```c++
// in 'cce.h'

// Other standard libraries we need
#include <cmath>

// cce::eval - Chess position evaluation
//
//
struct eval {

    // Score, in pawns, for white
    //   if > 0, then position is better for white
    //   if < 0, then position is better for black
    // If 'score==INFINITY' or 'score==-INFINITY', there is a forced checkmate in 'matein' moves
    float score;

    // Number of moves until checkmate (assuming best play)
    // Only used if 'score == INFINITY' (checkmate for white) or 'score == -INFINITY' (checkmate for black)
    int matein;

    // Contructor
    eval(float score_=0.0f, int matein_=-1) : score(score_), matein(matein_) {}

    // Return a forced draw
    static eval draw() {
        return eval(NAN);
    }

    // Returns whether the evaluation is a forced draw
    bool isdraw() const { return isnan(score); }

    // Returns whether the evaluation is a forced checkmate
    bool ismate() const { return isinf(score); }

    // Return evaluation as a string
    string getstr() const {
        if (isdraw()) {
            return "DRAW";
        } else if (ismate()) {
            if (score >= 0) {
                // + for white
                return "M+" + to_string(matein);
            } else {
                // - for black
                return "M-" + to_string(matein);
            }
        } else {
            // Use snprintf so we can specify that only 2 decimal digits should be printed
            char tmp[64];
            snprintf(tmp, sizeof(tmp) - 1, "%+.2f", score);
            return (string)tmp;
        }
    }

    // Comparator
    //   if > 0, then b is better for white than a
    //   if = 0, then a is the same as b
    //   if < 0, then b is worse for white than a
    static int cmp(const eval& a, const eval& b) {
        if (a.score > b.score) {
            return +1;
        } else if (a.score < b.score) {
            return -1;
        } else {
            if (a.ismate() && b.ismate()) {
                
                if (a.score > 0) {
                    // The checkmate is for white
                    // Choose faster checkmate
                    if (a.matein < b.matein) {
                        return +1;
                    } else {
                        return -1;
                    }
                } else {
                    // The checkmate is for black
                    // Choose slower checkmate
                    if (a.matein > b.matein) {
                        return +1;
                    } else {
                        return -1;
                    }
                }
            } else {
                // Draw
                return 0;
            }
        }
    }
};


```

The comparator (`cce::eval::cmp`) may seem odd, but it allows us to compare evaluations instead of defining a `<`, `<=`, `>`, `>=`, `==`, and `!=` operators seperately. So, to compare two evaluations, we can use `eval::cmp(a, b) < 0`, `eval::cmp(a, b) <= 0`, and so forth. It is basically the [spaceship operator](https://en.cppreference.com/w/cpp/language/default_comparisons).

There's also a string conversion which will be good for debugging.

Let's go ahead and add a function to our engine:

```c++

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


};

```


And here's our implementation:


```c++

// Scores for each piece
#define SCORE_Q (9.0)
#define SCORE_B (3.25)
#define SCORE_N (3.0)
#define SCORE_R (5.0)
#define SCORE_P (1.0)

// Calculate a score for a particular color
static float my_score(const Engine& eng, const State& s, Color c) {
    // Positions of each piece
    int ntiles;
    int tiles[64];

    // Total material score for this color
    float mat = 0.0f;

    ntiles = bbtiles(s.color[c] & s.piece[Piece::Q], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_Q;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::B], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_B;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::N], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_N;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::R], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_R;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::P], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_P;
    }

    return mat;
}

eval Engine::eval_static(const State& s) {

    // Calculate score for each side
    float sW = my_score(*this, s, Color::WHITE), sB = my_score(*this, s, Color::BLACK);

    // Return the difference of the scores, so >0 means white is winning
    return eval(sW - sB);
}

```

As you can see, we define some constants which are the scores for various pieces (these are fairly standard, but feel free to make your own and see how it goes!). Now, let's test it out with a few positions:


```c++

    // Create engine
    Engine eng;

    // Starting position
    State s = State::from_FEN("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    // Score: +0.00
    cout << "Score: " << eng.eval_static(s).getstr() << endl;


    // Starting position, without black's queen
    State s = State::from_FEN("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
    // Score: +9.00
    cout << "Score: " << eng.eval_static(s).getstr() << endl;

    // Starting position, without white's queen
    State s = State::from_FEN("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1");
    // Score: -9.00
    cout << "Score: " << eng.eval_static(s).getstr() << endl;

```

So, it does seem to be working. However, let's try adding in some more hueristics, including adding scores for castling rights, and detecting checkmate:

```c++

// Scores for each piece
#define SCORE_Q (9.0)
#define SCORE_B (3.25)
#define SCORE_N (3.0)
#define SCORE_R (5.0)
#define SCORE_P (1.0)


// Scores for castling rights
#define SCORE_CK (0.8)
#define SCORE_CQ (0.5)


// Calculate a score for a particular color
static float my_score(const Engine& eng, const State& s, Color c) {
    // Positions of each piece
    int ntiles;
    int tiles[64];

    // Total material score for this color
    float mat = 0.0f;

    ntiles = bbtiles(s.color[c] & s.piece[Piece::Q], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_Q;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::B], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_B;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::N], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_N;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::R], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_R;
    }

    ntiles = bbtiles(s.color[c] & s.piece[Piece::P], tiles);
    for (int i = 0; i < ntiles; ++i) {
        mat += SCORE_P;
    }

    // Castling rights
    if (c == Color::WHITE) {
        if (s.c_WK) mat += SCORE_CK;
        if (s.c_WQ) mat += SCORE_CQ;
    } else {
        if (s.c_BK) mat += SCORE_CK;
        if (s.c_BQ) mat += SCORE_CQ;
    }

    return mat;
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

And, let's just check its evaluation of fool's mate:

![assets/img/chess-g2.jpg](assets/img/chess-g3.jpg)

```c++
    // Fool's mate
    State s = State::from_FEN("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3");
    // Score: M-0
    cout << "Score: " << eng.eval_static(s).getstr() << endl;
```



## Static Evaluation

To truly know the evaluation of a position, we would need to play out all possible moves to see if either side can force a win, or a draw. However, this is impossible as chess is too vast a game. Instead, let's just write a simple function to evaluate a static position based on how good it seems to be, making basic measurements about a gamestate.

The main problem with this is that it cannot see specific tactics that make a certain position bad.

For example, consider this position (from [Legal's Trap](https://en.wikipedia.org/wiki/L%C3%A9gal_Trap)):

![assets/img/chess-g2.jpg](assets/img/chess-g2.jpg)


If you merely count the number of pieces, it would seem that black is up a queen in exchange for a single pawn. However, white has a forced checkmate in 2 moves (`Bxf7+ Ke7 Nd5#`). So, obviously, the position is actually winning for white! Our simple metric of counting material on the board won't work. But, we also can't check for all forced checkmates for an evaluation function. 

So what's the solution? We will need to search through a tree of possible moves and responses, and see which is the best for each player. Then, we find the static evaluation of the final position, and back propogate to find the best. This way, we will find forced checkmate in 0, then forced checkmate in 1, and finally forced checkmate in 2, which is the correct evaluation for this position.

We can get better moves by using deeper searches. But, that will have to wait for next time!

