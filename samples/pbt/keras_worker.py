#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import schedy
import keras
from keras.datasets import mnist
from keras.models import Model
from keras.layers import Input, Dense, Dropout, Flatten, Conv2D, MaxPooling2D
import keras.backend as K
import tensorflow as tf
import os
import argparse

cfg = tf.ConfigProto()
cfg.gpu_options.allow_growth = True
K.set_session(tf.Session(config=cfg))

IMG_SIZE = 28
NUM_CLASSES = 10

def make_model(job):
    inputs = Input(shape=x_train.shape[1:])
    inner = inputs
    # Conv2D layers w/o any pooling in between, or any residual connection,
    # this is a bad network but it exists just for the sake of the experiment
    for layer_idx in range(job.hyperparameters['num_layers']):
        inner = Conv2D(
            job.hyperparameters['num_filters'],
            kernel_size=job.hyperparameters['kernel_size'],
            activation=job.hyperparameters['activations'],
            padding='same'
        )(inner)
        inner = Dropout(job.hyperparameters['dropout_rate'])(inner)
    inner = Flatten()(inner)
    outputs = Dense(NUM_CLASSES, activation='softmax')(inner)
    model = Model(inputs=inputs, outputs=outputs)
    model.compile(
        optimizer=keras.optimizers.SGD(job.hyperparameters['learning_rate']),
        loss=keras.losses.categorical_crossentropy,
        metrics=['accuracy'],
    )
    # Reload the weights if we are resuming from previous work
    weights_path = job.results.get('weights_path')
    if weights_path:
        model.load_weights(weights_path)
        print('Reloaded weights from ' + weights_path)
    return model

def main(args):
    # Get experiment data
    db = schedy.SchedyDB()
    experiment = db.get_experiment(args.experiment)
    # Create the directory that will contain the models
    try:
        os.makedirs(args.models_dir)
    except FileExistsError:
        pass
    # Load the training/test data
    (x_train, y_train), (x_test, y_test) = mnist.load_data()
    x_train = x_train.reshape(x_train.shape[0], IMG_SIZE, IMG_SIZE, 1).astype(K.floatx()) / 255.
    x_test = x_test.reshape(x_test.shape[0], IMG_SIZE, IMG_SIZE, 1).astype(K.floatx()) / 255.
    y_train = keras.utils.to_categorical(y_train, NUM_CLASSES)
    y_test = keras.utils.to_categorical(y_test, NUM_CLASSES)
    # Process one job
    with experiment.next_job() as job:
        # Create and train the model for one epoch
        model = make_model(job)
        model.fit(x_train, y_train, batch_size=256)
        loss, accuracy = model.evaluate(x_test, y_test, batch_size=256)
        # Update the results
        job.results.setdefault('loss', []).append(loss)
        job.results.setdefault('accuracy', []).append(accuracy)
        job.results['min_loss'] = min(job.results['loss'])
        job.results['max_accuracy'] = max(job.results['accuracy'])
        # Do not forget to save the weights, as the next job that will need to
        # load these
        weights_path = os.path.join(args.models_dir, job.job_id + '.h5')
        job.results['weights_path'] = weights_path
        model.save_weights(weights_path)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', default='MNIST with PBT')
    parser.add_argument('--models-dir', default='models', help='Path to the directory in which the models are saved.')
    args = parser.parse_args()
    main(args)

