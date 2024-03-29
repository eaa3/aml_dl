import tensorflow as tf
import math
import numpy as np
import random
from aml_dl.utilities.tf_optimisers import optimiser_op
from aml_dl.mdn.model.tf_mdn_model import MixtureDensityNetwork
# from aml_io.tf_io import load_tf_check_point
import copy
import os


class EnsembleMDN(object):

    def __init__(self, network_params, sess, tf_sumry_wrtr = None):

        self._load_model = network_params['load_saved_model']
        network_params['load_saved_model'] = False

        self._params = network_params

        self._sess = sess

        self._device_id = network_params['device']
        self._n_ensembles = network_params['n_ensembles']
        self._dim_input = network_params['dim_input']
        self._dim_output = network_params['dim_output']


        try:
            self._batch_size = network_params['batch_size']
        except:
            self._batch_size = 20
            pass

        self._adv_epsilon = network_params['adv_epsilon']
        
        try:
            self._adv_batch_size = network_params['adv_batch_size']
        except:
            self._adv_batch_size = 5

        self._mdn_ensembles = [MixtureDensityNetwork(network_params, tf_sumry_wrtr = tf_sumry_wrtr) for _ in range(self._n_ensembles)]

    def _init_model(self, input_op = None, input_tgt = None):

        with tf.device(self._device_id):

            with tf.name_scope('ensemble_input'):

                if input_op is None:
                    self._x = tf.placeholder(dtype=tf.float32, shape=[None,self._dim_input],  name="x")
                else:
                    self._x = input_op

                if input_tgt is None:
                    self._y = tf.placeholder(dtype=tf.float32, shape=[None,self._dim_output], name="y")
                else:
                    self._y = input_tgt

            for k in range(self._n_ensembles):
                with tf.name_scope('mdn_%d_'%(k,)):
                    self._mdn_ensembles[k]._init_model(input_op=self._x, input_tgt=self._y)


            with tf.name_scope('ensamble_output'):

                self._mu_ops =  [self._mdn_ensembles[k]._ops['mu'] for k in range(self._n_ensembles)]
                self._sigma_ops =  [self._mdn_ensembles[k]._ops['sigma'] for k in range(self._n_ensembles)]
                self._pi_ops =  [self._mdn_ensembles[k]._ops['pi'] for k in range(self._n_ensembles)]


            self._init_op = tf.global_variables_initializer()
            self._saver = tf.train.Saver()

            self._sess.run(self._init_op)


        self._ops = {'x': self._x, 
                     'y': self._y,
                     'mus': self._mu_ops,
                     'sigmas': self._sigma_ops,
                     'pis': self._pi_ops}

        if self._load_model:
            self.load_model()


    def get_adversarial_examples(self, data_x, data_y, loss_grad, epsilon=0.0001, no_examples=50):
    
        rand_indices = np.arange(len(data_x))[:no_examples]#[random.randint(0,len(data_x)-1) for _ in range(no_examples)]
        ##
        x_adv = np.zeros((len(rand_indices), self._dim_input))
        y_adv = np.zeros((len(rand_indices), self._dim_output))

        idx = 0
        for index in rand_indices:
            x_adv[idx,:] = data_x[index,:] + epsilon*np.sign(loss_grad[index])
            y_adv[idx,:] = data_y[index]
            idx += 1

        return x_adv, y_adv

    def train(self, x_train , y_train , sess, iterations):
        #training session

        with tf.device(self._device_id):
            # Keeping track of loss progress as we train
            loss = np.zeros([self._n_ensembles, iterations])
            
            for i in range(iterations):
                #train them parrallely
                for k in range(self._n_ensembles):
                    train_op = self._mdn_ensembles[k]._ops['train']
                    loss_op  = self._mdn_ensembles[k]._ops['loss']
                    grad_op  = self._mdn_ensembles[k]._ops['loss_grad']

                    batchsize = self._batch_size
                    batch_indices = np.random.choice(np.arange(len(x_train)), size=batchsize)
                    x_batch = x_train[batch_indices]
                    y_batch = y_train[batch_indices]
                    
                    #compute value of the gradients
                    loss_grad = sess.run(grad_op, feed_dict={self._mdn_ensembles[k]._ops['x']: x_batch, self._mdn_ensembles[k]._ops['y']: y_batch})
                    
                    #get adversarial examples

                    x_adv, y_adv = self.get_adversarial_examples(data_x = x_batch, 
                                                                 data_y = y_batch, 
                                                                 epsilon=self._adv_epsilon, 
                                                                 loss_grad=loss_grad, 
                                                                 no_examples=self._adv_batch_size)
                    
                    x_batch = copy.deepcopy(np.append(x_adv, x_batch, axis=0))
                    y_batch = copy.deepcopy(np.append(y_adv, y_batch, axis=0))

                    _, loss[k,i] = sess.run([train_op, loss_op], feed_dict={self._mdn_ensembles[k]._ops['x']: x_batch, self._mdn_ensembles[k]._ops['y']: y_batch})


            return loss

    def run_op(self, sess, op,  xs, ys = None):
        out = []

        if ys is None:
            out = sess.run(self._ops[op], feed_dict = { self._x: xs })
        else:
            out = sess.run(self._ops[op], feed_dict = { self._x: xs, self._y: ys })


        return out

    def forward(self, sess, xs, get_full_list=False):

        mean_out = np.zeros((xs.shape[0],self._dim_output))
        var_out = np.zeros((xs.shape[0],self._dim_output))

        if get_full_list:
            mean_list = np.zeros((self._n_ensembles, xs.shape[0],self._dim_output))
            var_list  = np.zeros((self._n_ensembles, xs.shape[0],self._dim_output))
            ensemble_idx = 0

        for model in self._mdn_ensembles:

            mu, sigma, pi = model.forward(sess, xs)

            idx = np.argmax(pi, axis=1)
            idx_max = np.max(pi, axis=1)


            # print pi[:5,:]
            # print idx[:5]
            # print idx_max[:5]

            ids = zip(idx,np.arange(0,xs.shape[0]))

            mu = np.array([ mu[data_idx,:, kernel_idx] for (kernel_idx, data_idx) in ids ])
            std = np.array([ sigma[data_idx, kernel_idx] for (kernel_idx, data_idx) in ids ])

            # mu = np.reshape(mu,(-1,self._dim_output))
            std = np.reshape(std,(-1,1))
            # print mu.shape

            if get_full_list:
                mean_list[ensemble_idx, :, :] = mu
                var_list[ensemble_idx, :, :]  = std + np.reshape(np.sum(np.square(mu),axis=1),(-1,1))
                ensemble_idx += 1

            # Correct only for the single kernel MDN case
            mean_out += mu
            var_out += std + np.reshape(np.sum(np.square(mu),axis=1),(-1,1))

        mean_out /= len(self._mdn_ensembles)
        var_out /= len(self._mdn_ensembles)

        tmp = np.reshape(np.sum(np.square(mean_out),axis=1),(-1,1))

        var_out -= tmp

        if not get_full_list:
            return mean_out, var_out
        else:
            return mean_out, var_out, mean_list, var_list

    def get_model_path(self):
        if 'model_dir' in self._params:
            model_dir = self._params['model_dir']
        else:
            model_path = './inv/'

        if not os.path.exists(model_dir):
            os.makedirs(model_dir)

        if 'model_name' in self._params:
            model_name = self._params['model_name']
        else:
            model_name = 'inv_model.ckpt'

        return model_dir+model_name

    # def load_model(self):
    #     load_tf_check_point(session=self._sess, filename=self.get_model_path())

    def save_model(self):
        save_path = self._saver.save(self._sess, self.get_model_path())
        print("Model saved in file: %s" % save_path)

