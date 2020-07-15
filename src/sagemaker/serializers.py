# Copyright 2017-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Implements methods for serializing data for an inference endpoint."""
from __future__ import absolute_import

import abc
import csv
import io
import json

import numpy as np


class BaseSerializer(abc.ABC):
    """Abstract base class for creation of new serializers.

    Provides a skeleton for customization requiring the overriding of the method
    serialize and the class attribute CONTENT_TYPE.
    """

    @abc.abstractmethod
    def serialize(self, data):
        """Serialize data into the media type specified by CONTENT_TYPE.

        Args:
            data (object): Data to be serialized.

        Returns:
            object: Serialized data used for a request.
        """

    @property
    @abc.abstractmethod
    def CONTENT_TYPE(self):
        """The MIME type of the data sent to the inference endpoint."""


class CSVSerializer(BaseSerializer):
    """Searilize data of various formats to a CSV-formatted string."""

    CONTENT_TYPE = "text/csv"

    def serialize(self, data):
        """Serialize data of various formats to a CSV-formatted string.

        Args:
            data (object): Data to be serialized. Can be a NumPy array, list,
                file, or buffer.

        Returns:
            str: The data serialized as a CSV-formatted string.
        """
        if hasattr(data, "read"):
            return data.read()

        is_mutable_sequence_like = self._is_sequence_like(data) and hasattr(data, "__setitem__")
        has_multiple_rows = len(data) > 0 and self._is_sequence_like(data[0])

        if is_mutable_sequence_like and has_multiple_rows:
            return "\n".join([self._serialize_row(row) for row in data])

        return self._serialize_row(data)

    def _serialize_row(self, data):
        """Serialize data as a CSV-formatted row.

        Args:
            data (object): Data to be serialized in a row.

        Returns:
            str: The data serialized as a CSV-formatted row.
        """
        if isinstance(data, str):
            return data

        if isinstance(data, np.ndarray):
            data = np.ndarray.flatten(data)

        if hasattr(data, "__len__"):
            if len(data) == 0:
                raise ValueError("Cannot serialize empty array")
            csv_buffer = io.StringIO()
            csv_writer = csv.writer(csv_buffer, delimiter=",")
            csv_writer.writerow(data)
            return csv_buffer.getvalue().rstrip("\r\n")

        raise ValueError("Unable to handle input format: ", type(data))

    def _is_sequence_like(self, data):
        """Returns true if obj is iterable and subscriptable."""
        return hasattr(data, "__iter__") and hasattr(data, "__getitem__")


class NumpySerializer(BaseSerializer):
    """Serialize data to a buffer using the .npy format."""

    CONTENT_TYPE = "application/x-npy"

    def __init__(self, dtype=None):
        """Initialize the dtype.

        Args:
            dtype (str): The dtype of the data.
        """
        self.dtype = dtype

    def serialize(self, data):
        """Serialize data to a buffer using the .npy format.

        Args:
            data (object): Data to be serialized. Can be a NumPy array, list,
                file, or buffer.

        Returns:
            io.BytesIO: A buffer containing data serialzied in the .npy format.
        """
        if isinstance(data, np.ndarray):
            if data.size == 0:
                raise ValueError("Cannot serialize empty array.")
            return self._serialize_array(data)

        if isinstance(data, list):
            if len(data) == 0:
                raise ValueError("Cannot serialize empty array.")
            return self._serialize_array(np.array(data, self.dtype))

        # files and buffers. Assumed to hold npy-formatted data.
        if hasattr(data, "read"):
            return data.read()

        return self._serialize_array(np.array(data))

    def _serialize_array(self, array):
        """Saves a NumPy array in a buffer.

        Args:
            array (numpy.ndarray): The array to serialize.

        Returns:
            io.BytesIO: A buffer containing the serialized array.
        """
        buffer = io.BytesIO()
        np.save(buffer, array)
        return buffer.getvalue()


class JSONSerializer(BaseSerializer):
    """Serialize data to a JSON formatted string."""

    CONTENT_TYPE = "application/json"

    def serialize(self, data):
        """Serialize data of various formats to a JSON formatted string.

        Args:
            data (object): Data to be serialized.

        Returns:
            str: The data serialized as a JSON string.
        """
        if isinstance(data, dict):
            return json.dumps(
                {
                    key: value.tolist() if isinstance(value, np.ndarray) else value
                    for key, value in data.items()
                }
            )

        if hasattr(data, "read"):
            return data.read()

        if isinstance(data, np.ndarray):
            return json.dumps(data.tolist())

        return json.dumps(data)
