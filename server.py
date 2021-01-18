import base64
import os
import sys
from io import BytesIO
from typing import Optional, Any

import numpy as np
from PIL import Image
from flask import Flask, request, render_template, send_from_directory
from flask.wrappers import Response

import model

app = Flask(__name__)


@app.route("/")
def index() -> Any:
    """
    Returns the rendered template in HTML format of the main page of the website
    for the GET request along the path "/" or "index.html".

    Returns
    -------
    Any
        HTML page: index.html.

    """
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon() -> Any:
    """
    Returns the site icon for the GET request along the path "/favicon.ico".

    Returns
    -------
    Any
        Site icon: favicon.ico.

    """
    return send_from_directory(os.path.join(app.root_path, "static"),
                               "favicon.ico", mimetype="image/png")


def prepare_input(image) -> Optional[np.ndarray]:
    """
    Prepares the file (image) to be sent for segmentation.

    Parameters
    ----------
    image
        Image file.

    Returns
    -------
    Optional[numpy.ndarray]
        Converted image in multidimensional array format
        or None if an error occurred.

    """
    try:
        array = np.array(Image.open(image))
        if len(array.shape) != 3 or (array.shape[2] != 3):
            return None
        return array
    except Exception as e:
        print(e, file=sys.stderr)
        return None


def prepare_output(image: np.ndarray) -> str:
    """
    Prepares the image for sending to the client
    by converting it to text format.

    Parameters
    ----------
    image : numpy.ndarray
        The mask image is the result of segmentation.

    Returns
    -------
    str
        Base64 encoded image in PNG format.

    """
    response_image = Image.fromarray(np.uint8(image * 255))
    buffer = BytesIO()
    response_image.save(buffer, "PNG")
    encoded = base64.b64encode(buffer.getvalue())
    return "data:image/png;base64," + str(encoded)[2:-1]


@app.route("/predict", methods=["POST"])
def predict() -> Any:
    """
    Processes a POST request for image segmentation and processes
    it based on the received request parameters.

    Returns
    -------
    Any
        A dictionary containing a set of key-value elements:
        - the key is the name of the file;
        - the value is None if an error occurred during processing of this image,
          or the result of segmentation is a mask.

    """
    threshold = request.form.get("threshold", type=float)
    source_size = request.form.get("source_size", type=bool)
    images = request.files.getlist("images")
    result = {}
    for image in images:
        input_image = prepare_input(image)
        if input_image is not None:
            output_image = model.predict(input_image, threshold, source_size)
            if output_image is not None:
                result[image.filename] = prepare_output(output_image)
            else:
                result[image.filename] = None
        else:
            result[image.filename] = None
    return result


@app.after_request
def after_request(response: Response) -> Response:
    """
    The function is executed after each request and allows the client access to resources.

    Parameters
    ----------
    response : Response
        HTTP response.

    Returns
    -------
    Response
        HTTP response with added headers.

    """
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,PUT,POST,DELETE")
    return response


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)
