# coding=utf-8
# Copyright 2018 The DisentanglementLib Authors.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Library of commonly used architectures and reconstruction losses."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import numpy as np
import tensorflow as tf
import gin.tf
import tensorflow_probability as tfp


@gin.configurable("encoder", whitelist=["num_latent", "encoder_fn"])
def make_gaussian_encoder(input_tensor,
                          is_training=True,
                          num_latent=gin.REQUIRED,
                          encoder_fn=gin.REQUIRED):
  """Gin wrapper to create and apply a Gaussian encoder configurable with gin.

  This is a separate function so that several different models (such as
  BetaVAE and FactorVAE) can call this function while the gin binding always
  stays 'encoder.(...)'. This makes it easier to configure models and parse
  the results files.

  Args:
    input_tensor: Tensor with image that should be encoded.
    is_training: Boolean that indicates whether we are training (usually
      required for batch normalization).
    num_latent: Integer with dimensionality of latent space.
    encoder_fn: Function that that takes the arguments (input_tensor,
      num_latent, is_training) and returns the tuple (means, log_vars) with the
      encoder means and log variances.

  Returns:
    Tuple (means, log_vars) with the encoder means and log variances.
  """
  with tf.variable_scope("encoder"):
    return encoder_fn(
        input_tensor=input_tensor,
        num_latent=num_latent,
        is_training=is_training)


@gin.configurable("decoder", whitelist=["decoder_fn"])
def make_decoder(latent_tensor,
                 output_shape,
                 is_training=True,
                 decoder_fn=gin.REQUIRED):
  """Gin wrapper to create and apply a decoder configurable with gin.

  This is a separate function so that several different models (such as
  BetaVAE and FactorVAE) can call this function while the gin binding always
  stays 'decoder.(...)'. This makes it easier to configure models and parse
  the results files.

  Args:
    latent_tensor: Tensor latent space embeddings to decode from.
    output_shape: Tuple with the output shape of the observations to be
      generated.
    is_training: Boolean that indicates whether we are training (usually
      required for batch normalization).
    decoder_fn: Function that that takes the arguments (input_tensor,
      output_shape, is_training) and returns the decoded observations.

  Returns:
    Tensor of decoded observations.
  """
  with tf.variable_scope("decoder"):
    return decoder_fn(
        latent_tensor=latent_tensor,
        output_shape=output_shape,
        is_training=is_training)


@gin.configurable("discriminator", whitelist=["discriminator_fn"])
def make_discriminator(input_tensor,
                       is_training=False,
                       discriminator_fn=gin.REQUIRED):
  """Gin wrapper to create and apply a discriminator configurable with gin.

  This is a separate function so that several different models (such as
  FactorVAE) can potentially call this function while the gin binding always
  stays 'discriminator.(...)'. This makes it easier to configure models and
  parse the results files.

  Args:
    input_tensor: Tensor on which the discriminator operates.
    is_training: Boolean that indicates whether we are training (usually
      required for batch normalization).
    discriminator_fn: Function that that takes the arguments
    (input_tensor, is_training) and returns tuple of (logits, clipped_probs).

  Returns:
    Tuple of (logits, clipped_probs) tensors.
  """
  with tf.variable_scope("discriminator"):
    logits, probs = discriminator_fn(input_tensor, is_training=is_training)
    clipped = tf.clip_by_value(probs, 1e-6, 1 - 1e-6)
  return logits, clipped


@gin.configurable("fc_encoder", whitelist=[])
def fc_encoder(input_tensor, num_latent, is_training=True):
  """Fully connected encoder used in beta-VAE paper for the dSprites data.

  Based on row 1 of Table 1 on page 13 of "beta-VAE: Learning Basic Visual
  Concepts with a Constrained Variational Framework"
  (https://openreview.net/forum?id=Sy2fzU9gl).

  Args:
    input_tensor: Input tensor of shape (batch_size, 64, 64, num_channels) to
      build encoder on.
    num_latent: Number of latent variables to output.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    means: Output tensor of shape (batch_size, num_latent) with latent variable
      means.
    log_var: Output tensor of shape (batch_size, num_latent) with latent
      variable log variances.
  """
  del is_training

  flattened = tf.layers.flatten(input_tensor)
  e1 = tf.layers.dense(flattened, 1200, activation=tf.nn.relu, name="e1")
  e2 = tf.layers.dense(e1, 1200, activation=tf.nn.relu, name="e2")
  means = tf.layers.dense(e2, num_latent, activation=None)
  log_var = tf.layers.dense(e2, num_latent, activation=None)
  return means, log_var


@gin.configurable("conv_encoder", whitelist=[])
def conv_encoder(input_tensor, num_latent, is_training=True):
  """Convolutional encoder used in beta-VAE paper for the chairs data.

  Based on row 3 of Table 1 on page 13 of "beta-VAE: Learning Basic Visual
  Concepts with a Constrained Variational Framework"
  (https://openreview.net/forum?id=Sy2fzU9gl)

  Args:
    input_tensor: Input tensor of shape (batch_size, 64, 64, num_channels) to
      build encoder on.
    num_latent: Number of latent variables to output.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    means: Output tensor of shape (batch_size, num_latent) with latent variable
      means.
    log_var: Output tensor of shape (batch_size, num_latent) with latent
      variable log variances.
  """
  del is_training

  e1 = tf.layers.conv2d(
      inputs=input_tensor,
      filters=32,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e1",
  )
  e2 = tf.layers.conv2d(
      inputs=e1,
      filters=32,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e2",
  )
  e3 = tf.layers.conv2d(
      inputs=e2,
      filters=64,
      kernel_size=2,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e3",
  )
  e4 = tf.layers.conv2d(
      inputs=e3,
      filters=64,
      kernel_size=2,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e4",
  )
  flat_e4 = tf.layers.flatten(e4)
  e5 = tf.layers.dense(flat_e4, 256, activation=tf.nn.relu, name="e5")
  means = tf.layers.dense(e5, num_latent, activation=None, name="means")
  log_var = tf.layers.dense(e5, num_latent, activation=None, name="log_var")
  return means, log_var


@gin.configurable("fc_decoder", whitelist=[])
def fc_decoder(latent_tensor, output_shape, is_training=True):
  """Fully connected encoder used in beta-VAE paper for the dSprites data.

  Based on row 1 of Table 1 on page 13 of "beta-VAE: Learning Basic Visual
  Concepts with a Constrained Variational Framework"
  (https://openreview.net/forum?id=Sy2fzU9gl)

  Args:
    latent_tensor: Input tensor to connect decoder to.
    output_shape: Shape of the data.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    Output tensor of shape (None, 64, 64, num_channels) with the [0,1] pixel
    intensities.
  """
  del is_training
  d1 = tf.layers.dense(latent_tensor, 1200, activation=tf.nn.tanh)
  d2 = tf.layers.dense(d1, 1200, activation=tf.nn.tanh)
  d3 = tf.layers.dense(d2, 1200, activation=tf.nn.tanh)
  d4 = tf.layers.dense(d3, np.prod(output_shape))
  return tf.reshape(d4, shape=[-1] + output_shape)


@gin.configurable("deconv_decoder", whitelist=[])
def deconv_decoder(latent_tensor, output_shape, is_training=True):
  """Convolutional decoder used in beta-VAE paper for the chairs data.

  Based on row 3 of Table 1 on page 13 of "beta-VAE: Learning Basic Visual
  Concepts with a Constrained Variational Framework"
  (https://openreview.net/forum?id=Sy2fzU9gl)

  Args:
    latent_tensor: Input tensor of shape (batch_size,) to connect decoder to.
    output_shape: Shape of the data.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    Output tensor of shape (batch_size, 64, 64, num_channels) with the [0,1]
      pixel intensities.
  """
  del is_training
  d1 = tf.layers.dense(latent_tensor, 256, activation=tf.nn.relu)
  d2 = tf.layers.dense(d1, 1024, activation=tf.nn.relu)
  d2_reshaped = tf.reshape(d2, shape=[-1, 4, 4, 64])
  d3 = tf.layers.conv2d_transpose(
      inputs=d2_reshaped,
      filters=64,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
  )

  d4 = tf.layers.conv2d_transpose(
      inputs=d3,
      filters=32,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
  )

  d5 = tf.layers.conv2d_transpose(
      inputs=d4,
      filters=32,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
  )
  d6 = tf.layers.conv2d_transpose(
      inputs=d5,
      filters=output_shape[2],
      kernel_size=4,
      strides=2,
      padding="same",
  )
  return tf.reshape(d6, [-1] + output_shape)


@gin.configurable("fc_discriminator", whitelist=[])
def fc_discriminator(input_tensor, is_training=True):
  """Fully connected discriminator used in FactorVAE paper for all datasets.

  Based on Appendix A page 11 "Disentangling by Factorizing"
  (https://arxiv.org/pdf/1802.05983.pdf)

  Args:
    input_tensor: Input tensor of shape (None, num_latents) to build
      discriminator on.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    logits: Output tensor of shape (batch_size, 2) with logits from
      discriminator.
    probs: Output tensor of shape (batch_size, 2) with probabilities from
      discriminator.
  """
  del is_training
  flattened = tf.layers.flatten(input_tensor)
  d1 = tf.layers.dense(flattened, 1000, activation=tf.nn.leaky_relu, name="d1")
  d2 = tf.layers.dense(d1, 1000, activation=tf.nn.leaky_relu, name="d2")
  d3 = tf.layers.dense(d2, 1000, activation=tf.nn.leaky_relu, name="d3")
  d4 = tf.layers.dense(d3, 1000, activation=tf.nn.leaky_relu, name="d4")
  d5 = tf.layers.dense(d4, 1000, activation=tf.nn.leaky_relu, name="d5")
  d6 = tf.layers.dense(d5, 1000, activation=tf.nn.leaky_relu, name="d6")
  logits = tf.layers.dense(d6, 2, activation=None, name="logits")
  probs = tf.nn.softmax(logits)
  return logits, probs


@gin.configurable("test_encoder", whitelist=["num_latent"])
def test_encoder(input_tensor, num_latent, is_training):
  """Simple encoder for testing.

  Args:
    input_tensor: Input tensor of shape (batch_size, 64, 64, num_channels) to
      build encoder on.
    num_latent: Number of latent variables to output.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    means: Output tensor of shape (batch_size, num_latent) with latent variable
      means.
    log_var: Output tensor of shape (batch_size, num_latent) with latent
      variable log variances.
  """
  del is_training
  flattened = tf.layers.flatten(input_tensor)
  means = tf.layers.dense(flattened, num_latent, activation=None, name="e1")
  log_var = tf.layers.dense(flattened, num_latent, activation=None, name="e2")
  return means, log_var


@gin.configurable("test_decoder", whitelist=[])
def test_decoder(latent_tensor, output_shape, is_training=False):
  """Simple decoder for testing.

  Args:
    latent_tensor: Input tensor to connect decoder to.
    output_shape: Output shape.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    Output tensor of shape (batch_size, 64, 64, num_channels) with the [0,1]
      pixel intensities.
  """
  del is_training
  output = tf.layers.dense(latent_tensor, np.prod(output_shape), name="d1")
  return tf.reshape(output, shape=[-1] + output_shape)



layerwise_deep_layer = [0]


def get_layerwise_deep_layer():
    return layerwise_deep_layer

def gaussian_log_density(samples, mean, log_var):
  from math import pi as pi
  pi = tf.constant(pi)
  normalization = tf.log(2. * pi)
  inv_sigma = tf.exp(-log_var)
  tmp = (samples - mean)
  return -0.5 * (tmp * tmp * inv_sigma + log_var + normalization)


def sample_from_latent_distribution(z_mean, z_logvar):
    """Samples from the Gaussian distribution defined by z_mean and z_logvar."""
    return tf.add(
        z_mean,
        tf.exp(z_logvar / 2) * tf.random_normal(tf.shape(z_mean), 0, 1),
        name="sampled_latent_variable")



@gin.configurable("layerwise_conv_encoder", whitelist=[])
def layerwise_conv_encoder(input_tensor, num_latent, is_training=True,
                           alpha=gin.REQUIRED,gamma=gin.REQUIRED,
                           zeta=gin.REQUIRED, lambdA=gin.REQUIRED):
  """Bayesian Convolutional encoder used in layerwise-VAE.

  Architecture based on row 3 of Table 1 on page 13 of "beta-VAE: Learning Basic Visual
  Concepts with a Constrained Variational Framework"
  (https://openreview.net/forum?id=Sy2fzU9gl)

  Args:
    input_tensor: Input tensor of shape (batch_size, 64, 64, num_channels) to
      build encoder on.
    num_latent: Number of latent variables to output.
    is_training: Whether or not the graph is built for training (UNUSED).

  Returns:
    means: Output tensor of shape (batch_size, num_latent) with latent variable
      means.
    log_var: Output tensor of shape (batch_size, num_latent) with latent
      variable log variances.
  """
  del is_training

  import tensorflow_probability as tfp
  tfd = tfp.distributions
  from disentanglement_lib.utils import joint_distribuition as joint

  model1 = tf.keras.Sequential()
  model1.add(tf.keras.layers.Conv2D(
      filters=32,
      kernel_size=6,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e1",
  ))
  model1.add(tf.keras.layers.Flatten())
  model1.add(tf.keras.layers.Dense(256))

  output1 = model1(input_tensor)
  mean1 = tf.layers.dense(output1, num_latent, activation=None, name="means1")
  var1 = tf.layers.dense(output1, num_latent, activation=None, name="var1")

  normal1 = tfd.MultivariateNormalDiag(
      loc=mean1,
      scale_diag=var1)

  model2 = tf.keras.Sequential()
  model2.add(tf.keras.layers.Conv2D(
      filters=32,
      kernel_size=8,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e2",
  ))

  model2.add(tf.keras.layers.Flatten())
  model2.add(tf.keras.layers.Dense(256))

  output2 = model2(input_tensor)
  mean2 = tf.layers.dense(output2, num_latent, activation=None, name="means2")
  var2 = tf.layers.dense(output2, num_latent, activation=None, name="var2")

  normal2 = tfd.MultivariateNormalDiag(
      loc=mean2,
      scale_diag=var2)


  model3 = tf.keras.Sequential()
  model3.add(tf.keras.layers.Conv2D(
      filters=32,
      kernel_size=4,
      strides=2,
      activation=tf.nn.relu,
      padding="same",
      name="e3",
  ))
  model3.add(tf.keras.layers.Flatten())
  model3.add(tf.keras.layers.Dense(256))

  output3 = model3(input_tensor)
  mean3 = tf.layers.dense(output3, num_latent, activation=None, name="means3")
  var3 = tf.layers.dense(output3, num_latent, activation=None, name="var3")

  normal3 = tfd.MultivariateNormalDiag(
      loc=mean3,
      scale_diag=var3)

  z1 = sample_from_latent_distribution(mean1, var1)
  z2 = sample_from_latent_distribution(mean2, var2)
  z3 = sample_from_latent_distribution(mean3, var3)

  xs = (z1, z2, z3)
  ds = [normal1, normal2, normal3]
  joint_log_prob = sum(tf.exp((d_.prob(x))) for d_, x in zip(ds, xs))

  pz1 = tf.exp(normal1.prob(z1))
  pz2 = tf.exp(normal2.prob(z2))
  pz3 = tf.exp(normal3.prob(z3))

  px_multiply = tf.multiply(pz1, pz2)
  px_multiply = tf.multiply(px_multiply, pz3)

  independence_loss = alpha * tf.reduce_mean(tf.squared_difference(joint_log_prob, px_multiply))
  layerwise_deep_layer[0] = independence_loss
  #layerwise_deep_layer[0] = independence_loss

  print("Helloo", independence_loss)

  mean = tf.add(mean1, mean2)
  mean = tf.add(mean, mean3)
  var = tf.add(var1, var2)
  var = tf.add(var, var3)

  return mean, var
