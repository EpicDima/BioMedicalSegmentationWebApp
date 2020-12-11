import base64
import os
import sys
from io import BytesIO
from typing import Optional

import numpy as np
from PIL import Image
from flask import Flask, request, render_template, send_from_directory

import model

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, "static"),
                               "favicon.ico", mimetype="image/png")


def prepare_input_image(image) -> Optional[np.ndarray]:
    try:
        array = np.array(Image.open(image))
        if len(array.shape) != 3 or (array.shape[2] != 3):
            return None
        return array
    except Exception as e:
        print(e, file=sys.stderr)
        return None


def prepare_output_image(image) -> str:
    response_image = Image.fromarray(np.uint8(image * 255))
    buffer = BytesIO()
    response_image.save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue())
    return "data:image/png;base64," + str(encoded)[2:-1]


@app.route("/predict", methods=["POST"])
def predict():
    threshold = request.form.get("threshold", type=float)
    source_size = request.form.get("source_size", type=bool)
    images = request.files.getlist("images")
    result = {}
    for image in images:
        input_image = prepare_input_image(image)
        if input_image is not None:
            output_image = model.predict(input_image, threshold, source_size)
            if output_image is not None:
                result[image.filename] = prepare_output_image(output_image)
            else:
                result[image.filename] = None
        else:
            result[image.filename] = None
    return result


@app.after_request
def after_request(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE")
    return response


if __name__ == "__main__":
    app.run()
