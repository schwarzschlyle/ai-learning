import { useState, useEffect } from 'react';
import ContactList from './ContactList';
import './App.css';
import ContactForm from './ContactForm';

function App() {
  const [contacts, setContacts] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentContact, setCurrentContact] = useState({});
  const [generatedEmail, setGeneratedEmail] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const recordsPerPage = 10;

  useEffect(() => {
    fetchContacts();
    fetchLogs();
    const interval = setInterval(fetchLogs, 2000);
    return () => clearInterval(interval);
  }, []);

  const fetchContacts = async () => {
    const response = await fetch('http://127.0.0.1:5000/contacts');
    const data = await response.json();
    setContacts(data.contacts);
    setIsLoading(false);
  };

  const fetchLogs = async () => {
    const response = await fetch('http://127.0.0.1:5000/logs');
    const data = await response.json();
    setLogs(data.logs);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setCurrentContact({});
  };

  const openCreateModal = () => {
    if (!isModalOpen) setIsModalOpen(true);
  };

  const openEditModal = (contact) => {
    if (isModalOpen) return;
    setCurrentContact(contact);
    setIsModalOpen(true);
  };

  const onUpdate = () => {
    closeModal();
    fetchContacts();
  };

  const generateEmail = async () => {
    const query = prompt('Who do you want to email');
    const purpose = prompt('What is your email about?');
    if (!query || !purpose) return;

    try {
      const response = await fetch('http://127.0.0.1:5000/generate_email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query, purpose }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        alert(`Error: ${errorData.detail}`);
        return;
      }

      const data = await response.json();
      setGeneratedEmail({
        contact: data.contact,
        emailContent: data.emailContent,
      });
      fetchLogs();
    } catch (error) {
      alert('Failed to generate email. Please try again.');
      console.error(error);
    }
  };

  // Pagination Logic
  const indexOfLastRecord = currentPage * recordsPerPage;
  const indexOfFirstRecord = indexOfLastRecord - recordsPerPage;
  const currentRecords = contacts.slice(indexOfFirstRecord, indexOfLastRecord);

  const totalPages = Math.ceil(contacts.length / recordsPerPage);

  const handleNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  return (
    <>
      {isLoading && (
        <div className="loading-screen">
          <h2>Loading...</h2>
          <div className="loader"></div>
        </div>
      )}

      {!isLoading && (
        <div className="container">
          <ContactList
            contacts={currentRecords}
            updateContact={openEditModal}
            updateCallback={onUpdate}
          />
          <button onClick={openCreateModal}>Create New Contact</button>
          <button onClick={generateEmail}>Generate Email</button>

          {isModalOpen && (
            <div className="modal">
              <div className="modal-content">
                <span className="close" onClick={closeModal}>
                  &times;
                </span>
                <ContactForm
                  existingContact={currentContact}
                  updateCallback={onUpdate}
                />
              </div>
            </div>
          )}

          {generatedEmail && (
            <div className="generated-email">
              <h2>
                Generated Email for {generatedEmail.contact.firstName}{' '}
                {generatedEmail.contact.lastName}
              </h2>
              <p>Email: {generatedEmail.contact.email}</p>
              <pre>{generatedEmail.emailContent}</pre>
            </div>
          )}

          {/* Pagination Controls */}
          <div className="pagination">
            <button
              onClick={handlePrevPage}
              disabled={currentPage === 1}
              className="pagination-btn"
            >
              Previous
            </button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={handleNextPage}
              disabled={currentPage === totalPages}
              className="pagination-btn"
            >
              Next
            </button>
          </div>
        </div>
      )}

      <div className="log-terminal">
        <h3>Logs</h3>
        <div className="log-container">
          {logs.map((log, index) => (
            <pre key={index}>{log}</pre>
          ))}
        </div>
      </div>
    </>
  );
}

export default App;
