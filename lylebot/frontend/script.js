
// Utility Functions

/**
 * Switch between tabs on the page.
 * @param {string} pageId - The ID of the page to display.
 */
 function showPage(pageId) {
    document.querySelectorAll(".page").forEach(page => page.classList.remove("active"));
    document.getElementById(pageId).classList.add("active");
    document.querySelectorAll("nav button").forEach(btn => btn.classList.remove("active"));
    document.querySelector(`nav button[onclick="showPage('${pageId}')"]`).classList.add("active");
}

/**
 * Display a message in the chatbox.
 * @param {string} message - The message content.
 * @param {string} className - The class name for the message (e.g., 'user' or 'bot').
 * @returns {HTMLElement} The created message element (if needed for updates).
 */
function addChatMessage(message, className) {
    const chatMessages = document.getElementById("chatMessages");
    const messageElement = document.createElement("div");
    messageElement.className = `message ${className}`;
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);
    return messageElement;
}

/**
 * Typewriter effect for a message.
 * @param {HTMLElement} element - The element to display the text in.
 * @param {string} text - The text to display with the typewriter effect.
 * @param {number} interval - The delay in milliseconds between each character.
 */
function typewriterEffect(element, text, interval) {
    let i = 0;
    const typeInterval = setInterval(() => {
        element.textContent += text.charAt(i);
        i++;
        if (i === text.length) {
            clearInterval(typeInterval);
        }
    }, interval);
}


/**
 * Clear elements in a container.
 * @param {HTMLElement} container - The container to clear.
 */
function clearContainer(container) {
    container.innerHTML = "";
}

// Add Initial Message and Sample Questions
document.addEventListener("DOMContentLoaded", () => {
    const chatMessages = document.getElementById("chatMessages");
    const sampleQuestions = document.getElementById("sampleQuestions");

    if (chatMessages && !chatMessages.hasChildNodes()) {
        // Add initial message with typewriter effect
        const initialMessage = addChatMessage("", "bot");
        typewriterEffect(initialMessage, "Hi! I'm LyleBot. How may I help you?", 15);

        // Add sample questions
        const questions = [
            "Who is Lyle?",
        ];
        questions.forEach((question) => {
            const questionButton = document.createElement("button");
            questionButton.textContent = question;
            questionButton.className = "sample-question";
            questionButton.addEventListener("click", () => handleSampleQuestion(questionButton, question));
            sampleQuestions.appendChild(questionButton);
        });
    }
});

// Handle Sample Question Click
async function handleSampleQuestion(button, question) {
    // Add fade-out effect
    button.classList.add("fade-out");

    // Remove button after the fade effect
    setTimeout(() => {
        button.remove();
    }, 500); // Match the fade-out duration

    // Populate the input field with the question and trigger chat
    const userInput = document.getElementById("userInput");
    userInput.value = question; // Populate the input field with the sample question
    document.getElementById("chatForm").dispatchEvent(new Event("submit")); // Trigger form submission
}

// Chat functionality
document.getElementById("chatForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const userInput = document.getElementById("userInput");
    const chatMessages = document.getElementById("chatMessages");
    const pdfViewer = document.getElementById("pdfViewer");

    // Add user's message
    addChatMessage(userInput.value, "user");

    // Add empty bot message placeholder (Markdown rendering enabled)
    const botMessage = addChatMessage("", "bot", true);

    try {
        const response = await fetch("http://localhost:5000/chat/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query: userInput.value }),
        });

        const result = await response.json();
        userInput.value = ""; // Clear input field

        // Populate bot message with Markdown
        botMessage.innerHTML = marked.parse(result.response);


        // Handle referenced sources (render PDF if applicable)
        if (result.sources && result.sources.length > 0) {
            const primarySource = result.sources[0];

            // Fetch the primary source's download URL
            const downloadResponse = await fetch(`http://localhost:5000/download/${primarySource.doc_id}`);
            const downloadResult = await downloadResponse.json();

            // Render the PDF
            renderPDF(downloadResult.download_url, pdfViewer);
        }
    } catch (error) {
        botMessage.innerHTML = "<p>Error fetching response.</p>";
        console.error("Chat Error:", error);
    }
});


/**
 * Render a PDF in an iframe.
 * Clears previous content in the container before rendering the new PDF.
 * @param {string} url - The URL of the PDF to render.
 * @param {HTMLElement} container - The container to render the PDF in.
 */
 function renderPDF(url, container) {
    // Clear previous content in the container
    clearContainer(container);

    // Create and append the iframe for the new PDF
    const iframe = document.createElement("iframe");
    iframe.src = url;
    iframe.width = "100%";
    iframe.height = "600px";
    iframe.style.border = "none";
    container.appendChild(iframe);
}





document.getElementById("reachOutForm").addEventListener("submit", async (e) => {
    e.preventDefault(); // Prevent default form submission

    const companyName = document.getElementById("companyName").value.trim();
    const jobDescription = document.getElementById("jobDescription").value.trim();
    const emailPreview = document.getElementById("emailPreview");
    const sendEmailButton = document.getElementById("sendEmailButton");

    // Clear previous content and show a loading message
    emailPreview.innerHTML = "<p>Generating email content...</p>";
    sendEmailButton.style.display = "none";

    try {
        const response = await fetch("http://localhost:5000/generate_email/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ companyName, jobDescription }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        const emailContent = result.emailContent;

        // Render the email preview
        emailPreview.innerHTML = `
            <h2>Email Preview</h2>
            <p><strong>Subject:</strong> ${emailContent.split("\n")[0]}</p>
            <p><strong>Body:</strong></p>
            <div class="email-body">${emailContent.replace(/\n/g, "<br>")}</div>
        `;

        // Show the "Send Email" button
        sendEmailButton.style.display = "block";
    } catch (error) {
        emailPreview.innerHTML = "<p>Error generating email. Please try again later.</p>";
        console.error("Error generating email:", error);
    }
});







// Send the generated email to Lyle's email address
async function sendEmail() {
    const companyName = document.getElementById("companyName").value;
    const jobDescription = document.getElementById("jobDescription").value;
    
    try {
        const response = await fetch("http://localhost:5000/send_email/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                companyName: companyName,
                jobDescription: jobDescription,
            }),
        });

        const result = await response.json();
        if (result.status === "success") {
            alert("Email sent successfully!");
        } else {
            alert("Failed to send email. Please try again.");
        }
    } catch (error) {
        console.error("Error sending email:", error);
        alert("Error sending email. Please try again.");
    }
}

document.getElementById("uploadForm")?.addEventListener("submit", async function (e) {
    e.preventDefault(); // Prevent default behavior

    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("http://localhost:5000/upload/", {
            method: "POST",
            body: formData,
        });

        if (response.ok) {
            const result = await response.json();
            document.getElementById("uploadStatus").innerHTML = `<p>File uploaded successfully! Document ID: ${result.doc_id}</p>`;
        } else {
            const error = await response.json();
            document.getElementById("uploadStatus").innerHTML = `<p>Error: ${error.message}</p>`;
        }
    } catch (error) {
        console.error("Error uploading file:", error);
        document.getElementById("uploadStatus").innerHTML = "<p>Error uploading file. Please try again.</p>";
    }
});


document.addEventListener("DOMContentLoaded", async () => {
    const uploadStatus = document.getElementById("uploadStatus");

    try {
        // Fetch the list of uploaded files from the backend
        const response = await fetch("http://localhost:5000/list_uploaded_files/");
        const result = await response.json();

        // Display the files in a grid
        if (response.ok && result.files.length > 0) {
            const fileList = document.getElementById("fileList");

            result.files.forEach(file => {
                const fileItem = document.createElement("div");
                fileItem.className = "file-item";

                const fileIcon = document.createElement("img");
                fileIcon.src = "pdf-icon.png"; // Replace with the path to your PDF icon image
                fileIcon.alt = file.filename;

                const fileName = document.createElement("span");
                fileName.textContent = file.filename;
                fileName.className = "file-name";

                const fileSize = document.createElement("span");
                fileSize.textContent = "120 KB"; // Mock file size; update dynamically if available
                fileSize.className = "file-size";

                const deleteButton = document.createElement("button");
                deleteButton.textContent = "X";
                deleteButton.className = "delete-button";
                deleteButton.addEventListener("click", async () => {
                    const confirmDelete = confirm(`Are you sure you want to delete "${file.filename}"?`);
                    if (confirmDelete) {
                        await deleteFile(file.doc_id, fileItem);
                    }
                });

                fileItem.appendChild(fileIcon);
                fileItem.appendChild(fileName);
                fileItem.appendChild(fileSize);
                fileItem.appendChild(deleteButton);
                fileList.appendChild(fileItem);
            });
        } else {
            uploadStatus.innerHTML = "<p>No files uploaded yet.</p>";
        }
    } catch (error) {
        console.error("Error fetching uploaded files:", error);
        uploadStatus.innerHTML = "<p>Error loading uploaded files. Please try again later.</p>";
    }
});

async function deleteFile(docId, fileItem) {
    try {
        const response = await fetch(`http://localhost:5000/delete/${docId}`, {
            method: "DELETE",
        });

        if (response.ok) {
            alert("File deleted successfully.");
            fileItem.remove(); // Remove the file item from the UI
        } else {
            const result = await response.json();
            alert(`Error deleting file: ${result.detail}`);
        }
    } catch (error) {
        console.error("Error deleting file:", error);
        alert("An error occurred while deleting the file. Please try again.");
    }
}



const dragAndDropZone = document.getElementById("dragAndDropZone");
const fileInput = document.getElementById("fileInput");
const fileList = document.getElementById("fileList");

dragAndDropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dragAndDropZone.classList.add("dragging");
});

dragAndDropZone.addEventListener("dragleave", () => {
    dragAndDropZone.classList.remove("dragging");
});

dragAndDropZone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dragAndDropZone.classList.remove("dragging");

    const files = Array.from(e.dataTransfer.files);
    await processFiles(files);
});

fileInput.addEventListener("change", async () => {
    const files = Array.from(fileInput.files);
    await processFiles(files);
});

async function processFiles(files) {
    for (const file of files) {
        if (file.type === "application/pdf") {
            try {
                const formData = new FormData();
                formData.append("file", file);

                const response = await fetch("http://localhost:5000/upload/", {
                    method: "POST",
                    body: formData,
                });

                if (response.ok) {
                    const result = await response.json();
                    displayFile(file, result.doc_id);
                } else {
                    const error = await response.json();
                    console.error("Upload failed:", error.detail);
                }
            } catch (error) {
                console.error("Error uploading file:", error);
            }
        } else {
            alert("Only PDF files are allowed.");
        }
    }
}

function displayFile(file, docId) {
    const fileItem = document.createElement("div");
    fileItem.classList.add("file-item");

    const fileName = document.createElement("span");
    fileName.textContent = file.name;

    const deleteButton = document.createElement("button");
    deleteButton.textContent = "Delete";
    deleteButton.classList.add("delete-button");
    deleteButton.addEventListener("click", async () => {
        try {
            const response = await fetch(`http://localhost:5000/delete/${docId}`, {
                method: "DELETE",
            });
            if (response.ok) {
                fileItem.remove();
            } else {
                console.error("Failed to delete file.");
            }
        } catch (error) {
            console.error("Error deleting file:", error);
        }
    });

    

    fileItem.appendChild(fileName);
    fileItem.appendChild(deleteButton);
    fileList.appendChild(fileItem);
}






