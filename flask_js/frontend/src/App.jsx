// import { useState, useEffect } from 'react'
// import ContactList from './ContactList'
// import './App.css'
// import ContactForm from './ContactForm'


// function App() {
//   const [contacts, setContacts] = useState([]);
//   const [ isModalOpen, setIsModalOpen ] = useState(false)
//   const [currentContact, setCurrentContact] = useState({})


//   useEffect(() => {
//     fetchContacts()
    
//   }, [])



//   const fetchContacts = async () => {
//     const response = await fetch("http://127.0.0.1:5000/contacts")
//     const data = await response.json()
//     setContacts(data.contacts)
//     console.log(data.contacts)


//   }


//   const closeModal = () => {
//     setIsModalOpen(false)
//     setCurrentContact({})
//   }

//   const openCreateModal = () => {
//     if (!isModalOpen) setIsModalOpen(true)
//   }


//   const openEditModal = (contact) => {
//     if (isModalOpen) return
//     setCurrentContact(contact)
//     setIsModalOpen(true)

//   }

//   const onUpdate = () => {
//     closeModal()
//     fetchContacts()
//   }

//   return (<>
//   <ContactList contacts = {contacts} updateContact={openEditModal} updateCallback={onUpdate} />
//   <button onClick={openCreateModal}> Create New Contact </button>
//   { isModalOpen && <div className="modal">
//   <div className="modal-content">
//     <span className="close" onClick={closeModal}>&times;</span>
//     <ContactForm existingContact={currentContact} updateCallback={onUpdate}/>
//   </div>
//   </div>

//   }
    
//     </>
//   );

// }




// export default App;

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
  const [isLoading, setIsLoading] = useState(true); // New state for loading

  useEffect(() => {
    fetchContacts();
    fetchLogs(); // Fetch logs when component mounts
    const interval = setInterval(fetchLogs, 2000); // Poll logs every 2 seconds
    return () => clearInterval(interval); // Clean up interval on unmount
  }, []);

  const fetchContacts = async () => {
    const response = await fetch('http://127.0.0.1:5000/contacts');
    const data = await response.json();
    setContacts(data.contacts);
    setIsLoading(false); // Set loading to false after data is fetched
  };

  const fetchLogs = async () => {
    const response = await fetch('http://127.0.0.1:5000/logs');
    const data = await response.json();
    setLogs(data.logs); // Set the logs from the backend
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
      fetchLogs(); // Fetch logs after email generation
    } catch (error) {
      alert('Failed to generate email. Please try again.');
      console.error(error);
    }
  };

  return (
    <>
      {/* Show loading screen while fetching data */}
      {isLoading && (
        <div className="loading-screen">
          <h2>Loading...</h2>
          <div className="loader"></div>
        </div>
      )}

      {/* Main content after loading */}
      {!isLoading && (
        <div className="container">
          <ContactList
            contacts={contacts}
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
                <ContactForm existingContact={currentContact} updateCallback={onUpdate} />
              </div>
            </div>
          )}

          {generatedEmail && (
            <div className="generated-email">
              <h2>Generated Email for {generatedEmail.contact.firstName} {generatedEmail.contact.lastName}</h2>
              <p>Email: {generatedEmail.contact.email}</p>
              <pre>{generatedEmail.emailContent}</pre>
            </div>
          )}
        </div>
      )}

      {/* Terminal log display */}
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
