# Copyright 2018 Changan Wang

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import sys

import tensorflow as tf

import numpy as np

from net import ssd_net_high
from net import ssd_net_low

#from dataset import dataset_common
from preprocessing import ssd_preprocessing
from utility import anchor_manipulator
from utility import scaffolds

# hardware related configuration
tf.app.flags.DEFINE_integer(
    'num_readers', 8,
    'The number of parallel readers that read data from the dataset.')
tf.app.flags.DEFINE_integer(
    'num_preprocessing_threads', 24,
    'The number of threads used to create the batches.')
tf.app.flags.DEFINE_integer(
    'num_cpu_threads', 0,
    'The number of cpu cores used to train.')
tf.app.flags.DEFINE_float(
    'gpu_memory_fraction', 1., 'GPU memory fraction to use.')
# scaffold related configuration
tf.app.flags.DEFINE_string(
    'model_dir', './logs/',
    'The directory where the model will be stored.')
tf.app.flags.DEFINE_integer(
    'log_every_n_steps', 10,
    'The frequency with which logs are printed.')
tf.app.flags.DEFINE_integer(
    'save_summary_steps', 500,
    'The frequency with which summaries are saved, in seconds.')
# model related configuration
tf.app.flags.DEFINE_integer(
    'train_image_size', 300,
    'The size of the input image for the model to use.')
tf.app.flags.DEFINE_integer(
    'train_epochs', 1,
    'The number of epochs to use for training.')
tf.app.flags.DEFINE_integer(
    'batch_size', 1,
    'Batch size for training and evaluation.')
tf.app.flags.DEFINE_string(
    'data_format', 'channels_first',  # 'channels_first' or 'channels_last'
    'A flag to override the data format used in the model. channels_first '
    'provides a performance boost on GPU but is not always compatible '
    'with CPU. If left unspecified, the data format will be chosen '
    'automatically based on whether TensorFlow was built for CPU or GPU.')
tf.app.flags.DEFINE_float(
    'negative_ratio', 3., 'Negative ratio in the loss function.')
tf.app.flags.DEFINE_float(
    'match_threshold', 0.5, 'Matching threshold in the loss function.')
tf.app.flags.DEFINE_float(
    'neg_threshold', 0.5, 'Matching threshold for the negtive examples in the loss function.')
tf.app.flags.DEFINE_float(
    'select_threshold', 0.01, 'Class-specific confidence score threshold for selecting a box.')
tf.app.flags.DEFINE_float(
    'min_size', 0.03, 'The min size of bboxes to keep.')
tf.app.flags.DEFINE_float(
    'nms_threshold', 0.45, 'Matching threshold in NMS algorithm.')
tf.app.flags.DEFINE_integer(
    'nms_topk', 200, 'Number of total object to keep after NMS.')
tf.app.flags.DEFINE_integer(
    'keep_topk', 400, 'Number of total object to keep for each image before nms.')
# optimizer related configuration
tf.app.flags.DEFINE_float(
    'weight_decay', 5e-4, 'The weight decay on the model weights.')
# checkpoint related configuration
tf.app.flags.DEFINE_string(
    'checkpoint_path', './model',
    'The path to a checkpoint from which to fine-tune.')
tf.app.flags.DEFINE_string(
    'model_scope', 'ssd300',
    'Model scope name used to replace the name_scope in checkpoint.')

################################################################################
## Daniel's Custom Added flags                                                ##
################################################################################

tf.app.flags.DEFINE_string(
    'class_set', 'original',
    'Which reduced dataset is to be used? One of `original`, `vehicles`, `animals`, `indoor`, `person`.')
tf.app.flags.DEFINE_string(
    'specify_gpu', None,
    'Which GPU(s) to use, in a string (e.g. `0,1,2`) If `None`, uses all available.')
tf.app.flags.DEFINE_float(
    'add_noise', None,
    'Whether to add gaussian noise to the imageset prior to training.')

# Quantization parameters
tf.app.flags.DEFINE_boolean(
    'qw_en', False,
    'If True, enables quantization of network weights. Use flag `qw_bits` to set the number of quantization bits.')
tf.app.flags.DEFINE_boolean(
    'qa_en', False,
    'If True, enables quantization of network activations. Use flag `qa_bits` to set the number of quantization bits.')
tf.app.flags.DEFINE_integer(
    'qw_bits', 32,
    'Number of quantization bits to allocate to the network weights.')
tf.app.flags.DEFINE_integer(
    'qa_bits', 32,
    'Number of quantization bits to allocate to the network activations.')

# Pruning parameters
tf.app.flags.DEFINE_boolean(
    'pw_en', False,
    'If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.')
tf.app.flags.DEFINE_boolean(
    'pa_en', False,
    'If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.')
tf.app.flags.DEFINE_float(
    'threshold_w', 0,
    'Pruning threshold under which to zero out the weights to.')
tf.app.flags.DEFINE_float(
    'threshold_a', 0,
    'Pruning threshold under which to zero out the activations.')
tf.app.flags.DEFINE_integer(
    'begin_pruning_at_step', 20000,
    'Specifies which step pruning will begin to occur after.')
tf.app.flags.DEFINE_integer(
    'end_pruning_at_step', 100000,
    'Specifies which step pruning will end after.')
tf.app.flags.DEFINE_integer(
    'pruning_frequency', 1000,
    'Specifies how often to prune the network.')
tf.app.flags.DEFINE_float(
    'target_sparsity', 0.5,
    'Specify the target sparsity for pruning such that pruning will stop once the weight and activation-sparsity reaches this value.')

###### HACKY GROSSNESS HEREIN ######
tf.app.flags.DEFINE_boolean(
    "pw_conv1_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv1_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv1_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv1_2", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv2_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv2_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv2_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv2_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv2_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv2_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv2_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv2_2", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv3_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv3_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv3_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv3_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv3_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv3_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv3_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv3_2", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv3_3",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv3_3",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv3_3", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv3_3", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv4_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv4_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv4_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv4_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv4_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv4_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv4_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv4_2", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv4_3",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv4_3",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv4_3", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv4_3", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv5_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv5_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv5_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv5_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv5_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv5_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv5_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv5_2", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv5_3",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv5_3",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv5_3", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv5_3", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_fc6",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_fc6",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_fc6", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_fc6", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_fc7",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_fc7",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_fc7", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_fc7", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv8_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv8_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv8_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv8_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv8_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv8_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv8_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv8_2", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv9_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv9_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv9_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv9_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv9_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv9_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv9_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv9_2", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv10_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv10_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv10_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv10_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv10_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv10_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv10_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv10_2", 0, "Pruning threshold under which to zero out the activations."
)

tf.app.flags.DEFINE_boolean(
    "pw_conv11_1",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv11_1",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv11_1", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv11_1", 0, "Pruning threshold under which to zero out the activations."
)
tf.app.flags.DEFINE_boolean(
    "pw_conv11_2",
    False,
    "If True, enables pruning of network weights. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_boolean(
    "pa_conv11_2",
    False,
    "If True, enables pruning of network activations. Use pruning parameters below to fine-tune behaviour.",
)
tf.app.flags.DEFINE_float(
    "tw_conv11_2", 0, "Pruning threshold under which to zero out the weights to."
)
tf.app.flags.DEFINE_float(
    "ta_conv11_2", 0, "Pruning threshold under which to zero out the activations."
)

FLAGS = tf.app.flags.FLAGS

original_dataset = '../VOCROOT_backup/tfrecords'
vehicles_dataset = '../VOCROOT_vehicles/tfrecords'
animals_dataset  = '../VOCROOT_animals/tfrecords'
indoor_dataset   = '../VOCROOT_indoor/tfrecords'
person_dataset   = '../VOCROOT_person/tfrecords'

if FLAGS.class_set == 'original':
    from dataset import dataset_common
elif FLAGS.class_set == 'vehicles':
    from dataset import dataset_common_vehicles as dataset_common
elif FLAGS.class_set == 'animals':
    from dataset import dataset_common_animals as dataset_common
elif FLAGS.class_set == 'indoor':
    from dataset import dataset_common_indoor as dataset_common
elif FLAGS.class_set == 'person':
    from dataset import dataset_common_person as dataset_common
else:
    from dataset import dataset_common

tf.app.flags.DEFINE_integer(
    'num_classes', len(dataset_common.VOC_LABELS_reduced), 'Number of classes to use in the dataset.')
tf.app.flags.DEFINE_string(
    'data_dir', '../VOCROOT_backup/tfrecords',
    'The directory where the dataset input data is stored.')

# CUDA_VISIBLE_DEVICES


def get_checkpoint():
    if tf.train.latest_checkpoint(FLAGS.model_dir):
        tf.logging.info(
            'Ignoring --checkpoint_path because a checkpoint already exists in %s' % FLAGS.model_dir)
        return None

    if tf.gfile.IsDirectory(FLAGS.checkpoint_path):
        checkpoint_path = tf.train.latest_checkpoint(FLAGS.checkpoint_path)
    else:
        checkpoint_path = FLAGS.checkpoint_path

    return checkpoint_path


# couldn't find better way to pass params from input_fn to model_fn
# some tensors used by model_fn must be created in input_fn to ensure they are in the same graph
# but when we put these tensors to labels's dict, the replicate_model_fn will split them into each GPU
# the problem is that they shouldn't be splited
global_anchor_info = dict()


def input_pipeline(dataset_pattern='train-*', is_training=True, batch_size=FLAGS.batch_size):
    def input_fn():
        out_shape = [FLAGS.train_image_size] * 2
        anchor_creator = anchor_manipulator.AnchorCreator(out_shape,
                                                          layers_shapes=[
                                                              (38, 38), (19, 19), (10, 10), (5, 5), (3, 3), (1, 1)],
                                                          anchor_scales=[
                                                              (0.1,), (0.2,), (0.375,), (0.55,), (0.725,), (0.9,)],
                                                          extra_anchor_scales=[
                                                              (0.1414,), (0.2739,), (0.4541,), (0.6315,), (0.8078,), (0.9836,)],
                                                          anchor_ratios=[(1., 2., .5), (1., 2., 3., .5, 0.3333), (
                                                              1., 2., 3., .5, 0.3333), (1., 2., 3., .5, 0.3333), (1., 2., .5), (1., 2., .5)],
                                                          #anchor_ratios = [(2., .5), (2., 3., .5, 0.3333), (2., 3., .5, 0.3333), (2., 3., .5, 0.3333), (2., .5), (2., .5)],
                                                          layer_steps=[8, 16, 32, 64, 100, 300])
        all_anchors, all_num_anchors_depth, all_num_anchors_spatial = anchor_creator.get_all_anchors()

        num_anchors_per_layer = []
        for ind in range(len(all_anchors)):
            num_anchors_per_layer.append(
                all_num_anchors_depth[ind] * all_num_anchors_spatial[ind])

        anchor_encoder_decoder = anchor_manipulator.AnchorEncoder(allowed_borders=[1.0] * 6,
                                                                  positive_threshold=FLAGS.match_threshold,
                                                                  ignore_threshold=FLAGS.neg_threshold,
                                                                  prior_scaling=[0.1, 0.1, 0.2, 0.2])

        def image_preprocessing_fn(image_, labels_, bboxes_): return ssd_preprocessing.preprocess_image(
            image_, labels_, bboxes_, out_shape, add_noise=FLAGS.add_noise, is_training=is_training, data_format=FLAGS.data_format, output_rgb=False)
        def anchor_encoder_fn(glabels_, gbboxes_): return anchor_encoder_decoder.encode_all_anchors(
            glabels_, gbboxes_, all_anchors, all_num_anchors_depth, all_num_anchors_spatial)

        if FLAGS.class_set == 'original':
            data_dir = original_dataset
        elif FLAGS.class_set == 'vehicles':
            data_dir = vehicles_dataset
        elif FLAGS.class_set == 'animals':
            data_dir = animals_dataset
        elif FLAGS.class_set == 'indoor':
            data_dir = indoor_dataset
        elif FLAGS.class_set == 'person':
            data_dir = person_dataset
        else:
            data_dir = FLAGS.data_dir

        image, filename, shape, loc_targets, cls_targets, match_scores = dataset_common.slim_get_batch(FLAGS.num_classes,
                                                                                                       batch_size,
                                                                                                       ('train' if is_training else 'val'),
                                                                                                       os.path.join(
                                                                                                           data_dir, dataset_pattern),
                                                                                                       FLAGS.num_readers,
                                                                                                       FLAGS.num_preprocessing_threads,
                                                                                                       image_preprocessing_fn,
                                                                                                       anchor_encoder_fn,
                                                                                                       num_epochs=FLAGS.train_epochs,
                                                                                                       is_training=is_training)
        global global_anchor_info
        global_anchor_info = {'decode_fn': lambda pred: anchor_encoder_decoder.decode_all_anchors(pred, num_anchors_per_layer),
                              'num_anchors_per_layer': num_anchors_per_layer,
                              'all_num_anchors_depth': all_num_anchors_depth}

        return {'image': image, 'filename': filename, 'shape': shape, 'loc_targets': loc_targets, 'cls_targets': cls_targets, 'match_scores': match_scores}, None
    return input_fn


def modified_smooth_l1(bbox_pred, bbox_targets, bbox_inside_weights=1., bbox_outside_weights=1., sigma=1.):
    """
        ResultLoss = outside_weights * SmoothL1(inside_weights * (bbox_pred - bbox_targets))
        SmoothL1(x) = 0.5 * (sigma * x)^2,    if |x| < 1 / sigma^2
                      |x| - 0.5 / sigma^2,    otherwise
    """
    with tf.name_scope('smooth_l1', None, [bbox_pred, bbox_targets]):
        sigma2 = sigma * sigma

        inside_mul = tf.multiply(
            bbox_inside_weights, tf.subtract(bbox_pred, bbox_targets))

        smooth_l1_sign = tf.cast(
            tf.less(tf.abs(inside_mul), 1.0 / sigma2), tf.float32)
        smooth_l1_option1 = tf.multiply(
            tf.multiply(inside_mul, inside_mul), 0.5 * sigma2)
        smooth_l1_option2 = tf.subtract(tf.abs(inside_mul), 0.5 / sigma2)
        smooth_l1_result = tf.add(tf.multiply(smooth_l1_option1, smooth_l1_sign),
                                  tf.multiply(smooth_l1_option2, tf.abs(tf.subtract(smooth_l1_sign, 1.0))))

        outside_mul = tf.multiply(bbox_outside_weights, smooth_l1_result)

        return outside_mul


def select_bboxes(scores_pred, bboxes_pred, num_classes, select_threshold):
    selected_bboxes = {}
    selected_scores = {}
    with tf.name_scope('select_bboxes', None, [scores_pred, bboxes_pred]):
        for class_ind in range(1, num_classes):
            class_scores = scores_pred[:, class_ind]
            select_mask = class_scores > select_threshold

            select_mask = tf.cast(select_mask, tf.float32)
            selected_bboxes[class_ind] = tf.multiply(
                bboxes_pred, tf.expand_dims(select_mask, axis=-1))
            selected_scores[class_ind] = tf.multiply(class_scores, select_mask)

    return selected_bboxes, selected_scores


def clip_bboxes(ymin, xmin, ymax, xmax, name):
    with tf.name_scope(name, 'clip_bboxes', [ymin, xmin, ymax, xmax]):
        ymin = tf.maximum(ymin, 0.)
        xmin = tf.maximum(xmin, 0.)
        ymax = tf.minimum(ymax, 1.)
        xmax = tf.minimum(xmax, 1.)

        ymin = tf.minimum(ymin, ymax)
        xmin = tf.minimum(xmin, xmax)

        return ymin, xmin, ymax, xmax


def filter_bboxes(scores_pred, ymin, xmin, ymax, xmax, min_size, name):
    with tf.name_scope(name, 'filter_bboxes', [scores_pred, ymin, xmin, ymax, xmax]):
        width = xmax - xmin
        height = ymax - ymin

        filter_mask = tf.logical_and(width > min_size, height > min_size)

        filter_mask = tf.cast(filter_mask, tf.float32)
        return tf.multiply(ymin, filter_mask), tf.multiply(xmin, filter_mask), \
            tf.multiply(ymax, filter_mask), tf.multiply(
                xmax, filter_mask), tf.multiply(scores_pred, filter_mask)


def sort_bboxes(scores_pred, ymin, xmin, ymax, xmax, keep_topk, name):
    with tf.name_scope(name, 'sort_bboxes', [scores_pred, ymin, xmin, ymax, xmax]):
        cur_bboxes = tf.shape(scores_pred)[0]
        scores, idxes = tf.nn.top_k(scores_pred, k=tf.minimum(
            keep_topk, cur_bboxes), sorted=True)

        ymin, xmin, ymax, xmax = tf.gather(ymin, idxes), tf.gather(
            xmin, idxes), tf.gather(ymax, idxes), tf.gather(xmax, idxes)

        paddings_scores = tf.expand_dims(
            tf.stack([0, tf.maximum(keep_topk - cur_bboxes, 0)], axis=0), axis=0)

        return tf.pad(ymin, paddings_scores, "CONSTANT"), tf.pad(xmin, paddings_scores, "CONSTANT"),\
            tf.pad(ymax, paddings_scores, "CONSTANT"), tf.pad(xmax, paddings_scores, "CONSTANT"),\
            tf.pad(scores, paddings_scores, "CONSTANT")


def nms_bboxes(scores_pred, bboxes_pred, nms_topk, nms_threshold, name):
    with tf.name_scope(name, 'nms_bboxes', [scores_pred, bboxes_pred]):
        idxes = tf.image.non_max_suppression(
            bboxes_pred, scores_pred, nms_topk, nms_threshold)
        return tf.gather(scores_pred, idxes), tf.gather(bboxes_pred, idxes)


def parse_by_class(cls_pred, bboxes_pred, num_classes, select_threshold, min_size, keep_topk, nms_topk, nms_threshold):
    with tf.name_scope('select_bboxes', None, [cls_pred, bboxes_pred]):
        scores_pred = tf.nn.softmax(cls_pred)
        selected_bboxes, selected_scores = select_bboxes(
            scores_pred, bboxes_pred, num_classes, select_threshold)
        for class_ind in range(1, num_classes):
            ymin, xmin, ymax, xmax = tf.unstack(
                selected_bboxes[class_ind], 4, axis=-1)
            #ymin, xmin, ymax, xmax = tf.split(selected_bboxes[class_ind], 4, axis=-1)
            #ymin, xmin, ymax, xmax = tf.squeeze(ymin), tf.squeeze(xmin), tf.squeeze(ymax), tf.squeeze(xmax)
            ymin, xmin, ymax, xmax = clip_bboxes(
                ymin, xmin, ymax, xmax, 'clip_bboxes_{}'.format(class_ind))
            ymin, xmin, ymax, xmax, selected_scores[class_ind] = filter_bboxes(selected_scores[class_ind],
                                                                               ymin, xmin, ymax, xmax, min_size, 'filter_bboxes_{}'.format(class_ind))
            ymin, xmin, ymax, xmax, selected_scores[class_ind] = sort_bboxes(selected_scores[class_ind],
                                                                             ymin, xmin, ymax, xmax, keep_topk, 'sort_bboxes_{}'.format(class_ind))
            selected_bboxes[class_ind] = tf.stack(
                [ymin, xmin, ymax, xmax], axis=-1)
            selected_scores[class_ind], selected_bboxes[class_ind] = nms_bboxes(
                selected_scores[class_ind], selected_bboxes[class_ind], nms_topk, nms_threshold, 'nms_bboxes_{}'.format(class_ind))

        return selected_bboxes, selected_scores


def ssd_model_fn(features, labels, mode, params):
    """model_fn for SSD to be used with our Estimator."""
    filename = features['filename']
    shape = features['shape']
    loc_targets = features['loc_targets']
    cls_targets = features['cls_targets']
    match_scores = features['match_scores']
    features = features['image']

    global global_anchor_info
    decode_fn = global_anchor_info['decode_fn']
    num_anchors_per_layer = global_anchor_info['num_anchors_per_layer']
    all_num_anchors_depth = global_anchor_info['all_num_anchors_depth']

    with tf.variable_scope(params['model_scope'], default_name=None, values=[features], reuse=tf.AUTO_REUSE):
        backbone = ssd_net_low.VGG16Backbone(params["data_format"])
        feature_layers = backbone.forward(
            inputs=features,
            pw_conv1_2=FLAGS.pw_conv1_2,
            pa_conv1_2=FLAGS.pa_conv1_2,
            tw_conv1_2=FLAGS.tw_conv1_2,
            ta_conv1_2=FLAGS.ta_conv1_2,
            pw_conv2_1=FLAGS.pw_conv2_1,
            pa_conv2_1=FLAGS.pa_conv2_1,
            tw_conv2_1=FLAGS.tw_conv2_1,
            ta_conv2_1=FLAGS.ta_conv2_1,
            pw_conv2_2=FLAGS.pw_conv2_2,
            pa_conv2_2=FLAGS.pa_conv2_2,
            tw_conv2_2=FLAGS.tw_conv2_2,
            ta_conv2_2=FLAGS.ta_conv2_2,
            pw_conv3_1=FLAGS.pw_conv3_1,
            pa_conv3_1=FLAGS.pa_conv3_1,
            tw_conv3_1=FLAGS.tw_conv3_1,
            ta_conv3_1=FLAGS.ta_conv3_1,
            pw_conv3_2=FLAGS.pw_conv3_2,
            pa_conv3_2=FLAGS.pa_conv3_2,
            tw_conv3_2=FLAGS.tw_conv3_2,
            ta_conv3_2=FLAGS.ta_conv3_2,
            pw_conv3_3=FLAGS.pw_conv3_3,
            pa_conv3_3=FLAGS.pa_conv3_3,
            tw_conv3_3=FLAGS.tw_conv3_3,
            ta_conv3_3=FLAGS.ta_conv3_3,
            pw_conv4_1=FLAGS.pw_conv4_1,
            pa_conv4_1=FLAGS.pa_conv4_1,
            tw_conv4_1=FLAGS.tw_conv4_1,
            ta_conv4_1=FLAGS.ta_conv4_1,
            pw_conv4_2=FLAGS.pw_conv4_2,
            pa_conv4_2=FLAGS.pa_conv4_2,
            tw_conv4_2=FLAGS.tw_conv4_2,
            ta_conv4_2=FLAGS.ta_conv4_2,
            pw_conv4_3=FLAGS.pw_conv4_3,
            pa_conv4_3=FLAGS.pa_conv4_3,
            tw_conv4_3=FLAGS.tw_conv4_3,
            ta_conv4_3=FLAGS.ta_conv4_3,
            pw_conv5_1=FLAGS.pw_conv5_1,
            pa_conv5_1=FLAGS.pa_conv5_1,
            tw_conv5_1=FLAGS.tw_conv5_1,
            ta_conv5_1=FLAGS.ta_conv5_1,
            pw_conv5_2=FLAGS.pw_conv5_2,
            pa_conv5_2=FLAGS.pa_conv5_2,
            tw_conv5_2=FLAGS.tw_conv5_2,
            ta_conv5_2=FLAGS.ta_conv5_2,
            pw_conv5_3=FLAGS.pw_conv5_3,
            pa_conv5_3=FLAGS.pa_conv5_3,
            tw_conv5_3=FLAGS.tw_conv5_3,
            ta_conv5_3=FLAGS.ta_conv5_3,
            pw_fc6=FLAGS.pw_fc6,
            pa_fc6=FLAGS.pa_fc6,
            tw_fc6=FLAGS.tw_fc6,
            ta_fc6=FLAGS.ta_fc6,
            pw_fc7=FLAGS.pw_fc7,
            pa_fc7=FLAGS.pa_fc7,
            tw_fc7=FLAGS.tw_fc7,
            ta_fc7=FLAGS.ta_fc7,
            pw_conv8_1=FLAGS.pw_conv8_1,
            pa_conv8_1=FLAGS.pa_conv8_1,
            tw_conv8_1=FLAGS.tw_conv8_1,
            ta_conv8_1=FLAGS.ta_conv8_1,
            pw_conv8_2=FLAGS.pw_conv8_2,
            pa_conv8_2=FLAGS.pa_conv8_2,
            tw_conv8_2=FLAGS.tw_conv8_2,
            ta_conv8_2=FLAGS.ta_conv8_2,
            pw_conv9_1=FLAGS.pw_conv9_1,
            pa_conv9_1=FLAGS.pa_conv9_1,
            tw_conv9_1=FLAGS.tw_conv9_1,
            ta_conv9_1=FLAGS.ta_conv9_1,
            pw_conv9_2=FLAGS.pw_conv9_2,
            pa_conv9_2=FLAGS.pa_conv9_2,
            tw_conv9_2=FLAGS.tw_conv9_2,
            ta_conv9_2=FLAGS.ta_conv9_2,
            pw_conv10_1=FLAGS.pw_conv10_1,
            pa_conv10_1=FLAGS.pa_conv10_1,
            tw_conv10_1=FLAGS.tw_conv10_1,
            ta_conv10_1=FLAGS.ta_conv10_1,
            pw_conv10_2=FLAGS.pw_conv10_2,
            pa_conv10_2=FLAGS.pa_conv10_2,
            tw_conv10_2=FLAGS.tw_conv10_2,
            ta_conv10_2=FLAGS.ta_conv10_2,
            pw_conv11_1=FLAGS.pw_conv11_1,
            pa_conv11_1=FLAGS.pa_conv11_1,
            tw_conv11_1=FLAGS.tw_conv11_1,
            ta_conv11_1=FLAGS.ta_conv11_1,
            pw_conv11_2=FLAGS.pw_conv11_2,
            pa_conv11_2=FLAGS.pa_conv11_2,
            tw_conv11_2=FLAGS.tw_conv11_2,
            ta_conv11_2=FLAGS.ta_conv11_2,
            qw_en=FLAGS.qw_en,
            qa_en=FLAGS.qa_en,
            qw_bits=FLAGS.qw_bits,
            qa_bits=FLAGS.qa_bits,
            pw_en=FLAGS.pw_en,
            pa_en=FLAGS.pa_en,
            threshold_w=FLAGS.threshold_w,
            threshold_a=FLAGS.threshold_a,
            begin_pruning=FLAGS.begin_pruning_at_step,
            end_pruning=FLAGS.end_pruning_at_step,
            pruning_frequency=FLAGS.pruning_frequency,
            target_sparsity=FLAGS.target_sparsity,
            training=(mode == tf.estimator.ModeKeys.TRAIN),
        )
        location_pred, cls_pred = ssd_net_low.multibox_head(
            feature_layers, params['num_classes'], all_num_anchors_depth, data_format=params['data_format'])

        if params['data_format'] == 'channels_first':
            cls_pred = [tf.transpose(pred, [0, 2, 3, 1]) for pred in cls_pred]
            location_pred = [tf.transpose(pred, [0, 2, 3, 1])
                             for pred in location_pred]

        cls_pred = [tf.reshape(
            pred, [tf.shape(features)[0], -1, params['num_classes']]) for pred in cls_pred]
        location_pred = [tf.reshape(
            pred, [tf.shape(features)[0], -1, 4]) for pred in location_pred]

        cls_pred = tf.concat(cls_pred, axis=1)
        location_pred = tf.concat(location_pred, axis=1)

        cls_pred = tf.reshape(cls_pred, [-1, params['num_classes']])
        location_pred = tf.reshape(location_pred, [-1, 4])

    with tf.device('/cpu:0'):
        bboxes_pred = decode_fn(location_pred)
        bboxes_pred = tf.concat(bboxes_pred, axis=0)
        selected_bboxes, selected_scores = parse_by_class(cls_pred, bboxes_pred,
                                                          params['num_classes'], params['select_threshold'], params['min_size'],
                                                          params['keep_topk'], params['nms_topk'], params['nms_threshold'])

    predictions = {'filename': filename, 'shape': shape}
    for class_ind in range(1, params['num_classes']):
        predictions['scores_{}'.format(class_ind)] = tf.expand_dims(
            selected_scores[class_ind], axis=0)
        predictions['bboxes_{}'.format(class_ind)] = tf.expand_dims(
            selected_bboxes[class_ind], axis=0)

    flaten_cls_targets = tf.reshape(cls_targets, [-1])
    flaten_match_scores = tf.reshape(match_scores, [-1])
    flaten_loc_targets = tf.reshape(loc_targets, [-1, 4])

    # each positive examples has one label
    positive_mask = flaten_cls_targets > 0
    n_positives = tf.count_nonzero(positive_mask)

    batch_n_positives = tf.count_nonzero(cls_targets, -1)

    # tf.logical_and(tf.equal(cls_targets, 0), match_scores > 0.)
    batch_negtive_mask = tf.equal(cls_targets, 0)
    batch_n_negtives = tf.count_nonzero(batch_negtive_mask, -1)

    batch_n_neg_select = tf.cast(
        params['negative_ratio'] * tf.cast(batch_n_positives, tf.float32), tf.int32)
    batch_n_neg_select = tf.minimum(
        batch_n_neg_select, tf.cast(batch_n_negtives, tf.int32))

    # hard negative mining for classification
    predictions_for_bg = tf.nn.softmax(tf.reshape(
        cls_pred, [tf.shape(features)[0], -1, params['num_classes']]))[:, :, 0]
    prob_for_negtives = tf.where(batch_negtive_mask,
                                 0. - predictions_for_bg,
                                 # ignore all the positives
                                 0. - tf.ones_like(predictions_for_bg))
    topk_prob_for_bg, _ = tf.nn.top_k(
        prob_for_negtives, k=tf.shape(prob_for_negtives)[1])
    score_at_k = tf.gather_nd(topk_prob_for_bg, tf.stack(
        [tf.range(tf.shape(features)[0]), batch_n_neg_select - 1], axis=-1))

    selected_neg_mask = prob_for_negtives >= tf.expand_dims(
        score_at_k, axis=-1)

    # include both selected negtive and all positive examples
    final_mask = tf.stop_gradient(tf.logical_or(tf.reshape(tf.logical_and(
        batch_negtive_mask, selected_neg_mask), [-1]), positive_mask))
    total_examples = tf.count_nonzero(final_mask)

    cls_pred = tf.boolean_mask(cls_pred, final_mask)
    location_pred = tf.boolean_mask(
        location_pred, tf.stop_gradient(positive_mask))
    flaten_cls_targets = tf.boolean_mask(tf.clip_by_value(
        flaten_cls_targets, 0, params['num_classes'] - 1), final_mask)
    flaten_loc_targets = tf.stop_gradient(
        tf.boolean_mask(flaten_loc_targets, positive_mask))

    # Calculate loss, which includes softmax cross entropy and L2 regularization.
    #cross_entropy = (params['negative_ratio'] + 1.) * tf.cond(n_positives > 0, lambda: tf.losses.sparse_softmax_cross_entropy(labels=glabels, logits=cls_pred), lambda: 0.)
    cross_entropy = tf.losses.sparse_softmax_cross_entropy(
        labels=flaten_cls_targets, logits=cls_pred) * (params['negative_ratio'] + 1.)
    # Create a tensor named cross_entropy for logging purposes.
    tf.identity(cross_entropy, name='cross_entropy_loss')
    tf.summary.scalar('cross_entropy_loss', cross_entropy)

    #loc_loss = tf.cond(n_positives > 0, lambda: modified_smooth_l1(location_pred, tf.stop_gradient(flaten_loc_targets), sigma=1.), lambda: tf.zeros_like(location_pred))
    loc_loss = modified_smooth_l1(location_pred, flaten_loc_targets, sigma=1.)
    loc_loss = tf.reduce_mean(tf.reduce_sum(
        loc_loss, axis=-1), name='location_loss')
    tf.summary.scalar('location_loss', loc_loss)
    tf.losses.add_loss(loc_loss)

    # Add weight decay to the loss. We exclude the batch norm variables because
    # doing so leads to a small improvement in accuracy.
    total_loss = tf.add(cross_entropy, loc_loss, name='total_loss')

    cls_accuracy = tf.metrics.accuracy(
        flaten_cls_targets, tf.argmax(cls_pred, axis=-1))

    # Create a tensor named train_accuracy for logging purposes.
    tf.identity(cls_accuracy[1], name='cls_accuracy')
    tf.summary.scalar('cls_accuracy', cls_accuracy[1])

    summary_hook = tf.train.SummarySaverHook(save_steps=params['save_summary_steps'],
                                             output_dir=params['summary_dir'],
                                             summary_op=tf.summary.merge_all())
    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(
            mode=mode,
            predictions=predictions,
            prediction_hooks=[summary_hook],
            loss=None, train_op=None)
    else:
        raise ValueError('This script only support "PREDICT" mode!')


def parse_comma_list(args):
    return [float(s.strip()) for s in args.split(',')]


def main(_):

    if FLAGS.specify_gpu != None:
        os.environ['CUDA_VISIBLE_DEVICES'] = FLAGS.specify_gpu
    # Using the Winograd non-fused algorithms provides a small performance boost.
    os.environ['TF_ENABLE_WINOGRAD_NONFUSED'] = '1'

    gpu_options = tf.GPUOptions(
        per_process_gpu_memory_fraction=FLAGS.gpu_memory_fraction)
    config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False, intra_op_parallelism_threads=FLAGS.num_cpu_threads,
                            inter_op_parallelism_threads=FLAGS.num_cpu_threads, gpu_options=gpu_options)

    # Set up a RunConfig to only save checkpoints once per training cycle.
    run_config = tf.estimator.RunConfig().replace(
        save_checkpoints_secs=None).replace(
        save_checkpoints_steps=None).replace(
        save_summary_steps=FLAGS.save_summary_steps).replace(
        keep_checkpoint_max=5).replace(
        log_step_count_steps=FLAGS.log_every_n_steps).replace(
        session_config=config)

    summary_dir = os.path.join(FLAGS.model_dir, 'predict')
    ssd_detector = tf.estimator.Estimator(
        model_fn=ssd_model_fn, model_dir=FLAGS.model_dir, config=run_config,
        params={
            'select_threshold': FLAGS.select_threshold,
            'min_size': FLAGS.min_size,
            'nms_threshold': FLAGS.nms_threshold,
            'nms_topk': FLAGS.nms_topk,
            'keep_topk': FLAGS.keep_topk,
            'data_format': FLAGS.data_format,
            'batch_size': FLAGS.batch_size,
            'model_scope': FLAGS.model_scope,
            'save_summary_steps': FLAGS.save_summary_steps,
            'summary_dir': summary_dir,
            'num_classes': FLAGS.num_classes,
            'negative_ratio': FLAGS.negative_ratio,
            'match_threshold': FLAGS.match_threshold,
            'neg_threshold': FLAGS.neg_threshold,
            'weight_decay': FLAGS.weight_decay,
        })
    tensors_to_log = {
        'ce': 'cross_entropy_loss',
        'loc': 'location_loss',
        'loss': 'total_loss',
        'acc': 'cls_accuracy',
    }
    logging_hook = tf.train.LoggingTensorHook(tensors=tensors_to_log, every_n_iter=FLAGS.log_every_n_steps,
                                              formatter=lambda dicts: (', '.join(['%s=%.6f' % (k, v) for k, v in dicts.items()])))

    print('Starting a predict cycle.')
    pred_results = ssd_detector.predict(input_fn=input_pipeline(dataset_pattern='val-*', is_training=False, batch_size=FLAGS.batch_size),
                                        hooks=[logging_hook], checkpoint_path=get_checkpoint())  # , yield_single_examples=False)
    det_results = list(pred_results)
    # print(list(det_results))

    #[{'bboxes_1': array([[0.        , 0.        , 0.28459054, 0.5679505 ], [0.3158835 , 0.34792888, 0.7312541 , 1.        ]], dtype=float32), 'scores_17': array([0.01333667, 0.01152573], dtype=float32), 'filename': b'000703.jpg', 'shape': array([334, 500,   3])}]

    ## Create new file write for the correct format output##
    for class_ind in range(1, FLAGS.num_classes):
        with open(os.path.join(summary_dir, 'results_{}.txt'.format(class_ind)), 'wt') as f:
            for image_ind, pred in enumerate(det_results):
                filename = pred['filename']
                shape = pred['shape']
                scores = pred['scores_{}'.format(class_ind)]
                bboxes = pred['bboxes_{}'.format(class_ind)]
                bboxes[:, 0] = (bboxes[:, 0] * shape[0]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 1] = (bboxes[:, 1] * shape[1]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 2] = (bboxes[:, 2] * shape[0]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 3] = (bboxes[:, 3] * shape[1]
                                ).astype(np.int32, copy=False) + 1

                valid_mask = np.logical_and(
                    (bboxes[:, 2] - bboxes[:, 0] > 0), (bboxes[:, 3] - bboxes[:, 1] > 0))

                for det_ind in range(valid_mask.shape[0]):
                    if not valid_mask[det_ind]:
                        continue
                    f.write('{:s} {:.3f} {:.1f} {:.1f} {:.1f} {:.1f}\n'.
                            format(filename.decode('utf8')[:-4], scores[det_ind],
                                   bboxes[det_ind, 1], bboxes[det_ind, 0],
                                   bboxes[det_ind, 3], bboxes[det_ind, 2]))

    with open(os.path.join(summary_dir, 'results_complete.txt'), 'wt') as file:
        file.write('Vision Type, Detection Algorithm, Frame, Detection Class, Detection Probability, left, top, right, bottom, adj left, adj top, adj right, adj bottom, volume\n')
        for image_ind, pred in enumerate(det_results):
            for class_ind in range(1, FLAGS.num_classes):
                for cls_name, cls_pair in dataset_common.VOC_LABELS_reduced.items():
                    if cls_pair[0] == class_ind:
                        class_name = cls_name
                scores = pred['scores_{}'.format(class_ind)]
                bboxes = pred['bboxes_{}'.format(class_ind)]
                filename = pred['filename']
                shape = pred['shape']
                bboxes[:, 0] = (bboxes[:, 0] * shape[0]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 1] = (bboxes[:, 1] * shape[1]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 2] = (bboxes[:, 2] * shape[0]
                                ).astype(np.int32, copy=False) + 1
                bboxes[:, 3] = (bboxes[:, 3] * shape[1]
                                ).astype(np.int32, copy=False) + 1
                valid_mask = np.logical_and(
                    (bboxes[:, 2] - bboxes[:, 0] > 0), (bboxes[:, 3] - bboxes[:, 1] > 0))
                for det_ind in range(valid_mask.shape[0]):
                    if (not (valid_mask[det_ind] and scores[det_ind] < 0.5)):
                        continue
                    file.write(' , ssd300, {:s}, {}, {:.3f}, {:.1f}, {:.1f}, {:.1f}, {:.1f}, , , , , {:0f}\n'.
                               format(filename.decode('utf8'), class_name, scores[det_ind],
                                      bboxes[det_ind, 1], bboxes[det_ind,
                                                                 0], bboxes[det_ind, 3], bboxes[det_ind, 2],
                                      (bboxes[det_ind, 3] - bboxes[det_ind, 1]) * (bboxes[det_ind, 2] - bboxes[det_ind, 0])))


if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run()