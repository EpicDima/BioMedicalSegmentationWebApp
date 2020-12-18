const MAX_IMAGES = 50;

const uploadButton = document.getElementById("upload-button");
const imagesInput = document.getElementById("images-input");
const thresholdLabel = document.getElementById("threshold-label");
const thresholdInput = document.getElementById("threshold-input");
const thresholdCheckbox = document.getElementById("threshold-checkbox");
const sourceSizeLabel = document.getElementById("source-size-label");
const sourceSizeCheckbox = document.getElementById("source-size-checkbox");

const imagePart = document.getElementById("image-part");
const imageContainer = document.getElementById("image-container");

const resultPart = document.getElementById("result-part");
const resultContainer = document.getElementById("result-container");
const downloadAllButton = document.getElementById("download-all");

const imagesCount = document.getElementById("image-part-title-count");

const sendButton = document.getElementById("send-button");
const sendStatus = document.getElementById("send-status");

const modal = document.getElementById("image-modal");
const modalImage = document.getElementById("image-modal-content");

let sending = false;

setup();

function setup() {
    // Initial setup of some parameters.

    document.getElementById("images-input").value = "";
    document.getElementById("threshold-checkbox").checked = true;
    setupImageContainerVisibilityButton();
    setupResultContainerVisibilityButton();
    downloadAllButton.onclick = () => {
        const cards = new Array(...resultContainer.childNodes).reverse();
        for (const card of cards) {
            const downloadButton = card.querySelector("button");
            if (downloadButton) {
                downloadButton.click();
            }
        }
    };
    checkSendButtonState();
    setupModal();
}

function setupImageContainerVisibilityButton() {
    // Setting parameters for the visibility button of the container with the original images.

    setupVisibilityButton(document.getElementById("image-container-visibility-button"), imageContainer);
}

function setupResultContainerVisibilityButton() {
    // Setting parameters for the visibility button of the container with the resulting images.

    setupVisibilityButton(document.getElementById("result-container-visibility-button"), resultContainer);
}

function setupVisibilityButton(button, container) {
    // Setting parameters for the visibility button of the container.

    button.innerText = "Скрыть";
    button.onclick = () => {
        if (container.classList.contains("hide")) {
            container.classList.remove("hide");
            button.innerText = "Скрыть";
        } else {
            container.classList.add("hide");
            button.innerText = "Развернуть";
        }
    };
}

function setupModal() {
    // Setting modal window parameters.

    modal.querySelector(".close").onclick = () => {
        modal.classList.add("hide");
        modalImage.src = "";
    };
}

function resetImageContainer() {
    // Resetting the container with the original images.

    imageContainer.innerHTML = "";
    imageContainer.classList.remove("hide");
    setupImageContainerVisibilityButton();
}

function resetResultContainer() {
    // Resetting the container with the resulting images.

    resultContainer.innerHTML = "";
    resultContainer.classList.remove("hide");
    setupResultContainerVisibilityButton();
}

function getImagesFromInput() {
    // Getting images from the input field.

    if (imagesInput.files && imagesInput.files.length > 0) {
        const files = [];
        let count = 0;
        for (const file of imagesInput.files) {
            if (file.type.startsWith("image/")) {
                files.push(file);
                count++;
                if (count === MAX_IMAGES) {
                    break;
                }
            }
        }
        return files;
    }
    return null;
}


function readImagesAndShow() {
    // Getting images from the input field and displaying them on the screen.

    const files = getImagesFromInput();
    if (files && files.length > 0) {
        sendStatus.innerText = "";
        sendStatus.classList.remove("error");
        downloadAllButton.classList.add("hide");
        resultContainer.innerHTML = "";
        resetImageContainer();
        imagePart.classList.remove("hide");
        resultPart.classList.add("hide");
        for (const file of files) {
            if (file.type.startsWith("image/")) {
                const reader = new FileReader();
                reader.onload = (e) => {
                    imageContainer.append(createImageCard(file.name, e.target.result, "input", false));
                }
                reader.readAsDataURL(file);
            }
        }
        imagesCount.innerText = `(${files.length})`;
    } else {
        alert("Выберите хотя бы одно изображение");
    }
    checkSendButtonState();
}

async function sendImages() {
    // Sending user-selected images for processing, receiving results and displaying them.

    if (imagesInput.files && imagesInput.files.length > 0) {
        sending = true;
        imagesInput.disabled = true;
        uploadButton.classList.add("hide");
        sendButton.disabled = true;
        sendStatus.innerText = "Отправка";
        sendStatus.classList.remove("error");
        resultPart.classList.add("hide");
        const startTime = new Date();
        const response = await fetch("/predict", {
            method: "POST",
            body: prepareFormData()
        }).catch(() => null);
        if (response && response.ok) {
            const data = await response.json();
            sendStatus.innerText = `Затраченное время (мс): ${new Date() - startTime}`;
            resetResultContainer();
            resultPart.classList.remove("hide");
            let notNullResult = false;
            for (const key in data) {
                const result = data[key];
                if (result !== null) {
                    notNullResult = true;
                }
                const card = createImageCard(key, result, "result", true);
                resultContainer.append(card);
            }
            if (notNullResult) {
                downloadAllButton.classList.remove("hide");
            }
        } else {
            sendStatus.classList.add("error");
            sendStatus.innerText = "Неизвестная ошибка отправки";
        }
        sending = false;
        imagesInput.disabled = false;
        uploadButton.classList.remove("hide");
        sendButton.disabled = false;
    }
}

function prepareFormData() {
    // Prepare request parameters for segmentation.

    downloadAllButton.classList.add("hide");
    resultContainer.innerHTML = "";
    const formData = new FormData();
    if (thresholdCheckbox.checked) {
        if (thresholdInput.validity.valid) {
            formData.append("threshold", thresholdInput.value);
        }
    }
    if (sourceSizeCheckbox.checked) {
        formData.append("source_size", "true");
    }
    const files = getImagesFromInput();
    for (const file of files) {
        if (file.type.startsWith("image/")) {
            formData.append("images", file);
        }
    }
    return formData;
}

function createImageCard(filename, imageData, qualifier, needButton) {
    // Creating a DOM element with an image for the container.

    const card = document.createElement("div");
    const cardId = `${qualifier}-${filename}`;
    card.id = cardId;
    card.className = "card";
    if (imageData === null) {
        const error = document.createElement("div");
        error.className = "error";
        card.classList.add("error");
        error.innerText = "Ошибка обработки";
        card.append(error);
    } else {
        const image = document.createElement("div");
        image.className = "image";
        image.style.backgroundImage = `url(${imageData})`;
        card.append(image);
        card.onclick = () => {
            modal.classList.remove("hide");
            modalImage.src = imageData;
        }
        card.classList.add("clicked");
    }
    const title = document.createElement("div");
    title.className = "title";
    title.innerText = filename;
    card.append(title);
    if (imageData !== null && needButton) {
        const downloadButton = document.createElement("button");
        downloadButton.className = "download-button";
        downloadButton.innerText = "Скачать";
        downloadButton.onclick = (e) => {
            e.stopPropagation();
            const a = document.createElement("a");
            a.download = cardId;
            a.href = imageData;
            a.click();
        };
        card.append(downloadButton);
    }
    return card;
}

function onThresholdSwitchChange() {
    // Changing the visibility of the threshold value input field
    // when switching the switch.

    thresholdInput.disabled = !thresholdCheckbox.checked;
    if (thresholdCheckbox.checked) {
        thresholdLabel.classList.remove("disabled");
    } else {
        thresholdLabel.classList.add("disabled");
    }
    checkSendButtonState();
}

function onSourceSizeSwitchChange() {
    // Changing the visibility of the source size value input
    // field when switching the switch.

    if (sourceSizeCheckbox.checked) {
        sourceSizeLabel.classList.remove("disabled");
    } else {
        sourceSizeLabel.classList.add("disabled");
    }
}

function checkSendButtonState() {
    // Toggles the state of the send button and the file selection button
    // when you enter different values in the input fields.

    let disabled = false;
    if (thresholdCheckbox.checked) {
        if (!thresholdInput.validity.valid) {
            disabled = true;
        }
    }
    const files = getImagesFromInput();
    if (files === null || files.length === 0) {
        disabled = true;
    }
    if (sending) {
        disabled = true;
    }
    sendButton.disabled = disabled;
}
