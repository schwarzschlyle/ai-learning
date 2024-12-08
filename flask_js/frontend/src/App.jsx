import { useState, useEffect } from 'react';
import './App.css';

const ContactForm = ({ existingContact = {}, updateCallback }) => {
  const [firstName, setFirstName] = useState(existingContact.firstName || '');
  const [lastName, setLastName] = useState(existingContact.lastName || '');
  const [email, setEmail] = useState(existingContact.email || '');

  const updating = Object.entries(existingContact).length !== 0;

  const onSubmit = async (e) => {
    e.preventDefault();

    const data = {
      firstName,
      lastName,
      email,
    };

    const url =
      'http://127.0.0.1:5000/' +
      (updating ? `update_contact/${existingContact.id}` : 'create_contact');

    const options = {
      method: updating ? 'PATCH' : 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    };
    const response = await fetch(url, options);

    if (response.status !== 201 && response.status !== 200) {
      const errorData = await response.json();
      alert(errorData.message);
    } else {
      updateCallback();
    }
  };

  return (
    <form onSubmit={onSubmit}>
      <div>
        <label htmlFor="firstName">First Name:</label>
        <input
          type="text"
          id="firstName"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="lastName">Last Name:</label>
        <input
          type="text"
          id="lastName"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="email">Email:</label>
        <input
          type="text"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button type="submit">{updating ? 'Update' : 'Create'}</button>
    </form>
  );
};

const ContactList = ({ contacts, updateContact, updateCallback }) => {
  const onDelete = async (id) => {
    try {
      const options = { method: 'DELETE' };
      const response = await fetch(
        `http://127.0.0.1:5000/delete_contact/${id}`,
        options
      );

      if (response.status === 200) {
        updateCallback();
      } else {
        console.error('Failed to delete contact.');
      }
    } catch (error) {
      alert(`Error occurred: ${error.message}`);
    }
  };

  return (
    <div>
      <h2>Contacts</h2>
      <table>
        <thead>
          <tr>
            <th>First Name</th>
            <th>Last Name</th>
            <th>Email</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr key={contact.id}>
              <td>{contact.firstName}</td>
              <td>{contact.lastName}</td>
              <td>{contact.email}</td>
              <td>
                <button onClick={() => updateContact(contact)}>Update</button>
                <button onClick={() => onDelete(contact.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

function App() {
  const [contacts, setContacts] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentContact, setCurrentContact] = useState({});
  const [generatedEmail, setGeneratedEmail] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  const [currentPage, setCurrentPage] = useState(1);
  const recordsPerPage = 10;

  useEffect(() => {
    fetchContacts();
    fetchLogs();

    const logInterval = setInterval(fetchLogs, 2000);
    return () => clearInterval(logInterval);
  }, []);

  const fetchContacts = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/contacts');
      const data = await response.json();
      setContacts(data.contacts);
      setIsLoading(false);
    } catch (error) {
      console.error('Failed to fetch contacts:', error);
    }
  };

  const fetchLogs = async () => {
    try {
      const response = await fetch('http://127.0.0.1:5000/logs');
      const data = await response.json();
      setLogs(data.logs);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    }
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setCurrentContact({});
  };

  const openCreateModal = () => setIsModalOpen(true);

  const openEditModal = (contact) => {
    setCurrentContact(contact);
    setIsModalOpen(true);
  };

  const onUpdate = () => {
    closeModal();
    fetchContacts();
  };

  const generateEmail = async () => {
    const query = prompt('Who do you want to email?');
    const purpose = prompt('What is your email about?');
    if (!query || !purpose) return;

    try {
      const response = await fetch('http://127.0.0.1:5000/generate_email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      console.error('Error generating email:', error);
    }
  };

  const indexOfLastRecord = currentPage * recordsPerPage;
  const indexOfFirstRecord = indexOfLastRecord - recordsPerPage;
  const currentRecords = contacts.slice(indexOfFirstRecord, indexOfLastRecord);
  const totalPages = Math.ceil(contacts.length / recordsPerPage);

  const handleNextPage = () => {
    if (currentPage < totalPages) setCurrentPage(currentPage + 1);
  };

  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage(currentPage - 1);
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

          <ContactList
            contacts={currentRecords}
            updateContact={openEditModal}
            updateCallback={onUpdate}
          />

          <div className="actions">
            <button onClick={openCreateModal}>Create New Contact</button>
            <button onClick={generateEmail}>Generate Email</button>
          </div>

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
        </div>
      )}

<div className="log-terminal">
  <div className="log-container">
    {logs.length > 0 ? logs[logs.length - 1] : 'No logs available'}
  </div>
</div>

    </>
  );
}

export default App;
