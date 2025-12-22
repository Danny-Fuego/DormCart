# DormCart

DormCart is a campus-focused marketplace web application designed to help college students buy and sell everyday items within their university community. The platform targets common dorm-life needs such as electronics, books, clothing, kitchen items, and furniture, providing a more relevant and convenient alternative to large, general-purpose marketplaces.

This project was developed as the **Final Project for CS50** and demonstrates full-stack web development concepts including authentication, database design, server-side rendering, and responsive user interface design.

---

## Video Demo

**Video Demo:** https://youtu.be/8UcrsLFA1nM

---

## Project Overview

DormCart was inspired by a common experience among college students: frequently needing affordable items for dorm life while also having unused items to sell. Existing marketplaces often feel cluttered, unsafe, or overly broad. DormCart narrows the scope to campus-relevant items and prioritizes simplicity, clarity, and ease of use.

The application allows users to create accounts, browse product listings, view detailed product pages with images, add items to a cart, and manage their listings through a personal profile page. While the project does not implement real payments, it simulates a complete marketplace flow and is structured to support future expansion.

---

## Features

- Secure user authentication (signup, login, logout)
- Session-based access control for protected routes
- Product browsing by category
- Keyword-based search (title, description, category)
- Product detail pages with images
- Shopping cart functionality
- User profile page with listing statistics
- Seller rating system (database-ready)
- Flash messages for user feedback
- Responsive design with mobile navigation

---

## Technologies Used

- **Python** – core application logic  
- **Flask** – web framework and routing  
- **SQLite** – lightweight relational database  
- **HTML & CSS** – page structure and styling  
- **JavaScript** – frontend interactivity  
- **Jinja2** – server-side templating  

---

## Project Structure

```
Code/
│── app.py
│── create_db.py
│── seed_product_images.py
│── dormcart.db
│── requirements.txt
│
├── templates/
│   ├── layout.html
│   ├── homepage.html
│   ├── product_detail.html
│   ├── profile.html
│   └── …
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── README.md
```

---

## How to Run

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize the database:
```bash
python create_db.py
```

3. Run the application:
```bash
flask run
```

---

## Design Decisions

DormCart was designed specifically for college students living on campus. Instead of acting as a general marketplace, it focuses on items commonly needed in dorms and student apartments. The user interface prioritizes simplicity and speed, while the database schema was structured to support future features such as seller ratings, saved items, and order history without major refactoring.

---

## Use of AI Tools

ChatGPT was used as a learning and debugging assistant during the development of this project. Whenever I encountered challenges while implementing features or resolving errors, ChatGPT helped guide me through understanding the problem and possible solutions.

Specifically, ChatGPT was used in the following areas:

- Debugging Flask route errors and request handling
- Troubleshooting SQL queries and database logic
- Understanding SQLite limitations (such as ALTER TABLE constraints)
- Clarifying application structure and best practices

All final implementation decisions and code were written and reviewed by me.

---

## Design Decisions, Trade-offs, and Development Reflections

One of the main design decisions I made early in this project was to **scope DormCart as a campus-only marketplace**, rather than a general-purpose platform like Facebook Marketplace or eBay. This decision influenced almost every part of the application—from the categories I included (Dorm & Room, Books, Electronics, etc.) to the way listings are displayed and searched. By narrowing the audience to students, I was able to design a simpler interface that prioritizes speed and relevance over complexity.

### Feature Prioritization and Scope Control
Because this project was developed as a CS50 final project with limited time, I intentionally **prioritized core functionality** over advanced features. User authentication, product listings, search, cart logic, and profile pages were treated as non-negotiable core features. On the other hand, features such as real-time messaging, checkout/payment processing, and notifications were deliberately left out. These features would significantly increase complexity and distract from demonstrating my understanding of Flask, databases, and full-stack fundamentals.

For example, the **checkout system** was intentionally disabled. Instead of simulating payments poorly, I chose to block checkout entirely and clearly communicate that it is unavailable in this demo. This kept the application honest and technically clean, while still allowing the cart system to demonstrate relational database design and route protection.

### Database Design Choices
I designed the database schema with **future scalability in mind**, even though not all tables are fully used yet. Tables such as `seller_ratings` and certain profile-related fields exist to show forward planning. I also implemented a `seed_flags` system to ensure database seeding scripts can be safely re-run without duplicating data. This approach reflects real-world backend practices where migrations and idempotent scripts are important.

SQLite was chosen instead of PostgreSQL or MySQL because it fits the scope of the project and keeps setup simple for graders. I accepted SQLite’s limitations (such as limited ALTER TABLE support) and worked around them carefully, rather than switching to a heavier database unnecessarily.

### UI / UX Decisions
On the frontend, I chose to build **custom HTML, CSS, and JavaScript** instead of using a UI framework like Bootstrap. This allowed me to fully control layout behavior, responsiveness, and visual hierarchy. The navbar drawer system, toast notifications, and responsive layouts were implemented manually to better demonstrate my understanding of frontend fundamentals.

The interface emphasizes clarity and minimalism. For example:
- Listings show only essential information upfront
- Actions like “Edit listing” are visibly disabled rather than hidden
- Profile statistics are summarized instead of overwhelming the user

### Security and Authentication Choices
Password hashing was handled using Werkzeug, and session-based authentication was used instead of JWTs to keep the architecture simple and appropriate for a server-rendered Flask app. Password reset functionality was implemented using signed, time-limited tokens to demonstrate secure token handling without introducing email infrastructure.

### Use of AI During Development
AI tools were used selectively as a **learning and debugging aid**, not as a code generator. In particular, AI helped clarify Flask routing patterns, SQLite behaviors, and edge cases during debugging. However, architectural decisions, database design, UI structure, and final implementations were all planned, written, and tested by me. Any AI assistance was treated as guidance rather than direct answers.

### What I Chose Not to Do (and Why)
Some features were intentionally forfeited:
- No real-time chat 
- No payment processing 
- No image upload handling 
- No admin dashboard

These decisions were made to keep the project focused, stable, and aligned with CS50’s learning goals rather than overextending into incomplete features.

## Future Improvements

- Real-time chat between buyers and sellers
- Image uploads instead of static URLs
- Payment integration
- Notifications for new messages and orders

---

Author: Daniel Baadom