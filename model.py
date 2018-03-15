from __future__ import print_function
import file_utility
import midi_utility
import utility
import model
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from mido import MidiFile
from sklearn.cross_validation import train_test_split
from keras.preprocessing import sequence
from keras.models import Sequential, load_model
from keras.layers import LSTM, Bidirectional
from keras.optimizers import Adam


def batch_generator(xs, ys, batch_size):
    '''Generates a batch of samples for training or validation.'''
    i = 0
    while True:
        index1 = (i * batch_size) % len(xs)
        index2 = min(index1 + batch_size, len(xs))
        x, y = xs[index1:index2], ys[index1:index2]
        x = sequence.pad_sequences(x, dtype='float32', padding='post')
        y = sequence.pad_sequences(y, dtype='float32', padding='post')
        yield (x, y)


number_of_notes = 88
input_size = number_of_notes * 2  # 88 notes * 2 states (pressed, sustained).
output_size = number_of_notes  # 88 notes.


def create_model(x_train, y_train, x_test, y_test, batch_size, epochs, model_path, save_model=False):
    print('Setting up model ...')

    dropout = 0.2  # Drop 20% of units for linear transformation of inputs.

    model = Sequential()
    model.add(Bidirectional(LSTM(output_size, activation='relu', return_sequences=True, dropout=dropout),
                            merge_mode='sum',
                            input_shape=(None, input_size),
                            batch_input_shape=(batch_size, None, input_size)))
    model.add(Bidirectional(LSTM(output_size, activation='relu',
                                 return_sequences=True, dropout=dropout), merge_mode='sum'))
    model.add(Bidirectional(LSTM(output_size, activation='tanh',
                                 return_sequences=True, dropout=dropout), merge_mode='sum'))
    model.compile(loss='mse', optimizer=Adam(
        lr=0.001, clipnorm=10), metrics=['mse'])

    print(model.summary())

    print('Training model ...')

    number_of_train_batches = np.ceil(len(x_train)/float(batch_size))
    model.fit_generator(batch_generator(x_train, y_train, batch_size),
                        steps_per_epoch=number_of_train_batches,
                        epochs=epochs)

    padded_x_test = sequence.pad_sequences(
        x_test, dtype='float32', padding='post')
    padded_y_test = sequence.pad_sequences(
        y_test, dtype='float32', padding='post')

    if save_model:
        print('Saving model ...')
        model.save(model_path)

    number_of_test_batches = np.ceil(len(padded_x_test)/float(batch_size))
    loss_and_metrics = model.evaluate_generator(batch_generator(padded_x_test,
                                                                padded_y_test,
                                                                batch_size),
                                                steps=number_of_test_batches)
    print('Loss and metrics:', loss_and_metrics)

    return model


def predict(path, batch_size):
    print('Predicting ...')

    prediction_data = np.load(path)

    # Copy prediction input N times to create a batch of the right size.
    tiled = np.tile(prediction_data, [batch_size, 1, 1])

    raw_prediction = model.predict(tiled, batch_size=batch_size)[0]
    prediction = (raw_prediction * 127).astype(int)  # Float -> MIDI velocity.

    print('Highest predicted velocity:', np.max(prediction))
    print('Lowest predicted velocity:', np.min(prediction))

    return prediction
