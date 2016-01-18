from application import app
from flask import Response, request
import json
import logging
import traceback
from jsonschema import Draft4Validator
import random


name_schema = {
    "type": "object",
    "properties": {
        "forenames": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "surname": {"type": "string"}
    },
    "required": ["forenames", "surname"]
}

address_schema = {
    "type": "object",
    "properties": {
        "address_lines": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "county": {"type": "string"},
        "postcode": {"type": "string"}
    },
    "required": ["address_lines", "postcode", "county"]
}

date_schema = {
    "type": "string",
    "pattern": "^([0-9]{4}-[0-9]{2}-[0-9]{2})$"
}

full_schema = {
    "type": "object",
    "properties": {
        "key_number": {
            "type": "string",
            "pattern": "^\d+$"
        },
        "application_type": {
            "type": "string",
            "enum": ["PA(B)", "WO(B)"]
        },
        "application_ref": {"type": "string"},
        "application_date": date_schema,
        "debtor_names": {
            "type": "array",
            "minItems": 1,
            "items": name_schema
        },
        "gender": {"type": "string"},
        "occupation": {"type": "string"},
        "trading_name": {"type": "string"},
        "residence": {
            "type": "array",
            "items": address_schema
        },
        "residence_withheld": {"type": "boolean"},
        "business_address": {
            "type": "array",
            "items": address_schema
        },
        "date_of_birth": date_schema,
        "investment_property": {
            "type": "array",
            "items": address_schema
        }
    },
    "required": ["key_number", "application_type", "application_ref", "application_date", "debtor_names",
                 "residence_withheld"]
}


@app.route('/', methods=["GET"])
def index():
    return Response(status=200)


@app.route('/health', methods=['GET'])
def health():
    result = {
        'status': 'OK',
        'dependencies': {}
    }

    status = 200
    return Response(json.dumps(result), status=status, mimetype='application/json')


@app.errorhandler(Exception)
def error_handler(err):
    logging.error('Unhandled exception: ' + str(err))
    call_stack = traceback.format_exc()

    lines = call_stack.split("\n")
    for line in lines:
        logging.error(line)

    return Response(status=500)


@app.before_request
def before_request():
    logging.info("BEGIN %s %s [%s] (%s)",
                 request.method, request.url, request.remote_addr, request.__hash__())


@app.after_request
def after_request(response):
    logging.info('END %s %s [%s] (%s) -- %s',
                 request.method, request.url, request.remote_addr, request.__hash__(),
                 response.status)
    return response


@app.route('/bankruptcies', methods=["POST"])
def register():
    if request.headers['Content-Type'] != "application/json":
        return Response(status=415)  # 415 (Unsupported Media Type)

    json_data = request.get_json(force=True)
    logging.info("Received: " + json.dumps(json_data))
    val = Draft4Validator(full_schema)
    errors = []
    for error in val.iter_errors(json_data):
        # Should be able to express the error location using JSONPath:
        path = "$"
        while len(error.path) > 0:
            item = error.path.popleft()
            if isinstance(item, int):  # This is an assumption!
                path += "[" + str(item) + "]"
            else:
                path += "." + item
        if path == '$':
            path = '$.'
        errors.append({
            "location": path,
            "error_message": error.message
        })

    if 'residence_withheld' in json_data and \
            json_data['residence_withheld'] is False \
            and not json_data['residence']:
        message = "'residence' is a required property when 'address_withheld' is false"
        errors.append({
            'location': '',
            'error_message': message
        })

    if 'residence_withheld' in json_data and json_data['residence_withheld'] is True \
            and 'residence' in json_data and len(json_data['residence']) > 0:
        errors.append({
            'location': '',
            'error_message': "'residence' may not be supplied when 'address_withheld' is true"
        })

    if len(errors) > 0:
        data = {
            'errors': errors,
        }
        if 'application_ref' in json_data:
            data['application_ref'] = json_data['application_ref']
        else:
            data['application_ref'] = ''
        resp_text = json.dumps(data)
        logging.info('Responding with errors: ' + resp_text)
        return Response(resp_text, status=400, mimetype='application/json')

    response = {
        "application_ref": json_data['application_ref'],
        "application_type": json_data['application_type'],
        "new_registrations": []
    }

    number = random.randrange(1000, 999999)
    for name in json_data['debtor_names']:
        response['new_registrations'].append({
            "date": json_data['application_date'],
            "number": number,
            "forenames": name['forenames'],
            "surname": name['surname']
        })
        number += 1

    resp_text = json.dumps(response)
    logging.info("response is: " + resp_text)
    return Response(resp_text, status=201, mimetype='application/json')


