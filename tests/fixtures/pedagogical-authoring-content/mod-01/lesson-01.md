# What is a convolution?

A convolution slides a small filter across the image, computing one output
value per stride. Same filter weights, every spatial location — that is
where translation equivariance comes from.

::: worked-example
Compute the output shape for a 32×32 input, 3×3 kernel, stride 1, padding 0.

Apply $(W - K + 2P) / S + 1 = (32 - 3 + 0) / 1 + 1 = 30$. Output: **30×30**.
:::

The receptive field grows as you stack convolutions; that's how a deep
network sees larger and larger neighbourhoods of pixels.
