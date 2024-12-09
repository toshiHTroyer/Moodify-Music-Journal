Here's the updated Markdown version of your README file:  

```markdown
[![Deploy to DigitalOcean Droplet](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/deploy.yml/badge.svg)](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/deploy.yml)
[![log github events](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/event-logger.yml/badge.svg)](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/event-logger.yml)

## **Team Members**

- **Boming Zhang** (bz2196) [GitHub Profile](https://github.com/BomingZhang-coder)
- **Annabeth Gao** (mg6839) [GitHub Profile](https://github.com/bellinimoon)
- **Sahar Bueno-Abdala** (sb8249) [GitHub Profile](https://github.com/saharbueno)
- **Toshi Troyer** (tht4789) [GitHub Profile](https://github.com/toshiHTroyer)

## **Product Description**
**Moodify** is a web-based platform designed to help users track their moods through journal entries and explore music that matches or enhances their emotional state. With the ability to search for songs via the Spotify API, add moods to entries, and visualize mood fluctuations through interactive graphs, Moodify combines self-reflection with music discovery. Users can also create playlists based on their moods, listen to songs to ensure they are the right fit, and manage their journal entries over time.

---

## **System Setup and Configuration**

### **1. Clone the Repository**
Clone the repository to your local machine:

```bash
git clone https://github.com/software-students-fall2024/5-final-codetarts.git
cd 5-final-codetarts
```

---

### **2. Create the `.env` File**
To run the application, create a `.env` file in the back-end directory with the following structure:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
FLASK_PORT=5001

# Spotify API Keys
CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here

# Database Configuration
MONGO_DBNAME=your_db_name_here
MONGO_URI='mongodb+srv://example:example@example.2h0hc.mongodb.net/?retryWrites=true&w=majority&appName=example'

# Secret Key
SECRET_KEY=your_secret_key_here
```

Replace the placeholders (`your_secret_key_here`, `your_client_id_here`, etc.) with your actual credentials.

---

### **3. Docker Setup**
To run the project in Docker containers:

1. **Build and Run the Docker Image**
   Navigate to the root directory and execute the following commands:

   ```bash
   docker-compose down
   docker-compose build
   docker-compose up -d
   ```

2. **Access the Application**
   After successfully running the Docker container, you can access the application using the following URLs:
   - **Home Page**: [http://localhost:5001](http://localhost:5001)

---

### **4. Dependencies Setup**
To run the application locally:

1. Install Python dependencies in the back-end folder:
   ```bash
   cd back-end
   pipenv shell
   pipenv install
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

---

### **5. Run the Flask App**
Once the dependencies and environment variables are set up, you can start the Flask app from the back-end directory:

```bash
python app.py
```

The application will be available at:  
[http://127.0.0.1:5001](http://127.0.0.1:5001)

```bash
* Running on http://127.0.0.1:5001 (Press CTRL+C to quit)
```

---

### **6. CI/CD Deployment**
The application is automatically deployed to a DigitalOcean Droplet using GitHub Actions.

#### **Steps in CI/CD Workflow**
1. **Build the Docker Image**: The Flask app is built as a Docker image.
2. **Push to Docker Hub**: The Docker image is uploaded to Docker Hub.
3. **Deploy on DigitalOcean**: The Docker container is deployed to a DigitalOcean Droplet.

#### **View Deployed Application**
The application is deployed at:  
[http://159.89.237.2:5001/](http://159.89.237.2:5001/)

---

## **Contributing**
Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix:
   ```bash
   git checkout -b feature-name
   ```
3. Commit your changes:
   ```bash
   git commit -m "Add feature-name"
   ```
4. Push to your branch:
   ```bash
   git push origin feature-name
   ```
5. Submit a pull request.

---

## **License**
This project is licensed under the MIT License.
```