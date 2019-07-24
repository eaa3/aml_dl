import os

check_point_dir   = os.environ['AML_DATA'] + '/aml_dl/mdn/tf_check_points/'
training_data_dir = ''
summary_dir       = os.environ['AML_DATA'] + '/aml_dl/mdn/summaries/'

try:
    training_data_dir = os.environ['AML_DATA'] + '/aml_dl/baxter_push_data/'
except:
    print "AML_DATA environment variable is not set."

if not os.path.exists(training_data_dir):
    print "Training data folder does not exist..."
    #raise ValueError


NUM_FP         = 10 #this is not the right value?
IMAGE_WIDTH    = 640
IMAGE_HEIGHT   = 480
IMAGE_CHANNELS = 3


train_file_indices = range(1, 10)
test_file_indices  = range(381,397)

adam_params = {
    'type': 'adam',
    'params': {'learning_rate' : 0.001, 'beta1': 0.9, 'beta2': 0.999, 'epsilon': 1e-08, 'use_locking': False}
}

network_params_inv = {
    'num_filters': [5, 5, NUM_FP],
    'dim_input': 14, 
    'dim_output': 2,
    'n_hidden': [24],
    'k_mixtures': 40,
    'batch_size': 25,
    'write_summary': True,
    'learning_rate': 0.0005,
    'image_width': IMAGE_WIDTH,
    'image_height': IMAGE_HEIGHT,
    'image_channels': IMAGE_CHANNELS,
    'image_size': IMAGE_WIDTH*IMAGE_HEIGHT*IMAGE_CHANNELS,
    'load_saved_model': False,
    'model_dir': check_point_dir + '/inv/',
    'model_name':'push_model_inv_40_kernels_ep50000.ckpt',
    'train_file_indices': train_file_indices,
    'test_file_indices': test_file_indices,
    'training_data_dir': training_data_dir,
    'optimiser': adam_params,
    'summary_dir':summary_dir+'/inv/',
    'device': '/cpu:0',
}


num_conv_layers = 3
filter_sizes_each_layer = [5, 5, 5]
num_filters_per_layer = [16,32,16]

if len(filter_sizes_each_layer) != num_conv_layers:
    print "Number of filter sizes in each layer has to specified"
    raise ValueError

if len(num_filters_per_layer) != num_conv_layers:
    print "Number of filters in each layer has to specified"
    raise ValueError

network_params_cnn = {
    'num_conv_layers':num_conv_layers,
    'num_fc_layers':2,
    'num_units_in_fc':[128,7],
    'output_order':['qt_w','qt_x','qt_y','qt_z','x','y','z'],
    'filter_sizes':filter_sizes_each_layer,
    'num_filters':num_filters_per_layer,
    'image_width': IMAGE_WIDTH,
    'image_height': IMAGE_HEIGHT,
    'image_channels': IMAGE_CHANNELS,
    'dim_output':7,
    'max_pooling':None,#{'x':2, 'y':2},
    'use_dropout':False,
    'strides':[1,1,1,1],
    'padding':'SAME',
    'img_resize':{'width':10,'height':10},
    'use_relu':True,
    'stddev':0.05,
    'load_saved_model': True,
    'model_dir': check_point_dir+'/cnn/',
    'model_name':'push_model_cnn.ckpt',
    'training_data_dir':training_data_dir,
    'train_file_indices':train_file_indices,
    'test_file_indices':test_file_indices,
    'summary_dir':summary_dir+'/cnn/',
    'device':'/cpu:0',

}


batch_params_cmbnd = {
'buffer_size':45, 
'batch_size': 20, 
'data_file_indices': train_file_indices, 
'model_type':'cnn', 
'use_random_batches':True}

cnn_network_params = {
'num_layers':2,
'filter_sizes':[5, 5],
'num_filters':[16,32],
'layer_names':['cnn_layer1', 'cnn_layer2'],
'layer_outputs':[128,10],
'image_width': IMAGE_WIDTH,
'image_height': IMAGE_HEIGHT,
'image_channels': IMAGE_CHANNELS,
'max_pooling':[None, None],#{'x':2, 'y':2},
'use_dropout':[False, False],
'strides':[[1,1,1,1],[1,1,1,1]],
'activation':['relu', 'relu'],
'padding':['SAME','SAME'],
'img_resize':{'width':10,'height':10},
'stddev':0.05,
}

fc_network_params = {
'num_layers':2,
'layer_names':['fc_layer1', 'fc_layer2'],
'num_units_per_layer':[10,7],
'layer_outputs':[7, 7],
'max_pooling':[None, None],
'use_dropout':[False, False],
'activation':['idty', 'idty'],
'stddev':0.05,  
}

network_params_cmbnd = {
'cnn_params':cnn_network_params,
'fc_params':fc_network_params,
'optimiser': adam_params,
'batch_params':batch_params_cmbnd, #pass None if not using batch training
'write_summary':True,
'dim_input':300,
'dim_output':7,
'output_order':['qt_w','qt_x','qt_y','qt_z','x','y','z'],
'load_saved_model': True,
'model_dir': check_point_dir+'/cmbnd/',
'model_name':'push_model_fwd_with_cnn.ckpt',
'training_data_dir':training_data_dir,
'train_file_indices':train_file_indices,
'test_file_indices':test_file_indices,
'summary_dir':summary_dir+'/cmbnd/',
'device':'/cpu:0',
}


batch_params_fwd = {
'buffer_size':45, 
'batch_size': 20, 
'data_file_indices': train_file_indices, 
'model_type':'fwd', 
'use_random_batches':False}

network_params_fwd = {
    'num_filters': [5, 5, NUM_FP],
    'dim_input': 9, 
    'dim_output': 7,
    'batch_params':batch_params_fwd, #pass None if not using batch training
    'cnn_params':None,
    'fc_params':fc_network_params,
    'optimiser': adam_params,
    'write_summary':True,
    'output_order':['qt_w','qt_x','qt_y','qt_z','x','y','z'],
    'batch_size': 25,
    'load_saved_model': True,
    'model_dir': check_point_dir+'/fwd/',
    'model_name':'push_model_fwd.ckpt',
    'training_data_dir':training_data_dir,
    'train_file_indices':train_file_indices,
    'test_file_indices':test_file_indices,
    'summary_dir':summary_dir+'/fwd/',
    'device': '/cpu:0',
}


batch_params_siam = {
'buffer_size':45, #default, it gets re-initialized in batch_creator
'batch_size': 20, 
'data_file_indices': train_file_indices, 
'model_type':'siam', 
'use_random_batches':False}

NUM_CNN_LAYERS_SIAM = 3

cnn_network_params_siam = {
'num_layers':NUM_CNN_LAYERS_SIAM,
'filter_sizes':[5, 5, 5],
'num_filters':[16, 32, 64],
'layer_names':['cnn_layer%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'variable_names':['cnn_variables%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'weight_names':['cnn_weight%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'bias_names':['cnn_bias%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'pre_activate_scope':['cnn_pre_activate%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'activate_scope':['cnn_activate%d'%i for i in range(NUM_CNN_LAYERS_SIAM)],
'layer_outputs':[128, 10, 10],
'image_width': IMAGE_WIDTH,
'image_height': IMAGE_HEIGHT,
'image_channels': IMAGE_CHANNELS,
'max_pooling':[None, None, None],#{'x':2, 'y':2},
'use_dropout':[False, False, False],
'strides':[[1,1,1,1],[1,1,1,1], [1,1,1,1]],
'activation':['relu', 'relu', 'relu'],
'padding':['SAME','SAME', 'SAME'],
'img_resize':{'width':224,'height':224},
'stddev':0.05,
}

fc_network_params_siam = {
'num_layers':3,
'state_dim':7,
'action_dim':2,
'layer_names':['fc_layer1', 'fc_layer2', 'fc_layer3'],
'num_units_per_layer':[10, 9, 7],
'layer_outputs':[7, 7, 7],
'max_pooling':[None, None, None],
'use_dropout':[False, False, False],
'activation':['idty', 'idty', 'idty'],
'stddev':0.05,  
}

cost_weights = {
    'fwd':0.1,
    'inv':1.,
}

network_params_siam = {
'cnn_params':cnn_network_params_siam,
'fc_params':fc_network_params_siam,
'inv_params': network_params_inv,
'optimiser': adam_params,
'fwd_loss_wght': 0.5,
'mdn_loss_wght':1.,
'cost_weights':cost_weights,
'batch_params':batch_params_siam, #pass None if not using batch training
'write_summary':True,
'dim_input':300,
'dim_output':7,
'output_order':['qt_w','qt_x','qt_y','qt_z','x','y','z'],
'load_saved_model': True,
'model_dir': check_point_dir+'/siam/',
'model_name':'push_model_fwd_with_siam.ckpt',
'training_data_dir':training_data_dir,
'train_file_indices':train_file_indices,
'test_file_indices':test_file_indices,
'summary_dir':summary_dir+'/siam/',
'device':'/cpu:0',
}