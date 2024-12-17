// Utility Functions

/**
 * Switch between tabs on the page.
 * @param {string} pageId - The ID of the page to display.
 */
 function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => page.classList.remove("active"));
    document.getElementById(pageId)?.classList.add("active");
    document.querySelectorAll("nav button").forEach(btn => btn.classList.remove("active"));
    document.querySelector(`nav button[onclick="showPage('${pageId}')"]`)?.classList.add("active");
}

/**
 * Display a message in the chatbox.
 * @param {string} message - The message content.
 * @param {string} className - The class name for the message (e.g., 'user' or 'bot').
 * @param {boolean} prepend - Whether to prepend the message to the chatbox.
 * @returns {HTMLElement} The created message element.
 */
function addChatMessage(message, className, prepend = false) {
    const chatMessages = document.getElementById("chatMessages");
    const messageElement = document.createElement("div");
    messageElement.className = `message ${className}`;
    messageElement.textContent = message;
    if (prepend) {
        chatMessages.prepend(messageElement);
    } else {
        chatMessages.appendChild(messageElement);
    }
    return messageElement;
}

/**
 * Clear content within a container.
 * @param {HTMLElement} container - The container to clear.
 */
function clearContainer(container) {
    container.innerHTML = "";
}

// Initialize Chatbox Content
document.addEventListener("DOMContentLoaded", () => {
    initializeChat();
    initializeFileList();
});

/**
 * Initialize chat messages and sample questions.
 */
function initializeChat() {
    const chatMessages = document.getElementById("chatMessages");
    const sampleQuestions = document.getElementById("sampleQuestions");

    if (!chatMessages?.hasChildNodes()) {
        addChatMessage("Hi! I'm LyleBot. How may I help you?", "bot");
        ["Who is Lyle?"].forEach(question => createSampleQuestion(sampleQuestions, question));
    }
}

/**
 * Create and append sample question buttons.
 * @param {HTMLElement} container - The container for sample questions.
 * @param {string} question - The question text.
 */
function createSampleQuestion(container, question) {
    const button = document.createElement("button");
    button.textContent = question;
    button.className = "sample-question";
    button.addEventListener("click", () => handleSampleQuestion(button, question));
    container.appendChild(button);
}

/**
 * Handle sample question clicks.
 * @param {HTMLElement} button - The clicked button element.
 * @param {string} question - The question text.
 */
async function handleSampleQuestion(button, question) {
    button.classList.add("fade-out");
    setTimeout(() => button.remove(), 500);
    document.getElementById("userInput").value = question;
    document.getElementById("chatForm")?.dispatchEvent(new Event("submit"));
}

/**
 * Fetch API responses with JSON body.
 * @param {string} endpoint - API endpoint.
 * @param {object} data - Request body.
 * @returns {object} - Parsed JSON response.
 */
async function fetchAPI(endpoint, data) {
    const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error("Network response error");
    return response.json();
}

// Chat Form Submission
document.getElementById("chatForm")?.addEventListener("submit", handleChatSubmit);
async function handleChatSubmit(e) {
    e.preventDefault();
    const userInput = document.getElementById("userInput");
    addChatMessage(userInput.value, "user");
    const botMessage = addChatMessage("", "bot", false);
    try {
        const result = await fetchAPI("http://localhost:5000/chat/", { query: userInput.value });
        userInput.value = "";
        botMessage.innerHTML = marked.parse(result.response);
        if (result.sources?.length) renderPDFSource(result.sources[0]);
    } catch (error) {
        botMessage.innerHTML = "<p>Error fetching response.</p>";
    }
}

/**
 * Render PDF document in a container.
 * @param {object} source - Document source.
 */
 async function renderPDFSource(source) {
    const pdfViewer = document.getElementById("pdfViewer");
    clearContainer(pdfViewer);

    // Use fetch directly with GET method
    const response = await fetch(`http://localhost:5000/download/${source.doc_id}`);
    if (!response.ok) {
        throw new Error("Failed to fetch PDF download URL");
    }
    const download = await response.json();

    const iframe = document.createElement("iframe");
    iframe.src = download.download_url;
    iframe.style.cssText = "width: 100%; height: 600px; border: none;";
    pdfViewer.appendChild(iframe);
}


/**
 * Initialize the uploaded file list.
 */
async function initializeFileList() {
    const uploadStatus = document.getElementById("uploadStatus");
    const fileList = document.getElementById("fileList");
    try {
        const response = await fetch("http://localhost:5000/list_uploaded_files/");
        const result = await response.json();
        if (response.ok && result.files.length > 0) {
            result.files.forEach(file => renderFileItem(fileList, file));
        } else {
            uploadStatus.innerHTML = "<p>No files uploaded yet.</p>";
        }
    } catch (error) {
        uploadStatus.innerHTML = "<p>Error loading files.</p>";
    }
}

/**
 * Render a single file item in the list.
 * @param {HTMLElement} container - The file list container.
 * @param {object} file - File metadata.
 */
function renderFileItem(container, file) {
    const fileItem = document.createElement("div");
    fileItem.className = "file-item";
    fileItem.innerHTML = `<img src="pdf-icon.png" alt="${file.filename}">
                          <span class="file-name">${file.filename}</span>
                          <span class="file-size">120 KB</span>`;
    const deleteButton = document.createElement("button");
    deleteButton.textContent = "X";
    deleteButton.className = "delete-button";
    deleteButton.addEventListener("click", () => confirmDeleteFile(file.doc_id, fileItem));
    fileItem.appendChild(deleteButton);
    container.appendChild(fileItem);
}

/**
 * Confirm and delete a file.
 * @param {string} docId - Document ID.
 * @param {HTMLElement} fileItem - The file's DOM element.
 */
async function confirmDeleteFile(docId, fileItem) {
    if (confirm("Are you sure you want to delete this file?")) {
        const response = await fetch(`http://localhost:5000/delete/${docId}`, { method: "DELETE" });
        if (response.ok) fileItem.remove();
    }
}
