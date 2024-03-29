import tensorflow as tf
import math
import numpy as np
from aml_dl.utilities.tf_optimisers import optimiser_op


def init_var(shape, init_type, name, stddev = None):


    # if init_type == 'normal':
    #     return tf.Variable(tf.random_normal(shape, stddev=stddev, dtype=tf.float32), name=name)
    # elif init_type == 'uniform':
    return tf.Variable(tf.random_uniform(shape, minval=-1.0, maxval=1.0, dtype=tf.float32), name=name)



class MixtureDensityNetwork(object):

    def __init__(self, network_params, tf_sumry_wrtr=None, sess=None):
      
        self._dim_input = network_params['dim_input']
        self._dim_output = network_params['dim_output']
        self._n_kernels = network_params['k_mixtures']
        self._n_hidden = network_params['n_hidden']
        self._optimiser = network_params['optimiser']

        self._sess = None

        try:
            self._reg_lambda = network_params['reg_lambda']
        except:
            self._reg_lambda = 0.0


        self._tf_sumry_wrtr = tf_sumry_wrtr

    def _init_model(self, input_op = None, input_tgt = None):

        with tf.name_scope('input'):

            if input_op is None:
                self._x = tf.placeholder(dtype=tf.float32, shape=[None,self._dim_input],  name="x")
            else:
                self._x = input_op

            if input_tgt is None:
                self._y = tf.placeholder(dtype=tf.float32, shape=[None,self._dim_output], name="y")
            else:
                self._y = input_tgt

        with tf.name_scope('output_fc_op'):
            self._output_fc_op = self._init_fc_layer(self._x)
            if self._tf_sumry_wrtr is not None:
                self._tf_sumry_wrtr.add_variable_summaries(self._output_fc_op)

        with tf.name_scope('init_mixture_params'):
            self._mus_op, self._sigmas_op, self._pis_op = self._init_mixture_parameters(self._output_fc_op)
            if self._tf_sumry_wrtr is not None:
                self._tf_sumry_wrtr.add_variable_summaries(self._mus_op)
                self._tf_sumry_wrtr.add_variable_summaries(self._sigmas_op)
                self._tf_sumry_wrtr.add_variable_summaries(self._pis_op)

        with tf.name_scope('cost_inv'):
            self._loss_op = self._init_loss(self._mus_op, self._sigmas_op, self._pis_op, self._y)
            #gradient of the loss function with respect to the input
            self._loss_grad = tf.gradients(self._loss_op, [self._x])[0]
            if self._tf_sumry_wrtr is not None:
                self._tf_sumry_wrtr.add_variable_summaries(self._loss_op)

      
        self._train_op = self._init_train(self._loss_op)
        self._ops = {'x': self._x, 
                     'y': self._y, 
                     'mu': self._mus_op, 
                     'sigma': self._sigmas_op, 
                     'pi': self._pis_op, 
                     'loss': self._loss_op, 
                     'train': self._train_op,
                     'loss_grad':self._loss_grad}

        if self._tf_sumry_wrtr is not None:
            self._tf_sumry_wrtr.write_summary()

    def init_model(self, input_op = None, input_tgt = None):
        self._init_model(input_op = None, input_tgt = None)

    def _init_fc_layer(self, input, stddev = 0.3):

        n_params_out = (self._dim_output + 2)*self._n_kernels

        input_op = input

        if type(self._n_hidden) == type([]):

            reg_terms = []
            for i in range(0,len(self._n_hidden)):

                input_dim = input_op.get_shape().dims[1].value

                Wh = init_var(shape=[input_dim, self._n_hidden[i]], init_type='normal', stddev=stddev, name='w_' + str(i)) 
                bh = init_var(shape=[1, self._n_hidden[i]], init_type='normal', stddev=stddev, name='b_' + str(i))

                input_op = tf.nn.tanh(tf.matmul(input_op, Wh) + bh)

                get_reg_term = lambda input_tensor: tf.sqrt(tf.reduce_sum(tf.square(input_tensor)))
                reg_terms.append(get_reg_term(Wh) + get_reg_term(bh))

            input_dim = input_op.get_shape().dims[1].value

            Wo = init_var(shape=[input_dim, n_params_out], init_type='normal', stddev=stddev, name='w_out_fc') 
            bo = init_var(shape=[1, n_params_out], init_type='normal', stddev=stddev, name='b_out_fc') 

            output_fc = tf.matmul(input_op, Wo) + bo

            self._reg_term = sum([rg for rg in reg_terms])

            return output_fc

        else:

            ## TODO: Output dimensions are wrong here.
            Wh = init_var(shape=[self._dim_input, self._n_hidden], init_type='normal',  stddev=stddev, name='w_0')
            bh = init_var(shape=[self._dim_input, self._n_hidden], init_type='normal',  stddev=stddev, name='b_0')

            Wo = init_var(shape=[self._n_hidden, n_params_out], init_type='normal', stddev=stddev, name='w_out_fc')
            bo = init_var(shape=[1, n_params_out], init_type='normal', stddev=stddev, name='b_out_fc')

            hidden_layer = tf.nn.tanh(tf.matmul(input, Wh) + bh)
            output_fc = tf.matmul(hidden_layer, Wo) + bo

            return output_fc

    def _init_mixture_parameters(self, output):

        c = self._dim_output
        m = self._n_kernels

        reshaped_output = tf.reshape(output,[-1, (c+2), m])
        mus = reshaped_output[:, :c, :]
        sigmas = tf.exp(reshaped_output[:, c, :])
        pis = tf.nn.softmax(reshaped_output[:, c+1, :])

        return mus, sigmas, pis


    def _init_loss(self, mus, sigmas, pis, ys):

        m = self._n_kernels

        kernels = self._kernels(mus, sigmas, ys)

        result = tf.multiply(kernels,tf.reshape(pis, [-1, 1, m]))
        result = tf.reduce_sum(result, 2, keep_dims=True)

        epsilon = 1e-20
        result = -tf.log(tf.maximum(result,epsilon))

        return tf.reduce_mean(result, 0) + self._reg_lambda * self._reg_term

    def _init_train(self,loss_op):

        train_op = optimiser_op(loss_op, self._optimiser)

        return train_op


    # Do the log trick here if it is not good enough the way it is now
    def _kernels(self, mus, sigmas, ys):
        c = self._dim_output
        m = self._n_kernels

        reshaped_ys = tf.reshape(ys, [-1, c, 1])
        reshaped_sigmas = tf.reshape(sigmas, [-1, 1, m])

        diffs = tf.subtract(mus, reshaped_ys) # broadcasting
        expoents = tf.reduce_sum( tf.multiply(diffs,diffs), 1, keep_dims=True )

        sigmacs = tf.pow(reshaped_sigmas,c)

        expoents = tf.multiply(-0.5,tf.multiply(tf.reciprocal(sigmacs), expoents))

        denominators = tf.pow(2*np.pi,c/2.0)*tf.sqrt(sigmacs)

        out = tf.div(tf.exp(expoents),denominators)

        return out

    def _mixture(self, kernels, pis):

        result = tf.multiply(kernels,tf.reshape(pis, [-1, 1, m]))
        mixture = tf.reduce_sum(result, 2, keep_dims=True)



    def run(self, sess, xs, ys = None):
        out = []
        if ys is None:
            out = sess.run([self._mus_op, self._sigmas_op, self._pis_op], feed_dict = { self._x: xs })
        else:
            out = sess.run([self._mus_op, self._sigmas_op, self._pis_op, self._loss_op], feed_dict = { self._x: xs, self._y: ys})

        return out

    def forward(self, sess, xs):

        out = sess.run([self._mus_op, self._sigmas_op, self._pis_op], feed_dict = { self._x: xs })

        return out

    def predict(self, sess, xs):

        mus, sigmas, pis = self.forward(sess, xs)

        out_mu = np.zeros((pis.shape[0],mus.shape[1]))
        out_sigmas = np.zeros((pis.shape[0],sigmas.shape[1]))
        for i in range(pis.shape[0]):
            pi = pis[i]
            idx = np.argmax(pi)
            # print mus[k]
            # print mus[k].shape
            mu = mus[i][0][idx]
            std = sigmas[i][idx]
            out_mu[i,:] = mu 
            out_sigmas[i] = std

            # print std



        return out_mu, out_sigmas





    def run_op(self, sess, op,  xs, ys = None):
        out = []

        if ys is None:
            out = sess.run([self._ops[op]], feed_dict = { self._x: xs })
        else:
            out = sess.run([self._ops[op]], feed_dict = { self._x: xs, self._y: ys })


        return out

    def train(self, sess, x_data, y_data, epochs = 10000):
        loss = np.zeros(epochs)
        for i in range(epochs):
            sess.run(self._ops['train'],feed_dict={self._ops['x']: x_data, self._ops['y']: y_data})
            loss[i] = sess.run(self._ops['loss'], feed_dict={self._ops['x']: x_data, self._ops['y']: y_data})

        return loss


class MixtureOfGaussians(object):


  def sample_pi_idx(self, x, pdf):
    N = pdf.size
    acc = 0

    for i in range(0, N):
      acc += pdf[i]
      if (acc >= x):
        return i

        print 'failed to sample mixture weight index'


    return -1


  def max_pi_idx(self, pdf):

    i = np.argmax(pdf)

    return i

  def sample_gaussian(self, rn, mu, std):


    return mu + rn*std

  def generate_mixture_samples_from_max_pi(self, out_pi, out_mu, out_sigma, m_samples=10):


    # Number of test inputs

    N = out_mu.shape[0]

    M = m_samples

    result = np.random.rand(N, M)
    rn  = np.random.randn(N, M) # normal random matrix (0.0, 1.0)

    # Generates M samples from the mixture for each test input

    for j in range(M):
      for i in range(0, N):
        idx = self.max_pi_idx(out_pi[i])
        mu = out_mu[i, idx]
        std = out_sigma[i, idx]
        result[i, j] = self.sample_gaussian(rn[i, j], mu, std)


    return result


  def generate_mixture_samples(self, out_pi, out_mu, out_sigma, m_samples=10):


    # Number of test inputs
    N = out_mu.shape[0]
    M = m_samples

    result = np.random.rand(N, M) # initially random [0, 1]
    rn  = np.random.randn(N, M) # normal random matrix (0.0, 1.0)
    mu  = 0
    std = 0
    idx = 0

    # Generates M samples from the mixture for each test input
    for j in range(M):
      for i in range(0, N):
        idx = self.sample_pi_idx(result[i, j], out_pi[i])
        mu = out_mu[i, idx]
        std = out_sigma[i, idx]
        result[i, j] = self.sample_gaussian(rn[i, j], mu, std)


    return result