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
        typewriterEffect(initialMessage, "Hi! I'm LyleBot. How may I help you?", 50);

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

    addChatMessage(userInput.value, "user"); // Add user's message
    const botMessage = addChatMessage("", "bot"); // Add empty bot message for response

    try {
        const response = await fetch("http://localhost:5000/chat/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ query: userInput.value }),
        });

        const result = await response.json();
        userInput.value = ""; // Clear input field

        // Display bot response with typewriter effect
        typewriterEffect(botMessage, result.response, 15);

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
        botMessage.textContent = "Error fetching response.";
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
    e.preventDefault();
    
    const companyName = document.getElementById("companyName").value;
    const jobDescription = document.getElementById("jobDescription").value;
    const emailPreview = document.getElementById("emailPreview");
    const sendEmailButton = document.getElementById("sendEmailButton");
    
    // Show loading message
    emailPreview.innerHTML = "<p>Generating email content...</p>";
    
    try {
        const response = await fetch("http://localhost:5000/generate_email/", {
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
        const emailContent = result.emailContent;

        // Display email preview
        emailPreview.innerHTML = `
            <h2>Email Preview</h2>
            <p><strong>Subject:</strong> Application for the position at ${companyName}</p>
            <p><strong>Body:</strong></p>
            <pre>${emailContent}</pre>
        `;
        
        // Show the send email button
        sendEmailButton.style.display = "block";
    } catch (error) {
        console.error("Error generating email:", error);
        emailPreview.innerHTML = "<p>Error generating email. Please try again.</p>";
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

document.getElementById("uploadForm").addEventListener("submit", async function (e) {
    e.preventDefault(); // Prevent the form from submitting the usual way
    
    const fileInput = document.getElementById("fileInput");
    const file = fileInput.files[0]; // Get the file selected by the user
    const formData = new FormData();
    formData.append("file", file); // Add the file to the FormData object

    // Get the upload status container
    const uploadStatus = document.getElementById("uploadStatus");

    try {
        // Send the file to the backend using fetch
        const response = await fetch("http://localhost:5000/upload/", {
            method: "POST",
            body: formData // Send FormData as the body
        });

        // Parse the response from the backend
        const result = await response.json();
        
        if (response.ok) {
            // If successful, display a success message
            uploadStatus.innerHTML = `<p>File uploaded successfully! Document ID: ${result.doc_id}</p>`;
        } else {
            // If there's an error, display an error message
            uploadStatus.innerHTML = `<p>Error: ${result.message}</p>`;
        }
    } catch (error) {
        // Handle network errors or other issues
        console.error("Error uploading file:", error);
        uploadStatus.innerHTML = "<p>Error uploading file. Please try again.</p>";
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
                const fileItem = document.createElement("a");
                fileItem.href = `http://localhost:5000/download/${file.doc_id}`;
                fileItem.target = "_blank";
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

                fileItem.appendChild(fileIcon);
                fileItem.appendChild(fileName);
                fileItem.appendChild(fileSize);
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
