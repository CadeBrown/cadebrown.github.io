---
layout: post
title: "Implementing {Zeta, Gamma} Functions From Scratch"
categories: [math]
tags: [math, kscript]
---

In developing [my language, kscript](https://github.com/chemicaldevelopment/kscript), I wanted to have the [Riemann Zeta Function](https://en.wikipedia.org/wiki/Riemann_zeta_function) and [Gamma Function](https://en.wikipedia.org/wiki/Gamma_function) available as part of the standard library. So, I implemented it!

We program a code generator in Python, which generates C code, which can then be used in another project with no dependencies.

<!--more-->

## Definitions

I'll assume you're more or less familiar with what the Zeta and Gamma functions are, but I'll also provide a definition we'll work with:

$$\Gamma(x) = (x - 1)! = \int_{0}^{\infty} t^{x-1} e^{-t} dt$$

$$\zeta(x) = \sum_{n=1}^{\infty} \frac{1}{n^x} $$


We use the following reflection formulas to define the value elsewhere: 

$$\zeta(x) = 2 (2 \pi) ^ {x - 1} \sin(\frac{x \pi}{2}) \Gamma(1 - x) \zeta(1 - x)$$

$$\Gamma(x) = \sin(\pi z) \Gamma(1 - x)$$


## Goal

Our goal is to define `C` functions with the following signatures, which evaluate the specific function at a particular point:

```c

double my_zeta(double x);
double complex my_czeta(double complex x);

double my_gamma(double x);
double complex my_cgamma(double complex x);

// equivalent to `log(gamma(x))`
double my_lgamma(double x);
double complex my_lcgamma(double complex x);

```

We would like this to be self contained, and distributable to any other C99 project. Further, the results should be accurate to the requested precision (`double` in C is typically IEEE 64 bit)

We include `lgamma` functions to compute the logarithm of the gamma function; we won't go into optimizing for this case too much, but I need this for kscript so we will also generate it (to generate it yourself, include `--lgamma` in your arguments to the script)

## Implementation

You can see the source code for this generator available online here: [https://gist.github.com/CadeBrown/f60d234cbfae1fc3cc1dcb114b93d538](https://gist.github.com/CadeBrown/f60d234cbfae1fc3cc1dcb114b93d538)

I used the paper referenced here: [http://numbers.computation.free.fr/Constants/Miscellaneous/zetaevaluations.pdf](http://numbers.computation.free.fr/Constants/Miscellaneous/zetaevaluations.pdf) to form the basis of my implementation for the Zeta function. Specifically, section `1.2` entitled `Convergence of alternating series method`. We'll also need an implementation of the Gamma Function, which I've linked papers to help us. Note that we can use C's `tgamma` function for real number computations, but we'll have to roll our own for complex numbers (we'll implement both, for completeness). I won't go into all of the derivations for all the formula (those are covered in the papers I linked if you're interested); I'll try and just breifly cover the motivation and basic algebra between formulas

References:

  * 0: [http://numbers.computation.free.fr/Constants/Miscellaneous/zetaevaluations.pdf](http://numbers.computation.free.fr/Constants/Miscellaneous/zetaevaluations.pdf)
  * 1: [https://en.wikipedia.org/wiki/Lanczos_approximation](https://en.wikipedia.org/wiki/Lanczos_approximation)
  * 2: [https://mrob.com/pub/ries/lanczos-gamma.html](https://mrob.com/pub/ries/lanczos-gamma.html)
  * 3: [https://web.viu.ca/pughg/phdThesis/phdThesis.pdf](https://web.viu.ca/pughg/phdThesis/phdThesis.pdf)
  * 4: [https://my.fit.edu/~gabdo/gamma.txt](https://my.fit.edu/~gabdo/gamma.txt)


We will dynamically generate C99 code that will be suitable to machine precision via a `Python` script, which will use the Python package `gmpy2` (`pip3 install gmpy2`)

We start by importing things, declaring an argument format, and having some built ins:

```python
# std library
import sys
import math
import argparse

# for cached functions (may help performance)
from functools import lru_cache

# gmpy2: multiprecision
import gmpy2
from gmpy2 import mpfr, const_pi, exp, sqrt, log, log10

# add commandline arguments
parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=40))

parser.add_argument('--prec', help='Internal precision to use in all computations (in bits)', default=1024, type=int)
parser.add_argument('--prefix', help='Prefix to the C style functions to generate (include the "_"!)', default="my_")
parser.add_argument('--lgamma', help='Whether or not to include an implementation of the `lgamma` function', action='store_true')

args = parser.parse_args()

# set precision to the requested one
gmpy2.get_context().precision = args.prec

# pi & e, but to full precision within gmpy2
pi = const_pi()
e = exp(1)

# factorial, product of all integers <= x
@lru_cache
def factorial(x):
    return math.factorial(x)

# double factorial, if n is even, product of all even numbers <= n, otherwise the product of all odd numbers <= n
@lru_cache
def double_factorial(n):
     if n <= 1:
         return 1
     else:
         return n * double_factorial(n - 2)

# n choose k, i.e. 
@lru_cache
def choose(n, k):
    if k < 0:
        return 0
    return math.comb(n, k)

# return the amount of digits that are accurate in a given error bound
# example: digits_accurate(.001) returns 3, since it is down to 3 places
def digits_accurate(x):
    return float(max([-log10(x), 0]))

```

These are all pretty self explanatory; especially with the comments. We use `@lru_cache` to cache results of functions to reduce overhead when repeatedly calling with the same arguments.

## Gamma Function

To create a table-based approximation (specifically, the [Lanczos Approximation](https://en.wikipedia.org/wiki/Lanczos_approximation)), we start with an observation that the Gamma function can be written as:

$$\Gamma(x+1) \approx \sqrt{2 \pi} (x+g+\frac{1}{2})^{x+\frac{1}{2}} e^{-(x+g+\frac{1}{2})} A_g(x)$$

where

$$A_g(x) = \frac{1}{2}p_0(g) + p_1(g)\frac{x}{x+1} + p_2(g)\frac{x(x-1)}{(x+1)(x+2)} + ...$$

where $g$ is a specifically chosen number to maximize accuracy, $n$ is the number of terms, and the $p_i$ are coefficients computed for the best fit

This works fine on paper, but when actually implementing the C code there is a number of problems:

  * The number of floating-point multiplies is $O(n^2)$ at run time (think about all the fractions in $A_g$), which will make it slower to execute, as well as introduce more error 
  * Those multiplications will result in fractions which have very different magnitudes; doing that and summing their results will make roundoff errors much more prevalent
  * More intermediate adds $x, x+1, x+2, ...$, means more register usage and for large tables, maybe even stack variables (that's really bad for performance!)


Wouldn't it be nice to re-arrange the $A_g$ function into something that looks like the following:

$$A_g'(x) = a_0 + \frac{a_1}{x+1} + \frac{a_2}{x+2} + ... \frac{a_{n-1}}{x+n-1}$$

Therefore minimizing and simplifying the resulting code? Yes it would! But how do we do that?

Well; we view the summation as a [Partial Fraction Summation](https://www.purplemath.com/modules/partfrac.htm); think of the following equation:

$ \frac{1}{x+1} + \frac{1}{x+2} = \frac{(x + 1) + (x + 2)}{(x+1)(x+2)} = \frac{2x+3}{(x+1)(x+2)}$

We can algebraically manipulate the rational expression to yield either a summation of divisions, or a division of products & sums. This is actually very similar to our above expression that we want for $A_g'(x)$

I'll skip all the murky details here, but essentially we'll end up solving a matrix equation that will tell us what our $a_i$ should be (similar to how, in the simple expression, if we are given $\frac{2x+3}{(x+1)(x+2)}$, our result $a_i$ should be $\[1, 1\]$). That matrix equation is defined via:

$$ a = \mathbf{B} \mathbf{C} \mathbf{D_c} \mathbf{D_r} p $$

Where $a, p$ are vectors of the coefficients mentioned in the above formulas, and the rest are $n \times n$ matrices generated to describe the partial fraction decomposition. 


Further, the error may be calculated as:

$$ \textrm{err} = |\Gamma(x) - approx(x)| \leq |\frac{\pi}{2}(\frac{e^g}{\sqrt{2}} - (\frac{p_0}{2} + \sum_{j=1}^{n}(-1)^{j} p_j))| $$

We would like to ensure that $$ \textrm{err} \leq 10^{-14} $$, which is among the limits of IEEE 64 bit floating point (i.e. a `double` in C)


Here's my code implementing the actual formulae:

```python
# generates a table for the Gamma function, used for approximation
# returns (coefs, errbound())
@lru_cache
def get_gamma_table(n, g):

    # we need to generate the array of coefficients `a` such that:
    # Gamma(x) = (x + g + 0.5)^(x+0.5) / (e^(x+g-0.5)) * L_g(x)
    # L_g(x) = a[0] + sum(a[k] / (z + k) for k in range(1, N))

    # essentially, we construct some matrices from number-theoretic functions
    #   and we can generate the coefficients of the partial fraction terms `1 / (z + k)`
    # This greatly simplifies from the native `z(z-1).../((z+1)(z+2)...)` form, which
    #   would require a lot more operations to implement internally (see definition of Ag(z) on wikipedia)

    # calculate an element for the 'B' matrix (n x n)
    def getB(i, j):
        if i == 0:
            return 1
        elif i > 0 and j >= i:
            return (-1) ** (j - i) * choose(i + j - 1, j - i)
        else:
            return 0
    
    # calculate an element for the 'C' matrix (n x n)
    def getC(i, j):
        if i == j and i == 0:
            return mpfr(0.5)
        elif j > i:
            return 0
        else:
            # this is the closed form instead of calculating a sum via the 'S' symbol mentioned in some places
            return int((-1) ** (i - j) * 4 ** j * i * factorial(i + j - 1) / (factorial(i - j) * factorial(2 * j)))

    # calculate an element for the 'Dc' matrix (n x n)
    @lru_cache
    def getDc(i, j):
        if i != j:
            # it's a diagonal matrix, so return 0 for all non-diagonal elements
            return 0
        else:
            # otherwise, compute via the formula given
            return 2 * double_factorial(2 * i - 1)

    # calculate an element for the 'Dr' matrix (n x n)
    @lru_cache
    def getDr(i, j):
        # it's diagonal, so filter out non-diagonal efforts
        if i != j:
            return 0
        elif i == 0:
            return 1
        else:
            # guaranteed to be a integer, so cast it (so no precision is lost)
            return -int(factorial(2 * i) / (2 * factorial(i) * factorial(i - 1)))

    # generate matrices from their generator functions as 2D lists
    # NOTE: this obviously isn't very efficient, but it allows arbitrary precision elements,
    #   which numpy does not
    # these matrices are size <100, so it won't be that bad anyway
    B  = [[getB (i, j) for j in range(n)] for i in range(n)]
    C  = [[getC (i, j) for j in range(n)] for i in range(n)]
    Dc = [[getDc(i, j) for j in range(n)] for i in range(n)]
    Dr = [[getDr(i, j) for j in range(n)] for i in range(n)]

    # the `f` vector, defined as `F` but without the double rising factorial (which Dc has)
    # I left this in here instead of combining here to be more accurate to 
    #   the method given in 4
    f_gn = [sqrt(2) * (e / (2 * (i + g) + 1)) ** (i + 0.5) for i in range(n)]

    # multiply matrices X*Y*...
    def matmul(X, Y, *args):
        if args:
            return matmul(matmul(X, Y), *args)
        else:
            # nonrecursive
            assert len(X[0]) == len(Y)
            M, N, K = len(X), len(Y[0]), len(Y)

            # GEMM kernel (very inefficient; but doesn't matter due to AP floats & small matrix sizes)
            return [[sum(X[i][k] * Y[k][j] for k in range(K)) for j in range(N)] for i in range(M)]

    # normalization factor; we multiply everything by this so it is `pretty close` to 1.0
    W = exp(g) / sqrt(2 * pi) 

    # get the resulting coefficients
    # NOTE: we should get a column vector back, so return the 0th element of each row to get the coefficients
    a = list(map(lambda x: W * x[0], matmul(Dr, B, C, Dc, [[f_gn[i]] for i in range(n)])))

    # compute 'p' coefficients (only needed for the error bound function)
    p = [sum([getC(2 * j, 2 * j) * f_gn[j] * Dc[j][j] for j in range(i)]) for i in range(n)]

    # error bound; does not depend on 'x'
    def errbound():
        # given: err <= |pi/2*W*( sqrt(pi) - u*a )|
        # compute dot product `u * a`
        dot_ua = (a[0] + sum([2 * a[i] / mpfr(2 * i - 1) for i in range(1, n)])) / W
        # compute full formulat
        return abs(pi / 2 * W) * abs(sqrt(pi) - dot_ua)

    # return them
    return a, errbound
```

Great! Now we can generate a function (in `C` code), that should look like:

I define macros for constants such as `PI` for kscript; but you may want to use your own; check the script to see how I precompute constants. The script will generate constants for $\pi$, $\log \pi$, $\sqrt{2 \pi}$, $\log\sqrt{2 \pi}$ in full precision, so we don't have to worry about that (defines them as `MY_PI`, `MY_LOG_PI`, etc)

```c
// evaluate the gamma function at a given point
double my_gamma(double x) {
    if (x <= 0) {
        // check for poles
        if (x == (int)x) return INFINITY;

        // use reflection formula, since it won't converge otherwise
        // Gamma(x) = pi / (sin(pi * x) * Gamma(1 - x))
        return MY_PI / (sin(MY_PI * x) * my_gamma(1 - x));
    } else {
        // shift off by 1 to make indexing cleaner
        x -= 1.0;

        // constant 
        static const double g = ...;
        // length (n) used
        static const int a_n = ...;
        // array of data
        static const long double a[] = {
            ... table values ...
        };

        // keep track of sum
        long double sum = a[0];
        int i;
        for (i = 1; i < a_n; ++i) {
            sum += a[i] / (x + i);
        }

        // temporary variable
        double tmp = x + g + 0.5;
        return sqrt(2 * MY_PI) * pow(tmp, x + 0.5) * exp(-tmp) * sum;
    }
}
```

Similarly, we can do the complex version (replacing `sin` with `csin`, etc):

```c
double complex my_cgamma(double complex x) {
    double x_re = creal(x), x_im = cimag(x);

    // short circuit for real only
    if (x_im == 0.0) return my_gamma(x_re);

    if (x_re < 0) {
        // use reflection formula, since it won't converge otherwise
        // Gamma(x) = pi / (sin(pi * x) * Gamma(1 - x))
        return MY_PI / (csin(MY_PI * x) * my_cgamma(1 - x));
    } else {
        // shift off by 1 to make indexing cleaner
        x -= 1.0;

        // constant 
        static const double g = ...;
        // length (n) used
        static const int a_n = ...;
        // array of data
        static const long double a[] = {
            ... table values ...
        };

        // keep track of sum
        long double complex sum = a[0];
        int i;
        for (i = 1; i < a_n; ++i) {
            sum += a[i] / (x + i);
        }

        // temporary variable
        double complex tmp = x + g + 0.5;
        return MY_SQRT_2PI * pow(tmp, x + 0.5) * exp(-tmp) * sum;
    }
}
```

For the sake of brevity; I won't post the implementation of `my_*lgamma`; it is very similar to these. Run the script yourself to see it's output for that!

## Zeta Function

The hard part is over; the Zeta function is actually (in my opinion) easier to generate a table for. It is based on a (quite) simple formula:

$$\zeta(x) = \frac{1}{d_0(1 - 2^{1-x})} \sum_{k=1}^{n}\frac{(-1)^{k-1}d_k}{k^x} + \gamma_n(x)$$

Where:

$n$ is the number of terms in the approximation, $d$ is a vector of coefficients (similar to $a$ in the Gamma approximation) best fit for a particular model, and $gamma_n(x)$ is the error term

The form of $d_k$ is much simpler to compute; it is given by: 

$$d_k = n \sum_{j=k}^{n}\frac{(n+j-1)!4^j}{(n-j)!(2j)!}$$

The error term is bounded by:

$$|\gamma_n(x)| \leq \frac{2}{(3+\sqrt{8})^n|\Gamma(x)||1-2^{1-x}|} \leq \frac{3(1+2|\Im(x)|e^{\frac{|\Im(x)|\pi}{2}})}{(3+\sqrt{8})^n|1-2^{1-x}|} $$

And, therefore, again in this approximation, we would require that $ \gamma_n(x) \leq 10^{-14}$, to give us a sufficiently accurate approximation


```python

# -- ZETA --

# generates a zeta table which can be used for calculation
# returns (coefs, errbound(x)), which are the coefficients for the table as well as an error bound function
@lru_cache
def get_zeta_table(n):

    # the error bound of the approximation technique for a given input `x`
    def errbound(x):
        # absolute value of the imaginary component
        t = abs(complex(x).imag)

        # calculate error term
        et = (3 / (3 + sqrt(8)) ** n) * ((1 + 2 * t) * exp(t * pi / 2)) / (1 - 2 ** (1 - x))
        return abs(et)

    # compute `d_k`, from Proposition #1 in the paper
    def d(k):
        res = 0
        for j in range(k, n+1):
            num, den = factorial(n + j - 1) * 4 ** j, (factorial(n - j) * factorial(2 * j))
            res += mpfr(num) / den

        return n * res

    # d(0) is the value by which we normalize; this is more efficient
    #   and reduces loss of precision while doing arithmetic in C
    d_norm = d(0)

    # list of 'd's to sum later (normalized to d(0))
    d = [d(k) / d_norm for k in range(1, n + 1)]

    return d, errbound

```


To generate C code for real inputs, we can generate a single table (since, the errbound() function relies on the imaginary component of the input, and does not change significantly with the real portion).

```c
double my_zeta(double x) {
    if (x < 0) {
        // check for negative even integers (which are exactly 0)
        int ix = (int)x;
        if (ix == x && ix % 2 == 0) return 0.0;

        // use reflection formula with the functional equation
        // Zeta(x) = 2 * (2*PI)^(x-1) * sin(x * PI/2) * Gamma(1-x) * Zeta(1 - x)
        return 2 * pow(2 *MY_PI, x - 1) * sin(x * MY_PI / 2) * my_gamma(1 - x) * my_zeta(1 - x);
    } else {
        // for x >= 0, summation with the coefficients will work fine

        // the 'n' used in computation
        static const int n = ...;

        // d_k for k == 0 through n-1 (0-indexing)
        // NOTE: we bake in the alternating sign here, instead of at runtime (cheaper this way)
        static const long double d[] = {
            ... table values ...
        };

        // use `long double` will prevent some rounding errors
        long double sum = 0.0;

        int i;
        // compute elementwise sum
        for (i = 0; i < n; ++i) {
            sum += d[i] * pow(i + 1, -x);
        }

        // divide by the normalization factor in Proposition 1 (without d0, since everything has been normalized by that)
        sum /= 1 - pow(2, 1 - x);

        return (double)sum;
    }
}
```

Note that our zeta function may call the gamma function we defined; this is neccessary due to the fact that the summation will not converge for negative values of $x$

For complex inputs; we need to realize that the maximum error term increases as the imaginary component; for example, the author estimates that it is required that $n \geq 1.3d + 0.9\Im(x)$, if $d$ digits are required for accuracy. However; for $x$ with small imaginary components, we should use the smallest $n$ that will work:

```python

# set to whatever the required digits of precision is
goal_digits = 14.0

# dictiorary where `k, v` indicates:
# when imag(x) <= k, `v` may be used as the list of `d_k` for sufficient accuracy
imag_d_map = { }
# current table length
n = 4

# get table bounds
d, errbound = get_zeta_table(n)

# find tables for imag(x) <= 2 ** p
for p in range(0, 5):

    val_r = 2.0
    val_i = 2 ** p

    while digits_accurate(errbound(val_r + val_i * 1j)) < goal_digits:
        n += 4
        d, errbound = get_zeta_table(n)

    imag_d_map[val_i] = d

```

This code creates a mapping that maps a threshold of the imaginary component to the corresponding minimal table size (and always has $n \equiv 0 \mod 4$), we then loop in our python script to generate the following generated code:

```c
double complex my_czeta(double complex x) {
    // get real and imaginary components
    double x_re = creal(x), x_im = cimag(x);

    // use the real-only version of the function if it is a real argument
    if (x_im == 0.0) return my_zeta(x_re);

    if (x_re < 0) {

        // use reflection formula with the functional equation
        // Zeta(x) = 2 * (2*PI)^(x-1) * sin(x * PI/2) * Gamma(1-x) * Zeta(1 - x)
        return 2 * cpow(2 * MY_PI, x - 1) * csin(x * MY_PI / 2) * my_cgamma(1 - x) * my_czeta(1 - x);

    } else {
        // when the real component is >= 0, summation with the coefficients will work fine

        /* Generated Tables */


        // the 'n' used in computation
        // NOTE: this table is useful for abs(imag(x)) <= 1
        static const int n_0 = 28;

        // d_k for k == 0 through n-1 (0-indexing)
        // NOTE: we bake in the alternating sign here, instead of at runtime (cheaper this way)
        static const long double d_0[] = {
            ... table values ...
        };


        // the 'n' used in computation
        // NOTE: this table is useful for abs(imag(x)) <= 2
        static const int n_1 = 28;

        // d_k for k == 0 through n-1 (0-indexing)
        // NOTE: we bake in the alternating sign here, instead of at runtime (cheaper this way)
        static const long double d_1[] = {
            ... table values ...
        };


        // the 'n' used in computation
        // NOTE: this table is useful for abs(imag(x)) <= 4
        static const int n_2 = 28;

        // d_k for k == 0 through n-1 (0-indexing)
        // NOTE: we bake in the alternating sign here, instead of at runtime (cheaper this way)
        static const long double d_2[] = {
            ... table values ...
        };


        // the 'n' used in computation
        // NOTE: this table is useful for abs(imag(x)) <= 16
        static const int n_4 = 40;

        // d_k for k == 0 through n-1 (0-indexing)
        // NOTE: we bake in the alternating sign here, instead of at runtime (cheaper this way)
        static const long double d_4[] = {
            ... table values ...
        };


        // absolute value of the imaginary portion (used for discriminating amongst tables)
        double x_im_abs = fabs(x_im);

        // the sum of all elements in the series
        long double complex sum = 0.0;
        int i;
        if (x_im_abs <= 1) {
            for (i = 0; i < n_0; ++i) {
                sum += d_0[i] * cpow(i + 1, -x);
            }
        } else if (x_im_abs <= 2) {
            for (i = 0; i < n_1; ++i) {
                sum += d_1[i] * cpow(i + 1, -x);
            }
        } else if (x_im_abs <= 4) {
            for (i = 0; i < n_2; ++i) {
                sum += d_2[i] * cpow(i + 1, -x);
            }
        } else if (x_im_abs <= 8) {
            for (i = 0; i < n_3; ++i) {
                sum += d_3[i] * cpow(i + 1, -x);
            }
        } else {
            for (i = 0; i < n_4; ++i) {
                sum += d_4[i] * cpow(i + 1, -x);
            }
        }

        // transform by the normalization factor
        sum /= 1 - cpow(2, 1 - x);

        return sum;
    }
}
```

The real code goes up to $2^{10}$, but you get the point; essentially, the smallest possible table is generated for every power of two threshold of the imaginary component. For example, $n = 144$ is required for $\Im(x) \leq 128$. If we used that for all numbers, we would be $\frac{144}{28} \approx 5.14$ times slower than we need to be! This will help in performance.


## Testing

To test this, I wrote a small program using the generated code. You can check out the full source code used [here](https://gist.github.com/CadeBrown/52d316379ca6335ad8614991215dc335). I tested values of $x=\sigma+it$, for $\sigma, t \in \[0, 256\)$, and compared the time. I also compared the built in `tgamma` function discussed earlier, and measured how accurate my implementation was relative to it; here are the results summarized:

```
$ gcc -std=c99 -Ofast -fno-math-errno t.c -lm -o test_gz && ./test_gz
# -- ACCURACY
|my_gamma(x)-tgamma(x)| <= 0.000000 , at x=0.000480, accurate to 14.76 digits

# -- SPEED
my_gamma(x), x in [0, 1)      :    0.039 us/iter
my_gamma(x), x in [0, 4)      :    0.038 us/iter
my_gamma(x), x in [0, 16)     :    0.037 us/iter
my_gamma(x), x in [0, 256)    :    0.052 us/iter
my_cgamma(x), x in [0i, 1i)   :    0.137 us/iter
my_cgamma(x), x in [0i, 4i)   :    0.135 us/iter
my_cgamma(x), x in [0i, 16i)  :    0.139 us/iter
my_cgamma(x), x in [0i, 256i) :    0.155 us/iter
my_zeta(x), x in [0, 1)       :    0.395 us/iter
my_zeta(x), x in [0, 4)       :    0.396 us/iter
my_zeta(x), x in [0, 16)      :    0.397 us/iter
my_zeta(x), x in [0, 256)     :    0.416 us/iter
my_czeta(x), x in [0i, 1i)    :    1.356 us/iter
my_czeta(x), x in [0i, 4i)    :    1.494 us/iter
my_czeta(x), x in [0i, 16i)   :    2.005 us/iter
my_czeta(x), x in [0i, 256i)  :   11.456 us/iter
tgamma(x), x in [0, 1)        :    0.029 us/iter
tgamma(x), x in [0, 4)        :    0.036 us/iter
tgamma(x), x in [0, 16)       :    0.058 us/iter
tgamma(x), x in [0, 256)      :    0.050 us/iter
```

Feel free to compile it on your machine and email me results; I'd be happy to include them.

My implementation and glibc's implementation of the gamma function agree everywhere up to `14` digits, which is plenty accurate (we could check Wolfram alpha exactly to see whether I was closer or they were, but they are both fine for our purposes).

The generated source code I use in kscript (as well as for the demo) is available at [https://gist.github.com/CadeBrown/52d316379ca6335ad8614991215dc335](https://gist.github.com/CadeBrown/52d316379ca6335ad8614991215dc335), feel free to use in non-commercial projects.

I hope you've enjoyed the blog, and can use these implementations for your own project. The C code is very simple and should be pretty easy to port to other languages (JavaScript, Python, C#, etc, etc).

Thanks for reading!






