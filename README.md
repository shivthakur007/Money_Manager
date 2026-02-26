💰 Money Manager
A full-stack cloud-based personal finance management application built with Python, Streamlit, Firebase, and Plotly.
Designed as a scalable foundation for intelligent financial analytics.

🚀 Live Overview
Money Manager is a secure, cloud-powered web application that allows users to:
- Track expenses
- Analyse spending patterns
- Visualize trends
- Manage financial data securely
- Download structured expense reports
This project combines authentication, database integration, analytics, and UI engineering into a production-style financial application.

🔐 Authentication System
The app supports:
✅ Email & Password login (Firebase Authentication REST API)
✅ Google OAuth 2.0 login
✅ Secure session management
✅ User-specific expense storage

Each user’s data is isolated using:
- users/{uid}/expenses
This ensures secure multi-user scalability.

🛠 Tech Stack
- Layer	Technology
- Frontend	Streamlit
- Backend Logic	Python
- Authentication	Firebase Auth (REST API + Google OAuth)
- Database	Firebase Firestore
- Data Processing	Pandas
- Visualization	Plotly
- API Handling	Requests

📊 Features

💵 Expense Management
Add expenses with:
- Name
- Amount
- Date
- Category
- Payment Mode
Custom categories & payment modes supported
Update existing entries
Delete entries

📈 Financial Analytics Dashboard
KPI Cards
- Total Expense
- Monthly Expense
- Top Spending Category

Interactive Charts
- Spending trend (line chart)
- Category distribution (donut chart)
- Monthly aggregated spending (bar chart)
All charts are built using Plotly for interactivity.

🔎 Advanced Filtering
Users can filter expenses by:
- Date range
- Category
- Payment mode
- Dynamic filtering updates:
- KPI metrics
- Charts
- Data tables

📁 Export Capability
- Download filtered expense data as CSV. This allows further financial analysis in Excel or other tools.

🎨 UI & UX Engineering
- Custom CSS-based theming
- Dark mode / Light mode toggle
- Gradient backgrounds
- Styled KPI cards
- Modern button animations
The interface is designed to resemble a production fintech dashboard.

🏗 Architecture Flow
- User authenticates (Email/Google)
- Firebase verifies identity
- User session stored in Streamlit
- Expense data stored in Firestore under user UID
- Data fetched → processed via Pandas
- Analytics computed dynamically
- Plotly renders interactive visualizations

📌 Design Philosophy
This project was designed with scalability in mind.

Why Firebase?
→ Serverless, scalable, real-time database.

Why OAuth?
→ Production-style authentication.

Why Plotly?
→ Interactive financial visualization.

Why user-level collections?
→ Multi-user secure architecture.

🧠 Future Scope
This application is designed to evolve into an intelligent financial system.
Planned enhancements:
🤖 Expense forecasting using ML
📷 OCR-based receipt parsing
🔍 Anomaly detection
🎯 Budget recommendation engine
📊 Category-wise predictive analytics
📈 Financial health scoring
🏦 Bank statement parsing integration
🎯 Learning Outcomes

Through this project, I implemented:
- REST-based authentication with Firebase
- OAuth 2.0 integration
- Firestore database design
- Secure multi-user data architecture
- Financial data processing with Pandas
- Interactive dashboards with Plotly
- UI customisation in Streamlit

🌍 Vision

Money Manager is not just an expense tracker.
It is the foundation for a data-driven personal financial intelligence system — combining finance, analytics, and scalable cloud architecture.
