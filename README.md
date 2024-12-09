[![Deploy to DigitalOcean Droplet](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/deploy.yml/badge.svg)](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/deploy.yml)
[![log github events](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/event-logger.yml/badge.svg)](https://github.com/software-students-fall2024/5-final-codetarts/actions/workflows/event-logger.yml)
# Final Project

An exercise to put to practice software development teamwork, subsystem communication, containers, deployment, and CI/CD pipelines. See [instructions](./instructions.md) for details.

## **Team Members**

- **Boming Zhang** (bz2196) [GitHub Profile](https://github.com/BomingZhang-coder)
- **Annabeth Gao** (mg6839) [GitHub Profile](https://github.com/bellinimoon)
- **Sahar Bueno-Abdala** (sb8249) [GitHub Profile](github.com/saharbueno)
- **Toshi Troyer** (tht4789) [GitHub Profile](https://github.com/toshiHTroyer)

## **Product Description**
**Moodify** is a web-based platform designed to help users track their moods through journal entries and explore music that matches or enhances their emotional state. With the ability to search for songs via the SoundCloud API, add moods to entries, and visualize mood fluctuations through interactive graphs, Moodify is a tool that combines self-reflection with music discovery. Additionally, users can create playlists based on their moods, listen to songs to ensure they are the right fit, and manage their journal entries over time.

## **System Setup and Configuration**

### **1. Clone the Repository**

   ```bash
    git clone https://github.com/software-students-fall2024/5-final-codetarts.git
    cd 5-final-codetarts
   ```

### **2. Docker Setup**
If you wish to run the project in Docker containers:
1. **Build the Docker Image**
   
   Navigate to the root directory and run the following command to build the Docker image and run:

    ```bash 
     docker-compose down
     docker-compose build
     docker-compose up -d
    ```

2. **Access the Application**
    After successfully running the Docker container, you can access the application using the following URLs:

    - **Home Page**:http://localhost:5001
    - **deployment**:http://159.89.237.2:5001


### **3. Dependencies Setup**
1. Install Python dependencies:

   ```bash 
    pipenv install
   ```

2. Install frontend dependencies:

   ```bash 
    npm install
   ```

### **4. Environment Setup**
Create a `.env` file in the root directory with the following content:
```env
   MONGO_DBNAME=codeTarts
   MONGO_URI=mongodb+srv://codeTarts:codeTarts@codetarts.2h0hc.mongodb.net/?retryWrites=true&w=majority&appName=codeTarts
   CLIENT_ID='2a9f6bc4387544a68f54ece6d445e615'
   CLIENT_SECRET='e8ff777cf6db4d82b8e73fce15407b05'
   FLASK_APP=app.py
   FLASK_ENV=development
   FLASK_PORT=5001
   SECRET_KEY=codeTarts
```
This .env file will configure the connection to your MongoDB instance.

### **5. Run the Flask App**
Once the dependencies and environment variables are set up, you can run the Flask app with the following command:

   ```bash 
    python app.py
   ```

This will start the application on http://127.0.0.1:5000. 

   ```bash 
    * Running on http://127.0.0.1:5000 (Press CTRL+C to quit)
   ```

### **6. CI/CD Deployment**

The application is automatically built and deployed to a DigitalOcean Droplet using GitHub Actions.

#### **Steps in CI/CD Workflow**
1. **Build the Docker Image**: Builds the Flask app as a Docker image.
2. **Push to Docker Hub**: Uploads the image to Docker Hub.
3. **Deploy on DigitalOcean**: Deploys the Docker container on a DigitalOcean Droplet.

#### **View Deployed Application**
- Deployed at: [http://159.89.237.2:5001/home](http://159.89.237.2:5001/home)



