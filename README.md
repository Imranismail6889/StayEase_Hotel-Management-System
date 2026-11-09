# 🏨 StayEase - Full-Stack Hotel Reservation System

StayEase is a full-stack hotel reservation and management application built with **Python Flask**. It provides customers with an easy way to explore rooms, check availability, make reservations, and manage bookings. Administrators can manage rooms, bookings, customers, promotional codes, and hotel reports.

## ✨ Features

### Customer Website
- Responsive hotel website.
- Browse and search available rooms.
- Filter rooms by price, capacity, type, and amenities.
- View room details, galleries, and reviews.
- Customer registration and login.
- Save favorite rooms.
- Submit room reviews.

### Booking and Reservations
- Book rooms with check-in and check-out dates.
- Automatic booking price calculation.
- Additional services such as breakfast, airport pickup, and spa packages.
- Apply promotional discount codes.
- Prevent overlapping room reservations.
- Modify or cancel bookings.
- View and download invoices.
- Download calendar booking files.
- Mock payment gateway integration.

### Customer Dashboard
- View upcoming and past bookings.
- Manage reservations.
- View booking history.
- Manage favorite rooms.
- View loyalty points and rewards.
- Receive notifications.
- Update profile information.

### Admin Dashboard
- View hotel statistics and revenue.
- Monitor room availability and occupancy.
- Add, update, and manage rooms.
- Manage customer bookings.
- View customer information.
- Export booking records to CSV.
- Manage promotional codes.
- Generate revenue and booking reports.
- Configure hotel settings.

### Additional Features
- Responsive design for desktop, tablet, and mobile.
- Light mode and dark mode.
- Interactive charts and tables.
- Form validation.
- Notifications and interactive modals.
- Loading, empty, and error states.

## 💻 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Backend framework |
| HTML5 | Website structure |
| CSS3 | Styling and responsive design |
| JavaScript | Frontend functionality |
| SQLAlchemy | Database ORM |
| SQLite | Database |
| Flask-JWT-Extended | Authentication |
| Flask-Migrate | Database migrations |
| pytest | Testing |

## 📂 Project Structure

```text
stayease/
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── wsgi.py
├── config.py
├── migrations/
├── app/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models/
│   ├── schemas/
│   ├── blueprints/
│   ├── services/
│   └── utils/
├── templates/
├── static/
│   ├── index.html
│   ├── css/
│   └── js/
└── tests/
```

## 🚀 Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Imranismail6889/StayEase.git
cd StayEase
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

### 3. Activate the Virtual Environment

**Windows:**

```bash
venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Copy `.env.example` to `.env` and configure the required environment variables.

```powershell
Copy-Item .env.example .env
```

### 6. Initialize the Database

Run the migration commands:

```bash
flask db init
flask db migrate -m "initial"
flask db upgrade
```

### 7. Add Demo Data

```bash
flask seed
```

### 8. Run the Application

```bash
flask run
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## 🔐 Demo Login Credentials

**Admin Account**

```text
Email: admin@stayease.com
Password: Admin@123
```

**Customer Account**

```text
Email: guest@stayease.com
Password: Guest@123
```

These credentials are for local development only; production seeding requires a unique administrator password.

## 🗄️ Database Models

The main database models include:

- User
- Room
- Amenity
- Booking
- BookingExtra
- Payment
- Review
- Favorite
- PromoCode
- Notification
- NewsletterSubscriber
- LoyaltyTransaction
- Setting

## 🔌 REST API

The application provides REST API endpoints for:

- Authentication and user management.
- Room search and availability.
- Booking creation and management.
- Payment processing.
- Reviews and favorites.
- Promotional codes.
- Notifications.
- Admin operations and reports.

Protected API endpoints use JWT authentication.

## 🔒 Security Features

- Password hashing.
- JWT-based authentication.
- Role-based authorization.
- Input validation.
- API rate limiting.
- Environment-based secret keys.
- Protected administrator routes.
- Customer data access restrictions.

## 💳 Payment Information

StayEase uses a mock payment gateway for demonstration purposes. It is designed to allow future integration with real payment providers such as Razorpay or Stripe.

Do not enter real payment card information into the demo application.

## 🔮 Future Enhancements

- Real payment gateway integration.
- Email booking confirmations.
- PostgreSQL or MySQL database integration.
- Real-time room availability.
- Advanced analytics and reports.
- Multi-language support.
- Live customer support.

## 🎯 Project Objective

The main objective of StayEase is to simplify hotel reservation and management operations through a user-friendly platform. It aims to improve customer booking experiences while providing administrators with efficient tools to manage hotel activities.

## 👨‍💻 Author

**Imran Ismail**

GitHub: [Imranismail6889](https://github.com/Imranismail6889)

## 📄 License

This project is developed for educational and demonstration purposes.


## Vercel deployment

Vercel serves the Flask app through the root `wsgi.py` entry point. The configured build step copies CSS and JavaScript into `public/static/` for CDN delivery. Production and preview environments must set strong `SECRET_KEY` and `JWT_SECRET_KEY` values and a persistent PostgreSQL or MySQL `DATABASE_URL`; the app refuses to start with SQLite in those environments. Apply migrations to the remote database before serving traffic.

Production `flask seed` requires a unique `STAYEASE_ADMIN_PASSWORD` with at least 16 characters. Seeded customer accounts receive random passwords unless `STAYEASE_GUEST_PASSWORD` is set. `flask reset-db` is disabled in production and preview environments.
