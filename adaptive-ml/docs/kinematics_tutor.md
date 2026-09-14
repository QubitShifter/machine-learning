# 1D Kinematics Tutor

Phase 21 adds the first runnable Physics topic to MAT-PAL
using the same generic tutor, catalog, session, progress,
and student-profile architecture as Mathematics.

## Scope

Subject / domain / topic:

- Physics
- Classical Mechanics
- Kinematics

Supported motion:

- 1D constant velocity
- 1D constant acceleration
- SI units only

Supported equations:

- $v = v_0 + a t$
- $\Delta x = v_0 t + \frac{1}{2} a t^2$
- $v^2 = v_0^2 + 2 a \Delta x$
- $\Delta x = \frac{v_0 + v}{2} t$

## Difficulty

1. From rest or constant velocity, one unknown, positive
   integers, direct substitution.
2. Nonzero $v_0$, find $v$ and $\Delta x$, simple
   acceleration or deceleration.
3. Solve for a less-direct unknown such as $t$ or
   $\Delta x$, still 1D constant acceleration. Generated
   difficulty 3 rejects $v < 0$ after $v = v_0 + a t$,
   and allows $v = 0$.

## Fixed Problem

`kinematics_fixed_001` — Car accelerating from rest.

Given $v_0 = 0\,\mathrm{m/s}$, $a = 3\,\mathrm{m/s^2}$,
$t = 4\,\mathrm{s}$:

- $v = 12\,\mathrm{m/s}$
- $\Delta x = 24\,\mathrm{m}$

The tutor walks through identifying givens, choosing
equations, computing results, and stating the final
answer with units.

## Generated Problems

Generated through the shared problem-generator registry
for `physics / classical_mechanics / kinematics`.
Difficulties 1–3 are available. Seeds are deterministic.
Invalid candidates are retried and rejected rather than
exposed.

## Units

Accepted SI forms include `m/s`, `m s^-1`, `m*s^-1`,
`m/s^2`, `m/s²`, and `m s^-2`. Incompatible dimensions
and missing required units are rejected.

This is not a general dimensional-analysis engine.

## Formula Equivalence

Formula steps accept algebraically equivalent equations,
including nonzero constant scalar multiples with no free
symbols, for example $2v = 2v_0 + 2at$.

Learners do not need the internal symbols. Common
MathLive / textbook aliases normalize before checking:

- $v_f$, $v_{f}$, $v_{\mathrm{f}}$ → $v$
- $v_0$, $v_{0}$ → $v0$
- $\Delta x$, $\Delta_{x}$, $\delta_{x}$, $\delta_x$,
  $\Delta{x}$, `delta x`, `x - x_0` → $dx$
- `\cdot` and `\times` → multiplication
- compact $at$ → $a t$

Symbol-dependent identities such as
$v(v - v_0 - at) = 0$ are rejected. The constant-velocity
equation $\Delta x = v t$ is rejected on the
constant-acceleration displacement step.

## Sign Convention

Positive direction is implied by the problem wording.
Positive acceleration increases velocity in that
direction. Difficulty 1 stays non-negative.

## Catalog And Progress

The Physics landing card becomes runnable from catalog
counts. Progress uses skill id `kinematics`. Adaptive
policy mathematics is unchanged; Kinematics is another
catalog-backed topic. Recommended difficulty and
dashboard statistics are derived from existing student
progress state, not hardcoded.

Student profiles isolate Kinematics progress the same
way they isolate ODE progress.

## Current Limitations

- 1D motion only
- SI units only; no unit conversion
- no general symbolic CAS identities beyond constant
  scalar equivalence of the supported kinematics
  equations
- no vector diagrams or force analysis

## Deferred Physics

- 2D motion
- projectile motion
- Newton's laws
- force diagrams
- energy
- momentum
- rotational mechanics

Deferred to Phase 22 — Internationalization & Bulgarian
Language Support
