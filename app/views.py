# Author: Pieter Lewyllie, pilewyll@cisco.com
#!/usr/bin/env python

# Copyright The IETF Trust 2019, All Rights Reserved
# Copyright (c) 2015-2018 Cisco and/or its affiliates.

# This software is licensed to you under the terms of the Apache License, Version 2.0 (the "License").
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
# The code, technical concepts, and all information contained herein, are the property of Cisco Technology, Inc.
# and/or its affiliated entities, under various laws including copyright, international treaties, patent,
# and/or contract. Any use of the material herein must be in accordance with the terms of the License.
# All rights not expressly granted by the License are reserved.
# Unless required by applicable law or agreed to separately in writing, software distributed under the
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied.

__author__ = 'Pieter Lewyllie'
__copyright__ = 'Copyright 2018 Cisco and its affiliates, Copyright The IETF Trust 2019, All Rights Reserved'
__license__ = 'Apache License, Version 2.0'
__email__ = 'pilewyll@cisco.com'

import os
import subprocess
import sys
import uuid

import config  # pyright: ignore
from flask import Blueprint, jsonify, make_response, render_template, request

bp = Blueprint('yangre_v1', __name__, static_folder='static', template_folder='templates')


def _run(args: list):
    # python 3.5 dependency. To get stdout as a string we need the universal_newlines=True parameter
    # in python 3.6 this changes to encoding='utf8'
    if sys.version_info < (3, 5, 0):
        try:
            output = subprocess.check_output(
                args,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
            result = 0
        except subprocess.CalledProcessError as err:
            result = err.returncode
            output = err.output
    else:
        input_obj = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True)
        result = input_obj.returncode
        output = input_obj.stdout
    return result, output


@bp.route('', methods=['GET'])
def swagger():
    """ Renders the SWAGGER API UI """
    return render_template('swagger.html')


@bp.route('/w3c', methods=['GET', 'POST'])
def w3c():
    """ JSON API to validate W3C input """
    req_data = request.get_json()  # pyright: ignore

    # writing the test string to file, as required by w3cgrep
    w3cinput_filename = '/tmp/w3c_input' + str(uuid.uuid4())
    with open(w3cinput_filename, 'w', encoding='utf-8') as testfile:
        testfile.write(req_data['content'])
        testfile.write('\n')
        testfile.flush()
        os.fsync(testfile.fileno())

    result, output = _run([config.W3CGREP_PATH, str(req_data['pattern']), w3cinput_filename])
    if not output:
        w3c_input_result = 1
    else:
        w3c_input_result = 0

    if req_data['inverted'] == 'true':
        w3c_input_result = int(not w3c_input_result)

    if result == 1:
        w3c_input_result = -1  # I used -1 as error code

    # clean up files
    try:
        os.remove(w3cinput_filename)
    except FileNotFoundError:
        print('Oops, file not found')

    return make_response(jsonify({
        'pattern_nb': req_data['pattern_nb'],
        'w3cgrep_result': w3c_input_result,
        'w3cgrep_output': output
    }), 200)


@bp.route('/yangre', methods=['POST'])
def yangre():
    """ JSON API to validate YANG input """
    req_data = request.get_json()  # pyright: ignore

    # writing the test string to another file for yangre
    yangreinput_filename = '/tmp/yangre_input' + str(uuid.uuid4())
    with open(yangreinput_filename, 'w', encoding='utf-8') as yangrefile:
        yangrefile.write(str(req_data['pattern']))
        yangrefile.write('\n\n')
        yangrefile.write(str(req_data['content']))
        yangrefile.flush()
        os.fsync(yangrefile.fileno())

    yangre_command = [config.YANGGRE_PATH, '-f', yangreinput_filename]
    if req_data.get('inverted') == 'true':
        yangre_command.append('-i')
    yangre_result, yangre_output = _run(yangre_command)

    # clean up files
    try:
        os.remove(yangreinput_filename)
    except FileNotFoundError:
        print('Oops, file not found')

    return make_response(jsonify({
        'pattern_nb': req_data['pattern_nb'],
        'yangre_result': yangre_result,
        'yangre_output': yangre_output
    }), 200)


@bp.route('/ping', methods=['GET'])
def ping():
    return make_response(jsonify({'info': 'Success'}), 200)
