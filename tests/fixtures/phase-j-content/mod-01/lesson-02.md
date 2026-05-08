# Hands-on: build your first conv

Time to wire a `Conv2d` layer in PyTorch. Reuse the output-shape formula
from lesson-01 to plan ahead.

::: faded-example
For a 64×64 input, 5×5 kernel, stride 1, padding 2 — what's the output
shape?

(Hint: re-apply the formula. The padding is chosen to keep height and
width unchanged.)
:::

::: independent-practice
Given a 28×28 input, design a `Conv2d` layer that outputs **14×14**.
State your kernel size, stride, and padding. Justify each choice in one
sentence.
:::
