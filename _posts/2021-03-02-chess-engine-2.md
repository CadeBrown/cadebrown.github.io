---
layout: post
title: "Chess Engine (#2) - Move Generation"
categories: [chess]
tags: [cce, chess]
series: cce
thumb: assets/img/chess-g1.jpg
---

In this part of the series, we will focus on [move generation](https://www.chessprogramming.org/Move_Generation), which will be neccessary to create a *correct* chess player.

<!--more-->

## Pieces

I will assume you are familiar with the basics of chess (if not, you probably wouldn't have made it this far). So, I'm not going to explain how all the pieces move in depth.

## Legal Moves

Legal moves are somewhat difficult to generate, due to [(absolute) pins](https://en.wikipedia.org/wiki/Pin_(chess)#Absolute_pin) and [en passant](https://en.wikipedia.org/wiki/En_passant). There are two main methods to generating moves:

  * Generate all psuedo-legal moves (i.e. squares pieces could normally travel to), and then double-check that none of them leave the king in check. Throw out those that do leave the king in check
  * Generate only the moves that are legal to begin with. Pins must be calculated, including en-passant

In general, the former method is easier to code, and even more resilient to bugs, but the second can be theoretically faster. We will abstract them as the `cce::State::getmoves` function, so we can replace that function later with a faster implementation. For now, we will write a psuedo-legal move generator, and then check whether the move was really legal.


Let's first update the `cce::State` structure and add some utilities, so that we can apply a move to it, and then perform checks to see if a square is attacked, or if a king is in check. We will also check game-ending conditions (like checkmate, stalemate, etc):

```c++
// in 'include/cce.hh'

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
                c = (color & m) ? Color::BLACK : Color::WHITE;
                p = Piece(i);
                return true;
            }
        }
        // Not found
        return false;
    }

    // Apply a move to a state
    void apply(const move& mv) {
        // Get masks
        bb mf = ONEHOT(mv.from), mt = ONEHOT(mv.to);
        Color other = tomove == Color::WHITE ? Color::BLACK : Color::WHITE;

        int p;
        for (p = 0; p < N_PIECES; ++p) {
            if (piece[p] & mf) {
                // Found piece moving from
                break;
            }
        }
        // Assert we found a piece from the place that is moving!
        assert(p < N_PIECES);

        // Remove where it was moving from
        color[tomove] &= ~mf;
        color[other] &= ~mf;

        // Now, add it where it is moving to, and clear opposite color tile if it was present
        color[tomove] |= mt;
        color[other] &= ~mt;

        // Remove piece where it was moving from
        piece[p] &= ~mf;
        // Add it back where it is moving to
        piece[p] |= mt;

        // Handle castling
        if (tomove == Color::WHITE) {
            if (mv.from == TILE(4, 0)) {
                if (mv.to == TILE(6, 0) && c_WK) {
                    // White kingside
                    bb rf = ONEHOT(TILE(7, 0));
                    bb rt = ONEHOT(TILE(5, 0));
                    color[Color::WHITE] &= ~rf;
                    color[Color::WHITE] |= rt;
                    piece[Piece::R] &= ~rf;
                    piece[Piece::R] |= rt;
                } else if (mv.to == TILE(2, 0) && c_WQ) {
                    // White queenside
                    bb rf = ONEHOT(TILE(0, 0));
                    bb rt = ONEHOT(TILE(3, 0));
                    color[Color::WHITE] &= ~rf;
                    color[Color::WHITE] |= rt;
                    piece[Piece::R] &= ~rf;
                    piece[Piece::R] |= rt;
                }
                c_WK = c_WQ = false;
            }
            if (mv.from == TILE(0, 0)) {
                c_WQ = false;
            } else if (mv.from == TILE(0, 7)) {
                c_WK = false;
            }
        } else {
            if (mv.from == TILE(4, 7)) {
                if (mv.to == TILE(6, 7) && c_BK) {
                    // Black kingside
                    bb rf = ONEHOT(TILE(7, 7));
                    bb rt = ONEHOT(TILE(5, 7));
                    color[Color::WHITE] &= ~rf;
                    color[Color::WHITE] |= rt;
                    piece[Piece::R] &= ~rf;
                    piece[Piece::R] |= rt;
                    c_WK = false;
                } else if (mv.to == TILE(2, 7) && c_BQ) {
                    // Black queenside
                    bb rf = ONEHOT(TILE(0, 7));
                    bb rt = ONEHOT(TILE(3, 7));
                    color[Color::WHITE] &= ~rf;
                    color[Color::WHITE] |= rt;
                    piece[Piece::R] &= ~rf;
                    piece[Piece::R] |= rt;
                }

                c_BK = c_BQ = false;
            }

            if (mv.from == TILE(7, 0)) {
                c_BQ = false;
            } else if (mv.from == TILE(7, 7)) {
                c_BK = false;
            }
        }

        
        // TODO: Handle en passant
        ep = -1;

        // Increment half move clock (TODO: check if it should be reset)
        hmclock++;

        // Now, increment state variables
        if (tomove == Color::WHITE) {
            // White
            tomove = Color::BLACK;
        } else {
            // Black
            fullmove++;
            tomove = Color::WHITE;
        }
    }

    // Returns whether the tile 'tile' is being attacked by the color about to move
    bool is_attacked(int tile) const;

    // Calculates whether the state represents a finished game, either by stalemate or checkmate (or draw
    //   due to repetition)
    // Stores status the winner, +1==white, 0==draw, -1==black
    bool is_done(int& status) const;

};


// Compute a list of the tiles in a bitboard, returning the number, and storing in 'pos'
// NOTE: 'pos' should be able to hold '64' integers
int bbtiles(bb v, int pos[64]);

```

Our implementation for `bbtiles` in `util.cc` is simple right now:

```c++
int bbtiles(bb v, int pos[64]) {
    if (!v) return 0;

    int r = 0;
    // TODO: Use some primitives. For now, we can try this
    bb m = 1, i = 0;
    while (m) {
        if (m & v) {
            pos[r++] = i;
        }

        i++;

        // Move bit up one
        m <<= 1;
    }

    return r;
}
```

There are some intrinsic functions that could speed this up, but for now we will use this implementation.

Back in `src/State.cc`, let's actually generate some moves:

```c++

// Internal method to determine whether `mv` is a valid move
bool isvalid(const State& s, const move& mv, bool ignorepins) {
    if (mv.isbad()) {
        // Out of range moves are never good
        return false;
    }

    bb mf = ONEHOT(mv.from), mt = ONEHOT(mv.to);
    bool issame = (s.color[s.tomove] & mf) != 0 && (s.color[s.tomove] & mt) != 0;
    if (issame) {
        // Can't move where your piece is
        return false;
    }

    // At this point, just return early
    if (ignorepins) return true; 

    // Create a new state
    State ns = s;

    // Apply move
    ns.apply(mv);
    assert(ns.tomove != s.tomove);

    // Get king position and see if it is attacked

    // Positions of various pieces
    int ntiles;
    int tiles[64];

    /* Generate king */
    ntiles = bbtiles(ns.piece[Piece::K] & ns.color[s.tomove], tiles);
    assert(ntiles == 1); // Must have exactly 1 king!

    // Now, switch back
    if (ns.is_attacked(tiles[0])) {
        // King cannot be attacked!
        return false;
    }

    // Now, determine if it was valid
    return true;
}

bool State::is_done(int& status) const {
    vector<move> moves;
    getmoves(moves);
    if (moves.size() == 0) {

        // Get king's position
        int ntiles;
        int tiles[64];
        ntiles = bbtiles(piece[Piece::K] & color[tomove], tiles);
        assert(ntiles == 1); // Must have exactly 1 king!


        // Check state from opposite perspective
        State ns = *this;
        ns.tomove = tomove == Color::WHITE ? Color::BLACK : Color::WHITE;

        if (ns.is_attacked(tiles[0])) {
            // Checkmate, the king is attacked and there are no legal moves
            status = tomove == Color::WHITE ? -1 : +1;
            return true;
        } else {
            // Stalemate, the king is not attacked and there are no legal moves
            status = 0;
            return true;
        }
    } else {

        // Game is not over, there are still legal moves
        status = 0;
        return false;
    }

}

bool State::is_attacked(int tile) const {

    // Super inefficient! But more correct... We can speed it up later
    vector<move> moves;
    getmoves(moves, true, true);

    int i;
    for (i = 0; i < moves.size(); ++i) {
        if (moves[i].to == tile) return true;
    }

    return false;
}

void State::getmoves(vector<move>& res, bool ignorepins, bool ignorecastling) const {
    res.clear();

    // Positions of various pieces
    int ntiles;
    int tiles[64];

    // Get the color mask to modify pieces with
    bb cmask = color[tomove], omask = color[tomove == Color::WHITE ? Color::BLACK : Color::WHITE];

    // Try and add '_mv', by checking if it is legal
    #define TRYADD(...) do { \
        move mv_ = __VA_ARGS__; \
        if (isvalid(*this, mv_, ignorepins)) { \
            res.push_back(mv_); \
        } \
    } while (0)

    int from;
    int i, j;
    bb m;

    /* Generate king moves */
    ntiles = bbtiles(piece[Piece::K] & cmask, tiles);
    assert(ntiles == 1); // Must have exactly 1 king!

    int kingpos = from = tiles[0];
    UNTILE(i, j, from);
    
    if (i >= 1 && j >= 1) TRYADD({from, TILE(i-1, j-1)});
    if (i >= 1) TRYADD({from, TILE(i-1, j)});
    if (i >= 1 && j <= 6) TRYADD({from, TILE(i-1, j+1)});
    
    if (j >= 1) TRYADD({from, TILE(i, j-1)});
    if (j <= 6) TRYADD({from, TILE(i, j+1)});
    
    if (i <= 6 && j >= 1) TRYADD({from, TILE(i+1, j-1)});
    if (i <= 6) TRYADD({from, TILE(i+1, j)});
    if (i <= 6 && j <= 6)TRYADD({from, TILE(i+1, j+1)});

    /* Generate queen moves */

    /* Generate bishop moves */

    /* Generate knight moves */
    ntiles = bbtiles(piece[Piece::N] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        // Consider all tiles (+-1, +-2) and (+-2, +-1) away, if they are in range
        if (i <= 6 && j <= 5) TRYADD({from, TILE(i+1, j+2)});
        if (i >= 1 && j <= 5) TRYADD({from, TILE(i-1, j+2)});
        if (i <= 6 && j >= 2) TRYADD({from, TILE(i+1, j-2)});
        if (i >= 1 && j >= 2) TRYADD({from, TILE(i-1, j-2)});

        if (i <= 5 && j <= 6) TRYADD({from, TILE(i+2, j+1)});
        if (i >= 2 && j <= 6) TRYADD({from, TILE(i-2, j+1)});
        if (i <= 5 && j >= 1) TRYADD({from, TILE(i+2, j-1)});
        if (i >= 2 && j >= 1) TRYADD({from, TILE(i-2, j-1)});
    }

    /* Generate rook moves */

    /* Generate pawn moves */
    ntiles = bbtiles(piece[Piece::P] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        if (tomove == Color::WHITE) {
            // White pawns move up
            if (j == 1) {
                // Can move 2 tiles
                TRYADD({from, TILE(i, j+2)});
            }
            TRYADD({from, TILE(i, j+1)});
        } else {
            // Black pawns move down
            if (j == 6) {
                // Can move 2 tiles
                TRYADD({from, TILE(i, j-2)});
            }
            TRYADD({from, TILE(i, j-1)});
        }
    }
}


```

Right now, we only have king, knight, and pawn moves programmed. We just want to be able to test whether it works. So, in `src/Engine.cc`, let's generate all the moves for the position, and say that the "best" move is a random one. We will have a random player who only knows how to move his king, knights, and pawns:

```c++

void Engine::go() {
    lock.lock();
    
    // TODO: Launch thread to do logic here

    vector<move> moves;
    state.getmoves(moves);

    // Pick random move
    best_move = moves[rand() % moves.size()];

    lock.unlock();
}

void Engine::stop() {
    lock.lock();

    // TODO: Kill thread here
    
    // For now, just output 'e2e4'
    //best_move = move(TILE(4, 1), TILE(4, 3));

    lock.unlock();
}

```

Loading back up in SCID, we can see how it plays (don't judge my chess playing):

![assets/img/chess-game0.gif](assets/img/chess-game0.gif)


Now, let's generate rook and bishop moves. The basic strategy is to iterate over rows and columns (or diagonals) until we hit something else, or hit the end of the board:


```c++
    /* Generate rook moves */
    ntiles = bbtiles(piece[Piece::R] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        // Add [*, j]
        for (int ti = i-1; ti >= 0; --ti) {
            to = TILE(ti, j);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        for (int ti = i+1; ti < 8; ++ti) {
            to = TILE(ti, j);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }

        // Add [i, *]
        for (int tj = j-1; tj >=0; --tj) {
            to = TILE(i, tj);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        for (int tj = j+1; tj < 8; ++tj) {
            to = TILE(i, tj);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
    }


    /* Generate bishop moves */
    ntiles = bbtiles(piece[Piece::B] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        // Add [i+n, j+n]
        for (int n = 1; i + n < 8 && j + n < 8; ++n) {
            to = TILE(i+n, j+n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i+n, j-n]
        for (int n = 1; i + n < 8 && j - n >= 0; ++n) {
            to = TILE(i+n, j-n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i-n, j+n]
        for (int n = 1; i - n >= 0 && j + n < 8; ++n) {
            to = TILE(i-n, j+n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i-n, j-n]
        for (int n = 1; i - n >= 0 && j - n >= 0; ++n) {
            to = TILE(i-n, j-n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
    }

```

And now, Queen moves are just a combination of rook and bishop moves:

```c++

    /* Generate queen moves */
    ntiles = bbtiles(piece[Piece::Q] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        // Add [i+n, j+n]
        for (int n = 1; i + n < 8 && j + n < 8; ++n) {
            to = TILE(i+n, j+n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i+n, j-n]
        for (int n = 1; i + n < 8 && j - n >= 0; ++n) {
            to = TILE(i+n, j-n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i-n, j+n]
        for (int n = 1; i - n >= 0 && j + n < 8; ++n) {
            to = TILE(i-n, j+n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        // Add [i-n, j-n]
        for (int n = 1; i - n >= 0 && j - n >= 0; ++n) {
            to = TILE(i-n, j-n);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }


        // Add [*, j]
        for (int ti = i-1; ti >= 0; --ti) {
            to = TILE(ti, j);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        for (int ti = i+1; ti < 8; ++ti) {
            to = TILE(ti, j);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }

        // Add [i, *]
        for (int tj = j-1; tj >=0; --tj) {
            to = TILE(i, tj);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
        for (int tj = j+1; tj < 8; ++tj) {
            to = TILE(i, tj);
            m = ONEHOT(to);
            if (cmask & m) {
                // Can't do our own pieces
                break;
            } else if (omask & m) {
                // Can capture, but go no further
                TRYADD({from, to});
                break;
            }
            TRYADD({from, to});
        }
    }

```

In the future, we will generate tables to make this process much faster.

Finally, let's fix pawn moves to include capturing (and en passant):

```c++


    /* Generate pawn moves */
    ntiles = bbtiles(piece[Piece::P] & cmask, tiles);
    for (int k = 0; k < ntiles; ++k) {
        from = tiles[k];
        UNTILE(i, j, from);

        if (tomove == Color::WHITE) {
            // White pawns move up
            if (j == 1) {
                // Can move 2 tiles
                TRYADD({from, TILE(i, j+2)});
            }
            TRYADD({from, TILE(i, j+1)});

            // Handle diagonal captures
            if (j <= 6) {
                if (i <= 6) {
                    to = TILE(i+1, j+1);
                    m = ONEHOT(to);
                    // Handle en-passant capture as well, with 'ep==to'
                    if ((omask & m) || ep == to) {
                        TRYADD({from, to});
                    }
                }
                if (i >= 1) {
                    to = TILE(i-1, j+1);
                    m = ONEHOT(to);
                    if ((omask & m) || ep == to) {
                        TRYADD({from, to});
                    }
                }
            }

        } else {
            // Black pawns move down
            if (j == 6) {
                // Can move 2 tiles
                TRYADD({from, TILE(i, j-2)});
            }
            TRYADD({from, TILE(i, j-1)});

            // Handle diagonal captures
            if (j >= 1) {
                if (i <= 6) {
                    to = TILE(i+1, j-1);
                    m = ONEHOT(to);
                    if ((omask & m) || ep == to) {
                        TRYADD({from, to});
                    }
                }
                if (i >= 1) {
                    to = TILE(i-1, j-1);
                    m = ONEHOT(to);
                    if ((omask & m) || ep == to) {
                        TRYADD({from, to});
                    }
                }
            }
        }
```

For now, we will always assume pawns promote to queen, so we won't worry about that. We will modify the `move` structure in the future when we run into this problem.


Now, the only thing we don't have is castling, so let's add that too:


```c++

    /* Generate castling moves */
    if (!ignorecastling) {
            
        if (tomove == Color::WHITE && (c_WK || c_WQ)) {

            // White can castle either king or queen or both
            // First, let's calculate moves that black has to see if they are attacking the squares we are going through
            // We do this by duplicating the state but chaning the 'tomove' color
            State ts = *this;
            ts.tomove = Color::BLACK;
            vector<move> bmv;
            ts.getmoves(bmv, true, true);


            if (c_WK) {
                // Three tiles that must be passed through not in check
                int t0 = TILE(4, 0), t1 = TILE(5, 0), t2 = TILE(6, 0);

                if ((ONEHOT(t0) | ONEHOT(t1) | ONEHOT(t2)) & (omask | cmask)) {
                    // Can't castle, people in the way
                } else {
                    bool good = true;
                    for (int k = 0; k < bmv.size(); ++k) {
                        int dest = bmv[k].to;
                        if (dest == t0 || dest == t1 || dest == t2) {
                            good = false;
                            break;
                        }
                    }

                    if (good) {
                        // Just add, since we already checked whether we were attacked
                        res.push_back({ TILE(4, 0), TILE(6, 0) });
                    }

                }
            }

            if (c_WQ) {
                // Three tiles that must be passed through not in check
                int t0 = TILE(4, 0), t1 = TILE(3, 0), t2 = TILE(2, 0);
                if ((ONEHOT(t0) | ONEHOT(t1) | ONEHOT(t2)) & (omask | cmask)) {
                    // Can't castle, people in the way
                } else {
                    bool good = true;
                    for (int k = 0; k < bmv.size(); ++k) {
                        int dest = bmv[k].to;
                        if (dest == t0 || dest == t1 || dest == t2) {
                            good = false;
                            break;
                        }
                    }

                    if (good) {
                        // Just add, since we already checked whether we were attacked
                        res.push_back({ TILE(4, 0), TILE(2, 0) });
                    }
                }
            }
        } else if (tomove == Color::BLACK && (c_BK || c_WQ)) {

            // Black can castle either king or queen or both
            // First, let's calculate moves that white has to see if they are attacking the squares we are going through
            // We do this by duplicating the state but chaning the 'tomove' color
            State ts = *this;
            ts.tomove = Color::WHITE;
            vector<move> bmv;
            ts.getmoves(bmv, true, true);

            if (c_BK) {
                // Three tiles that must be passed through not in check
                int t0 = TILE(4, 7), t1 = TILE(5, 7), t2 = TILE(6, 7);
                if ((ONEHOT(t0) | ONEHOT(t1) | ONEHOT(t2)) & (omask | cmask)) {
                    // Can't castle, people in the way
                } else {
                    bool good = true;
                    for (int k = 0; k < bmv.size(); ++k) {
                        int dest = bmv[k].to;
                        if (dest == t0 || dest == t1 || dest == t2) {
                            good = false;
                            break;
                        }
                    }

                    if (good) {
                        // Just add, since we already checked whether we were attacked
                        res.push_back({ TILE(4, 7), TILE(6, 7) });
                    }
                }
            }
            if (c_BQ) {
                // Three tiles that must be passed through not in check
                int t0 = TILE(4, 7), t1 = TILE(3, 7), t2 = TILE(2, 7);
                if ((ONEHOT(t0) | ONEHOT(t1) | ONEHOT(t2)) & (omask | cmask)) {
                    // Can't castle, people in the way
                } else {
                    bool good = true;
                    for (int k = 0; k < bmv.size(); ++k) {
                        int dest = bmv[k].to;
                        if (dest == t0 || dest == t1 || dest == t2) {
                            good = false;
                            break;
                        }
                    }

                    if (good) {
                        // Just add, since we already checked whether we were attacked
                        res.push_back({ TILE(4, 7), TILE(2, 7) });
                    }
                }
            }
        }

```

And if we load it up in SCID, we can see it plays all these amazing moves:

![assets/img/chess-g1.jpg](assets/img/chess-g1.jpg)

(in case you don't get the joke, this is called [fool's mate](https://en.wikipedia.org/wiki/Fool%27s_mate), which is the fastest check mate possible)


Clearly, our bot needs some work! In the next part, we'll actually start evaluating positions, and then making decisions based on that (so we don't get such awful moves)

