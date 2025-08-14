# Healthcare_Assistant
A simple AI-powered health assistant that provides general health guidance based on user symptoms and suggests when to seek medical care. It uses:  OpenAI API for natural language understanding and response generation  Google Maps API for finding nearby hospitals, clinics, or pharmacies
# 🏥 AI Health Assistant

An AI-powered health assistant that helps users describe their symptoms and get general guidance on possible causes and when to seek medical attention.  
It also provides medicine facility details, nearby healthcare centers (via Google Maps API), and general health tips.

---

## ✨ Features
- 🤖 **AI Symptom Checker** – Users can input their symptoms and get helpful guidance.
- 💊 **Medicine Facilities Info** – Information about various types of medicines and their purposes.
- 📍 **Nearby Healthcare Search** – Uses Google Maps API to find hospitals, pharmacies, and clinics.
- 🔒 **Secure API Key Management** – API keys stored in `.env` file.
- 🖥 **User-Friendly Interface** – Simple chatbot-style UI for quick interaction.

---

## 🛠 Tech Stack
- **Python** (Flask backend)
- **HTML/CSS/JavaScript** (Frontend)
- **OpenAI API** – AI responses
- **Google Maps API** – Location services
- **dotenv** – Environment variable management

---

## 📂 Project Structure
newbot/
│-- app.py # Main application
│-- requirements.txt # Dependencies
│-- templates/ # HTML files
│-- static/ # CSS & JS files
│-- .env # API keys (not uploaded to GitHub)

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/ai-health-assistant.git
cd ai-health-assistant
2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Create .env File

Inside the project folder, create a .env file:

OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here


4️⃣ Run the App
python app.py


Then open your browser and go to:

http://127.0.0.1:5000

🚀 Usage

Start the application.

Enter your symptoms in the chatbot.

Get AI-generated health advice and nearby medical facilities.

📌 Important Notes

This app is for general informational purposes only and not a substitute for professional medical advice.

Always consult a healthcare provider for serious or urgent symptoms.

Keep your API keys safe and never commit .env to GitHub.
